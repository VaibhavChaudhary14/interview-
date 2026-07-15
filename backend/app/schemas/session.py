from pydantic import BaseModel
from typing import Literal, Optional
from app.models.session import SessionDifficulty


class SessionCreateRequest(BaseModel):
    resume_id: Optional[str] = None
    role: str
    mode: Literal["agency", "self_prep"] = "self_prep"
    retention_days_override: Optional[int] = None
    difficulty: SessionDifficulty = SessionDifficulty.intermediate



class SessionResponse(BaseModel):
    session_id: str
    status: str
    role: str
    mode: str
    difficulty: SessionDifficulty
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
    difficulty: SessionDifficulty
    questions_asked: int
    max_questions: int
    report_available: bool
    retention_days_override: Optional[int] = None
    matched_family_id: Optional[str] = None
    classification_method: Optional[str] = None
    classification_confidence: Optional[float] = None

