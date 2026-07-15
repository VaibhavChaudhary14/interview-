import logging
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Integer, Float, Date
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base

logger = logging.getLogger(__name__)


# Per-character cost estimates for TTS providers (USD per character).
# ElevenLabs free tier: 10,000 chars/month. Paid: ~$0.00003/char.
# Sarvam: similar magnitude. These are rough estimates for alerting, not billing.
TTS_COST_PER_CHAR = {
    "elevenlabs": 0.00003,
    "sarvam": 0.000025,
    "mock": 0.0,
}

# Per-second cost estimates for STT providers (USD per second of audio).
STT_COST_PER_SECOND = {
    "assemblyai": 0.0001,
    "elevenlabs": 0.00008,
    "sarvam": 0.0001,
    "whisper": 0.0001,
    "mock": 0.0,
}


class ProviderUsage(Base):
    __tablename__ = "provider_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False, index=True)
    call_type = Column(String, nullable=False, default="stt")  # "stt" | "tts"
    call_count = Column(Integer, default=0, nullable=False)
    total_seconds = Column(Float, default=0.0, nullable=False)    # STT: seconds of audio
    total_characters = Column(Float, default=0.0, nullable=False)  # TTS: input text char count
    usage_date = Column(Date, default=lambda: datetime.now(timezone.utc).date(), nullable=False, index=True)

    @classmethod
    def record_usage(cls, db, provider: str, duration: float):
        """Record STT usage (billed by seconds of audio processed)."""
        if db is None:
            return
        try:
            today = datetime.now(timezone.utc).date()
            usage = (
                db.query(cls)
                .filter(cls.provider == provider, cls.call_type == "stt", cls.usage_date == today)
                .first()
            )
            if not usage:
                usage = cls(
                    provider=provider,
                    call_type="stt",
                    call_count=1,
                    total_seconds=duration,
                    usage_date=today,
                )
                db.add(usage)
            else:
                usage.call_count += 1
                usage.total_seconds += duration
            db.commit()

            rate = STT_COST_PER_SECOND.get(provider.lower(), 0.0)
            cost_estimate = rate * duration
            logger.info(
                "STT: %s used, %.2fs, cost_estimate=$%.5f", provider, duration, cost_estimate
            )

            # Alert when AssemblyAI free tier usage is >80% of 600 mins (28,800s) in current month
            if provider.lower() == "assemblyai":
                first_of_month = today.replace(day=1)
                from sqlalchemy import func
                monthly_secs = (
                    db.query(func.sum(cls.total_seconds))
                    .filter(
                        cls.provider == "assemblyai",
                        cls.call_type == "stt",
                        cls.usage_date >= first_of_month,
                    )
                    .scalar()
                    or 0.0
                )
                if monthly_secs > 480 * 60:
                    logger.warning(
                        "ALARM: AssemblyAI usage has exceeded 80%% of the free tier limit! "
                        "Current month total: %.2f minutes.",
                        monthly_secs / 60,
                    )
        except Exception as e:
            logger.error("Failed to record STT provider usage: %s", e)

    @classmethod
    def record_tts_usage(cls, db, provider: str, char_count: int):
        """
        Record TTS usage, billed per character of *input text* (not output audio duration).
        ElevenLabs and Sarvam both price TTS per character, not per second of audio generated.
        Keeping a separate daily-aggregate row per provider+call_type keeps the existing
        STT rows intact while adding correct TTS accounting.
        """
        if db is None:
            return
        try:
            today = datetime.now(timezone.utc).date()
            usage = (
                db.query(cls)
                .filter(cls.provider == provider, cls.call_type == "tts", cls.usage_date == today)
                .first()
            )
            if not usage:
                usage = cls(
                    provider=provider,
                    call_type="tts",
                    call_count=1,
                    total_characters=char_count,
                    usage_date=today,
                )
                db.add(usage)
            else:
                usage.call_count += 1
                usage.total_characters += char_count
            db.commit()

            rate = TTS_COST_PER_CHAR.get(provider.lower(), 0.0)
            cost_estimate = rate * char_count
            logger.info(
                "TTS: %s used, %d chars, cost_estimate=$%.5f", provider, char_count, cost_estimate
            )
        except Exception as e:
            logger.error("Failed to record TTS provider usage: %s", e)
