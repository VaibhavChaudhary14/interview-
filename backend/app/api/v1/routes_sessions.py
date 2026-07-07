from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from app.db.session import get_db
from app.models.resume import Resume
from app.models.session import Session
from app.services.query_builder import QueryBuilderService
from app.schemas.session import SessionCreateRequest, SessionResponse, SessionStatusResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])
query_builder = QueryBuilderService()


@router.post("", response_model=SessionResponse, status_code=201)
def create_session(body: SessionCreateRequest, db: DBSession = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.id == body.resume_id).first()
    if not resume:
        raise HTTPException(404, detail={"error_code": "RESUME_NOT_FOUND", "message": "No resume found with the given id.", "details": {}})

    session = Session(
        resume_id=resume.id,
        role=body.role,
        status="CREATED",
        max_questions=8,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    session.transition_to("PROCESSING_RESUME")
    queries = query_builder.build_queries(
        resume_signals={
            "extracted_skills": resume.extracted_skills,
            "extracted_technologies": resume.extracted_technologies,
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
        max_questions=session.max_questions,
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
        questions_asked=session.questions_asked,
        max_questions=session.max_questions,
        report_available=report is not None,
    )
