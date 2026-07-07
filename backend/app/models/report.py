import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.session import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), unique=True, nullable=False)
    topics_covered = Column(JSONB, default=list)
    insights = Column(JSONB, default=dict)
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
