from pydantic import BaseModel


class AnswerSubmitRequest(BaseModel):
    question_id: str
    answer_text: str


class AnswerSubmitResponse(BaseModel):
    stored: bool
    session_status: str
    questions_asked: int
    questions_remaining: int
