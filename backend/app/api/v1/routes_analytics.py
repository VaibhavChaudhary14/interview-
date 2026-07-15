import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession
from app.db.session import get_db
from app.models.session import Session
from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreateRequest, FeedbackResponse

router = APIRouter()


@router.post("/sessions/{session_id}/feedback", response_model=FeedbackResponse)
def submit_session_feedback(
    session_id: str,
    body: FeedbackCreateRequest,
    db: DBSession = Depends(get_db)
):
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error_code": "INVALID_UUID", "message": "Invalid session ID format."})

    # 1. Verify session exists
    session = db.query(Session).filter(Session.id == session_uuid).first()
    if not session:
        raise HTTPException(status_code=404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found."})

    # 2. Check if feedback already submitted
    existing = db.query(Feedback).filter(Feedback.session_id == session_uuid).first()
    if existing:
        raise HTTPException(status_code=409, detail={"error_code": "FEEDBACK_ALREADY_EXISTS", "message": "Feedback already submitted for this session."})

    # 3. Create feedback
    fb = Feedback(
        session_id=session_uuid,
        rating_realistic=body.rating_realistic,
        rating_feedback=body.rating_feedback,
        comments=body.comments
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    return FeedbackResponse(
        id=str(fb.id),
        session_id=str(fb.session_id),
        rating_realistic=fb.rating_realistic,
        rating_feedback=fb.rating_feedback,
        comments=fb.comments,
        created_at=fb.created_at.isoformat()
    )


@router.get("/analytics/overview")
def get_analytics_overview(
    days: int = 7,
    db: DBSession = Depends(get_db)
):
    if days <= 0:
        raise HTTPException(status_code=400, detail={"error_code": "INVALID_DAYS", "message": "Days query parameter must be a positive integer."})

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # 1. Funnel Statistics inside the time window
    funnel_rows = (
        db.query(Session.status, func.count(Session.id))
        .filter(Session.created_at >= start_date)
        .group_by(Session.status)
        .all()
    )
    funnel = {status: 0 for status in ["CREATED", "PROCESSING_RESUME", "CONTEXT_BUILT", "RETRIEVING", "IN_PROGRESS", "COMPLETED", "REPORT_READY"]}
    for status, count in funnel_rows:
        if status in funnel:
            funnel[status] = count
        else:
            funnel[status] = count  # track other custom statuses dynamically if any

    # 2. Mid-Interview Drop-offs (sessions that stayed in IN_PROGRESS grouped by questions_asked)
    in_progress_rows = (
        db.query(Session.questions_asked, func.count(Session.id))
        .filter(Session.created_at >= start_date)
        .filter(Session.status == "IN_PROGRESS")
        .group_by(Session.questions_asked)
        .all()
    )
    mid_interview_dropoffs = {str(q): 0 for q in range(1, 8)}  # 1 to 7
    for q_asked, count in in_progress_rows:
        q_key = str(q_asked)
        if q_key in mid_interview_dropoffs:
            mid_interview_dropoffs[q_key] = count
        else:
            mid_interview_dropoffs[q_key] = mid_interview_dropoffs.get(q_key, 0) + count

    # 3. Unclassified Custom Roles inside the time window
    unclassified_rows = (
        db.query(func.lower(Session.role), func.count(Session.id))
        .filter(Session.created_at >= start_date)
        .filter(Session.classification_method == "unclassified")
        .group_by(func.lower(Session.role))
        .order_by(func.count(Session.id).desc())
        .limit(20)
        .all()
    )
    unclassified_roles = [{"role": role, "count": count} for role, count in unclassified_rows]

    return {
        "time_window_days": days,
        "funnel": funnel,
        "mid_interview_dropoffs": mid_interview_dropoffs,
        "unclassified_roles": unclassified_roles
    }
