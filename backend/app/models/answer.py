import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class Answer(Base):
    __tablename__ = "answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), unique=True, nullable=False)
    answer_text = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)
    answered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
