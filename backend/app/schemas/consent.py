from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ConsentSubmitRequest(BaseModel):
    consent_text_version: str
    audio_recording_allowed: bool


class ConsentResponse(BaseModel):
    consent_id: str
    session_id: str
    consent_text_version: str
    audio_recording_allowed: bool
    granted_at: datetime
    ip_address: Optional[str] = None


class ConsentActiveVersionResponse(BaseModel):
    version: str
    consent_text: str
