import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from app.db.session import get_db
from app.models.session import Session
from app.models.question import Question
from app.models.answer import Answer
from app.models.answer_metrics import AnswerMetrics
from app.models.report import Report
from app.models.resume import Resume
from app.models.feedback import Feedback
from app.services.report_builder import ReportBuilderService
from app.schemas.report import ReportResponse

router = APIRouter(prefix="/sessions/{session_id}", tags=["reports"])


def _build_delivery_summary(answer_ids: list, db: DBSession) -> dict | None:
    """
    Aggregate delivery metrics across all answers in a session.
    Returns None if no metrics rows exist yet (metrics not yet computed).
    Returns a partial dict if some answers have metrics and others don't.
    """
    if not answer_ids:
        return None

    metrics_rows = (
        db.query(AnswerMetrics)
        .filter(
            AnswerMetrics.answer_id.in_(answer_ids),
            AnswerMetrics.computation_error.is_(None),
            AnswerMetrics.wpm.isnot(None),
        )
        .all()
    )
    if not metrics_rows:
        return None

    # Average WPM across all answers with successful metrics
    wpms = [m.wpm for m in metrics_rows if m.wpm is not None]
    avg_wpm = round(sum(wpms) / len(wpms), 1) if wpms else None

    # Total filler words across all answers
    total_fillers = sum(
        (m.filler_word_count or 0) for m in metrics_rows
    )

    # Most common single filler word across all breakdown dicts
    filler_tally: dict[str, int] = {}
    for m in metrics_rows:
        breakdown = m.filler_word_breakdown or {}
        for tier in ("unambiguous", "contextual"):
            for word, count in (breakdown.get(tier) or {}).items():
                filler_tally[word] = filler_tally.get(word, 0) + count
    most_common_filler = max(filler_tally, key=filler_tally.get) if filler_tally else None

    # Question with the longest single pause
    worst_pause = None
    worst_pause_answer_id = None
    for m in metrics_rows:
        if m.longest_pause_seconds and (worst_pause is None or m.longest_pause_seconds > worst_pause):
            worst_pause = m.longest_pause_seconds
            worst_pause_answer_id = str(m.answer_id)

    return {
        "answers_with_metrics": len(metrics_rows),
        "avg_wpm": avg_wpm,
        "total_filler_words": total_fillers,
        "most_common_filler": most_common_filler,
        "question_with_longest_pause": {
            "answer_id": worst_pause_answer_id,
            "pause_seconds": worst_pause,
        } if worst_pause_answer_id else None,
    }


@router.post("/report")
def generate_report(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == uuid.UUID(session_id)).first()
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
    session = db.query(Session).filter(Session.id == uuid.UUID(session_id)).first()
    if not session:
        raise HTTPException(404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found.", "details": {}})

    report = db.query(Report).filter(Report.session_id == session.id).first()
    if not report:
        raise HTTPException(404, detail={"error_code": "REPORT_NOT_FOUND", "message": "Report not yet generated for this session.", "details": {}})

    questions = db.query(Question).filter(Question.session_id == session.id).order_by(Question.sequence).all()
    answer_ids_uuid = [q.id for q in questions]
    answers = db.query(Answer).filter(Answer.question_id.in_(answer_ids_uuid)).all() if answer_ids_uuid else []
    answer_ids = [a.id for a in answers]

    resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
    resume_signals = {
        "extracted_skills": resume.extracted_skills if resume else [],
    }

    data = ReportBuilderService().build(session, questions, answers, resume_signals, db=db)

    # Attach delivery summary — null if metrics haven't been computed yet
    data["delivery_summary"] = _build_delivery_summary(answer_ids, db)
    
    # Query if feedback exists
    data["has_feedback"] = db.query(Feedback).filter(Feedback.session_id == session.id).first() is not None

    return ReportResponse(**data)
