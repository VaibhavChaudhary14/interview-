from pydantic import BaseModel
from typing import Optional


class TranscriptEntry(BaseModel):
    sequence: int
    question: str
    answer: str
    topic: str
    source_chunks: list[str]
    recording_id: Optional[str] = None
    audio_metrics: Optional[dict] = None


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
