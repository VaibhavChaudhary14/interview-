import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession
from app.db.session import get_db
from app.models.session import Session
from app.services.consent import ConsentService
from app.schemas.consent import ConsentSubmitRequest, ConsentResponse, ConsentActiveVersionResponse

router = APIRouter(prefix="/sessions/{session_id}/consent", tags=["consent"])


@router.post("", response_model=ConsentResponse, status_code=201)
def record_session_consent(
    session_id: str,
    body: ConsentSubmitRequest,
    request: Request,
    db: DBSession = Depends(get_db),
):
    session = db.query(Session).filter(Session.id == uuid.UUID(session_id)).first()
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "SESSION_NOT_FOUND",
                "message": "No session found with the given id.",
                "details": {},
            },
        )

    # Get client IP address
    ip_address = request.client.host if request.client else None

    try:
        consent = ConsentService.record_consent(
            db=db,
            session_id=str(session.id),
            consent_text_version=body.consent_text_version,
            audio_recording_allowed=body.audio_recording_allowed,
            ip_address=ip_address,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_CONSENT_VERSION",
                "message": str(e),
                "details": {},
            },
        )

    return ConsentResponse(
        consent_id=str(consent.id),
        session_id=str(consent.session_id),
        consent_text_version=consent.consent_text_version,
        audio_recording_allowed=consent.audio_recording_allowed,
        granted_at=consent.granted_at,
        ip_address=consent.ip_address,
    )


@router.get("", response_model=ConsentResponse)
def get_session_consent(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == uuid.UUID(session_id)).first()
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "SESSION_NOT_FOUND",
                "message": "No session found with the given id.",
                "details": {},
            },
        )

    consent = ConsentService.get_consent_for_session(db, str(session.id))
    if not consent:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "CONSENT_NOT_FOUND",
                "message": "No consent record found for this session.",
                "details": {},
            },
        )

    return ConsentResponse(
        consent_id=str(consent.id),
        session_id=str(consent.session_id),
        consent_text_version=consent.consent_text_version,
        audio_recording_allowed=consent.audio_recording_allowed,
        granted_at=consent.granted_at,
        ip_address=consent.ip_address,
    )


@router.get("/active-version", response_model=ConsentActiveVersionResponse)
def get_active_consent_version(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == uuid.UUID(session_id)).first()
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "SESSION_NOT_FOUND",
                "message": "No session found with the given id.",
                "details": {},
            },
        )

    active_policy = ConsentService.get_active_version(db)
    if not active_policy:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "ACTIVE_VERSION_NOT_FOUND",
                "message": "No active consent policy version found.",
                "details": {},
            },
        )

    return ConsentActiveVersionResponse(
        version=active_policy.version,
        consent_text=active_policy.consent_text,
    )
