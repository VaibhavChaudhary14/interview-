from pydantic import BaseModel


class ResumeExtracted(BaseModel):
    skills: list[str]
    technologies: list[str]
    domains: list[str]
    years_experience_estimate: int


class ResumeResponse(BaseModel):
    resume_id: str
    extracted: ResumeExtracted


class ResumeUploadResponse(BaseModel):
    resume_id: str
    extracted: ResumeExtracted
