from pydantic import BaseModel


class QuestionResponse(BaseModel):
    question_id: str
    sequence: int
    topic: str
    question_text: str
    source_chunks: list[str]
    is_final_question: bool
    copilot_hints: dict | None = None
    reference_texts: list[dict] | None = None
