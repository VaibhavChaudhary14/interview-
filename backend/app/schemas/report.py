from pydantic import BaseModel


class TranscriptEntry(BaseModel):
    sequence: int
    question: str
    answer: str
    topic: str
    source_chunks: list[str]


class Insights(BaseModel):
    questions_answered: int
    average_answer_length_words: int
    topics_with_thin_answers: list[str]
    resume_alignment_note: str


class ReportResponse(BaseModel):
    session_id: str
    role: str
    generated_at: str
    topics_covered: list[str]
    transcript: list[TranscriptEntry]
    insights: Insights
