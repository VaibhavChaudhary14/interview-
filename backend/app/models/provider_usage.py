import logging
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Integer, Float, Date
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base

logger = logging.getLogger(__name__)


class ProviderUsage(Base):
    __tablename__ = "provider_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False, index=True)
    call_count = Column(Integer, default=0, nullable=False)
    total_seconds = Column(Float, default=0.0, nullable=False)
    usage_date = Column(Date, default=lambda: datetime.now(timezone.utc).date(), nullable=False, index=True)

    @classmethod
    def record_usage(cls, db, provider: str, duration: float):
        if db is None:
            return
        try:
            today = datetime.now(timezone.utc).date()
            usage = db.query(cls).filter(cls.provider == provider, cls.usage_date == today).first()
            if not usage:
                usage = cls(
                    provider=provider,
                    call_count=1,
                    total_seconds=duration,
                    usage_date=today
                )
                db.add(usage)
            else:
                usage.call_count += 1
                usage.total_seconds += duration
            db.commit()

            # Cost estimates:
            rates = {
                "assemblyai": 0.0001,
                "elevenlabs": 0.00008,
                "sarvam": 0.0001,
                "whisper": 0.0001,
                "mock": 0.0
            }
            rate = rates.get(provider.lower(), 0.0)
            cost_estimate = rate * duration
            logger.info(f"STT/TTS: {provider} used, {duration:.2f}s, cost_estimate=${cost_estimate:.5f}")

            # Alert when AssemblyAI free tier usage is > 80% of 600 mins (i.e. 480 mins / 28800 seconds) in the current month
            if provider.lower() == "assemblyai":
                first_of_month = today.replace(day=1)
                from sqlalchemy import func
                monthly_secs = db.query(func.sum(cls.total_seconds)).filter(
                    cls.provider == "assemblyai",
                    cls.usage_date >= first_of_month
                ).scalar() or 0.0
                if monthly_secs > 480 * 60:
                    logger.warning(f"ALARM: AssemblyAI usage has exceeded 80% of the free tier limit! Current month total: {monthly_secs / 60:.2f} minutes.")
        except Exception as e:
            logger.error(f"Failed to record provider usage: {e}")
