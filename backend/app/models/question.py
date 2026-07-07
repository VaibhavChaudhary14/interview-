import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.session import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    topic = Column(String, nullable=False)
    question_text = Column(Text, nullable=False)
    source_chunk_ids = Column(JSONB, default=list)
    generation_strategy = Column(String, default="initial")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
