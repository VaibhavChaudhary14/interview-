from pydantic import BaseModel
from typing import Literal, Optional


class SessionCreateRequest(BaseModel):
    resume_id: Optional[str] = None
    role: str
    mode: Literal["agency", "self_prep"] = "self_prep"
    retention_days_override: Optional[int] = None


class SessionResponse(BaseModel):
    session_id: str
    status: str
    role: str
    mode: str
    max_questions: int
    retention_days_override: Optional[int] = None
    matched_family_id: Optional[str] = None
    classification_method: Optional[str] = None
    classification_confidence: Optional[float] = None


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    role: str
    mode: str
    questions_asked: int
    max_questions: int
    report_available: bool
    retention_days_override: Optional[int] = None
    matched_family_id: Optional[str] = None
    classification_method: Optional[str] = None
    classification_confidence: Optional[float] = None

