from pydantic import BaseModel


class SessionCreateRequest(BaseModel):
    resume_id: str
    role: str


class SessionResponse(BaseModel):
    session_id: str
    status: str
    role: str
    max_questions: int


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    role: str
    questions_asked: int
    max_questions: int
    report_available: bool
