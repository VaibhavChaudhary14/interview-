from pydantic import BaseModel, Field, field_validator
from typing import Optional


class FeedbackCreateRequest(BaseModel):
    rating_realistic: int = Field(..., description="Rating for question realism from 1 to 5")
    rating_feedback: int = Field(..., description="Rating for coaching feedback from 1 to 5")
    comments: Optional[str] = Field(None, description="Optional text feedback comments")

    @field_validator("rating_realistic", "rating_feedback")
    @classmethod
    def validate_ratings(cls, value: int) -> int:
        if value < 1 or value > 5:
            raise ValueError("Ratings must be between 1 and 5 (inclusive)")
        return value


class FeedbackResponse(BaseModel):
    id: str
    session_id: str
    rating_realistic: int
    rating_feedback: int
    comments: Optional[str]
    created_at: str
