import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.session import Base


class AnswerMetrics(Base):
    __tablename__ = "answer_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    answer_id = Column(UUID(as_uuid=True), ForeignKey("answers.id"), unique=True, nullable=False)

    # Speaking pace
    wpm = Column(Float, nullable=True)
    word_count = Column(Integer, nullable=True)
    audio_duration_seconds = Column(Float, nullable=True)

    # Pause detection
    pause_count = Column(Integer, nullable=True)
    avg_pause_duration = Column(Float, nullable=True)
    longest_pause_seconds = Column(Float, nullable=True)

    # Filler words
    filler_word_count = Column(Integer, nullable=True)
    filler_word_breakdown = Column(JSONB, nullable=True, default=dict)
    # e.g. {"unambiguous": {"um": 3, "uh": 1}, "contextual": {"so": 5, "actually": 2}}

    computed_at = Column(DateTime(timezone=True), nullable=True)

    # Null on success. On failure, stores the exception message so the failure
    # is visible rather than silently producing a missing row.
    computation_error = Column(Text, nullable=True)
