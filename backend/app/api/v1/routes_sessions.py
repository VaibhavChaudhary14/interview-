import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from app.db.session import get_db
from app.models.resume import Resume
from app.models.session import Session
from app.services.query_builder import QueryBuilderService
from app.services.role_classifier import RoleClassifierService
from app.schemas.session import SessionCreateRequest, SessionResponse, SessionStatusResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])
query_builder = QueryBuilderService()


@router.post("", response_model=SessionResponse, status_code=201)
def create_session(body: SessionCreateRequest, db: DBSession = Depends(get_db)):
    resume_id = None
    extracted_skills = []
    extracted_technologies = []

    if body.resume_id:
        try:
            resume_uuid = uuid.UUID(body.resume_id) if isinstance(body.resume_id, str) else body.resume_id
        except ValueError:
            raise HTTPException(400, detail={"error_code": "INVALID_RESUME_ID", "message": "Invalid resume ID format.", "details": {}})
        
        resume = db.query(Resume).filter(Resume.id == resume_uuid).first()
        if not resume:
            raise HTTPException(404, detail={"error_code": "RESUME_NOT_FOUND", "message": "No resume found with the given id.", "details": {}})
        
        resume_id = resume.id
        extracted_skills = resume.extracted_skills
        extracted_technologies = resume.extracted_technologies

    # Classify the target role
    classifier = RoleClassifierService(db)
    result = classifier.classify(body.role)
    matched_family_uuid = uuid.UUID(result.family_id) if result.family_id else None

    session = Session(
        resume_id=resume_id,
        role=body.role,
        mode=body.mode,
        retention_days_override=body.retention_days_override,
        status="CREATED",
        max_questions=8,
        matched_family_id=matched_family_uuid,
        classification_method=result.method,
        classification_confidence=result.confidence,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    session.transition_to("PROCESSING_RESUME")
    queries = query_builder.build_queries(
        resume_signals={
            "extracted_skills": extracted_skills,
            "extracted_technologies": extracted_technologies,
        },
        role=session.role,
        max_questions=session.max_questions,
    )
    session.retrieval_queries = queries
    session.transition_to("CONTEXT_BUILT")
    db.commit()

    return SessionResponse(
        session_id=str(session.id),
        status=session.status,
        role=session.role,
        mode=session.mode,
        max_questions=session.max_questions,
        retention_days_override=session.retention_days_override,
        matched_family_id=str(session.matched_family_id) if session.matched_family_id else None,
        classification_method=session.classification_method,
        classification_confidence=session.classification_confidence,
    )


@router.get("/{session_id}", response_model=SessionStatusResponse)
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found with the given id.", "details": {}})

    from app.models.report import Report
    report = db.query(Report).filter(Report.session_id == session.id).first()

    return SessionStatusResponse(
        session_id=str(session.id),
        status=session.status,
        role=session.role,
        mode=session.mode,
        questions_asked=session.questions_asked,
        max_questions=session.max_questions,
        report_available=report is not None,
        retention_days_override=session.retention_days_override,
        matched_family_id=str(session.matched_family_id) if session.matched_family_id else None,
        classification_method=session.classification_method,
        classification_confidence=session.classification_confidence,
    )
