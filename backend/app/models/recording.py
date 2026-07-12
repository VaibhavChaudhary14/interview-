import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.session import Base


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    answer_id = Column(UUID(as_uuid=True), ForeignKey("answers.id"), nullable=True)
    s3_key = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    consent_id = Column(UUID(as_uuid=True), ForeignKey("consents.id"), nullable=True)
    metrics = Column(JSONB, nullable=True, default=dict)
    deletion_requested_at = Column(DateTime(timezone=True), nullable=True)
    deletion_completed_at = Column(DateTime(timezone=True), nullable=True)
