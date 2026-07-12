from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from app.db.session import get_db
from app.models.session import Session
from app.models.question import Question
from app.models.answer import Answer
from app.models.report import Report
from app.models.resume import Resume
from app.services.report_builder import ReportBuilderService
from app.schemas.report import ReportResponse

router = APIRouter(prefix="/sessions/{session_id}", tags=["reports"])


@router.post("/report")
def generate_report(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found.", "details": {}})

    existing = db.query(Report).filter(Report.session_id == session.id).first()
    if existing:
        return {"report_id": str(existing.id), "status": "already_exists"}

    session.transition_to("REPORT_READY")
    questions = db.query(Question).filter(Question.session_id == session.id).order_by(Question.sequence).all()
    answer_ids = [q.id for q in questions]
    answers = db.query(Answer).filter(Answer.question_id.in_(answer_ids)).all() if answer_ids else []
    resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
    resume_signals = {
        "extracted_skills": resume.extracted_skills if resume else [],
    }

    data = ReportBuilderService().build(session, questions, answers, resume_signals, db=db)

    report = Report(
        session_id=session.id,
        topics_covered=data["topics_covered"],
        insights=data["insights"],
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {"report_id": str(report.id), "status": "generated"}


@router.get("/report", response_model=ReportResponse)
def get_report(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found.", "details": {}})

    report = db.query(Report).filter(Report.session_id == session.id).first()
    if not report:
        raise HTTPException(404, detail={"error_code": "REPORT_NOT_FOUND", "message": "Report not yet generated for this session.", "details": {}})

    questions = db.query(Question).filter(Question.session_id == session.id).order_by(Question.sequence).all()
    answer_ids = [q.id for q in questions]
    answers = db.query(Answer).filter(Answer.question_id.in_(answer_ids)).all() if answer_ids else []
    resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
    resume_signals = {
        "extracted_skills": resume.extracted_skills if resume else [],
    }

    data = ReportBuilderService().build(session, questions, answers, resume_signals, db=db)
    return ReportResponse(**data)
