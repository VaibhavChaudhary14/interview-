from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from app.db.session import get_db
from app.models.resume import Resume
from app.services.resume_parser import ResumeParserService
from app.schemas.resume import ResumeUploadResponse, ResumeExtracted

router = APIRouter(prefix="/resume", tags=["resume"])
parser_service = ResumeParserService()


@router.post("", response_model=ResumeUploadResponse, status_code=201)
async def upload_resume(file: UploadFile = File(...), db: DBSession = Depends(get_db)):
    if file.content_type not in ("application/pdf", "text/plain"):
        raise HTTPException(400, detail={"error_code": "UNSUPPORTED_FILE", "message": "Only PDF and .txt files are supported.", "details": {}})

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, detail={"error_code": "FILE_TOO_LARGE", "message": "File exceeds 5MB limit.", "details": {}})

    import io
    file_like = io.BytesIO(content)
    try:
        parsed = parser_service.parse(file_like)
    except ValueError as e:
        raise HTTPException(422, detail={"error_code": "UNPARSABLE_RESUME", "message": str(e), "details": {}})

    resume = Resume(**parsed)
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return ResumeUploadResponse(
        resume_id=str(resume.id),
        extracted=ResumeExtracted(
            skills=resume.extracted_skills,
            technologies=resume.extracted_technologies,
            domains=resume.extracted_domains,
            years_experience_estimate=resume.years_experience_estimate,
        ),
    )
