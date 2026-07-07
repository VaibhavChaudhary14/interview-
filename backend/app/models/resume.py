import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.session import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raw_text = Column(Text, nullable=False)
    extracted_skills = Column(JSONB, default=list)
    extracted_technologies = Column(JSONB, default=list)
    extracted_domains = Column(JSONB, default=list)
    years_experience_estimate = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
