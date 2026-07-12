import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.session import Base


VALID_STATUSES = [
    "CREATED", "PROCESSING_RESUME", "CONTEXT_BUILT",
    "RETRIEVING", "IN_PROGRESS", "COMPLETED", "REPORT_READY",
]

VALID_TRANSITIONS = {
    "CREATED": ["PROCESSING_RESUME"],
    "PROCESSING_RESUME": ["CONTEXT_BUILT"],
    "CONTEXT_BUILT": ["RETRIEVING"],
    "RETRIEVING": ["IN_PROGRESS"],
    "IN_PROGRESS": ["IN_PROGRESS", "COMPLETED"],
    "COMPLETED": ["REPORT_READY"],
    "REPORT_READY": [],
}


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=True)
    role = Column(String, nullable=False)
    mode = Column(String, default="self_prep", nullable=False)
    retention_days_override = Column(Integer, nullable=True)
    status = Column(String, default="CREATED", nullable=False)
    max_questions = Column(Integer, default=8)
    questions_asked = Column(Integer, default=0)
    retrieval_queries = Column(JSONB, default=list)

    matched_family_id = Column(UUID(as_uuid=True), ForeignKey("role_families.id"), nullable=True)
    classification_method = Column(String, nullable=True)
    classification_confidence = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def transition_to(self, new_status: str) -> None:
        if new_status not in VALID_TRANSITIONS.get(self.status, []):
            from app.core.exceptions import InvalidStateTransition
            raise InvalidStateTransition(f"Cannot transition from {self.status} to {new_status}")
        self.status = new_status
