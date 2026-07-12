import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class TranscriptionJob(Base):
    __tablename__ = "transcription_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String, unique=True, nullable=False, index=True)
    answer_id = Column(UUID(as_uuid=True), ForeignKey("answers.id"), nullable=True)
    status = Column(String, default="pending", nullable=False)
    error_message = Column(Text, nullable=True)
    webhook_received_at = Column(DateTime(timezone=True), nullable=True)
    sync_poll_exhausted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
