import os
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession
from app.db.session import get_db
from app.models.session import Session
from app.models.answer import Answer
from app.models.recording import Recording
from app.models.question import Question
from app.services.audio import AudioService

router = APIRouter(tags=["audio"])


@router.post("/sessions/{session_id}/questions/{question_id}/audio", status_code=201)
async def upload_answer_audio(
    session_id: str,
    question_id: str,
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
):
    session = db.query(Session).filter(Session.id == uuid.UUID(session_id)).first()
    if not session:
        raise HTTPException(status_code=404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found."})

    question = db.query(Question).filter(Question.id == uuid.UUID(question_id)).first()
    if not question:
        raise HTTPException(status_code=404, detail={"error_code": "QUESTION_NOT_FOUND", "message": "No question found."})

    answer = db.query(Answer).filter(Answer.question_id == question.id).first()
    if not answer:
        answer = Answer(
            id=uuid.uuid4(),
            question_id=question.id,
            answer_text="",
        )
        db.add(answer)
        db.commit()
        db.refresh(answer)

    # Read file content
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail={"error_code": "EMPTY_AUDIO", "message": "Audio file is empty."})

    # Upload recording
    recording = AudioService.upload_recording(
        db=db,
        session_id=str(session.id),
        answer_id=str(answer.id),
        file_content=content,
        consent_id=None,  # We can link from latest consent in future if needed
    )

    # Transcribe recording
    import logging
    logger = logging.getLogger(__name__)
    from app.services.transcription import TranscriptionService
    from app.services.audio_providers import SyncPollExhausted

    transcript = None
    provider = None
    message = "Transcribed successfully"
    status = "completed"
    try:
        transcript, provider = TranscriptionService.transcribe_audio(
            content,
            file.filename or "answer.webm",
            db=db,
            answer_id=answer.id,
        )
        answer.transcript_text = transcript
        answer.transcript_provider = provider
        if not answer.answer_text or answer.answer_text.strip() == "":
            answer.answer_text = transcript
    except SyncPollExhausted as e:
        logger.info(f"Sync polling exhausted for job {e.transcript_id}, falling back to webhook.")
        status = "pending"
        provider = "assemblyai"
        message = "Transcribing in background - we'll notify you when it's ready."
    except Exception as e:
        logger.exception("Failed to transcribe audio")
        message = "Could not transcribe; your answer was still recorded"
        status = "error"

    # Link answer back to recording
    answer.recording_id = recording.id
    db.commit()

    return {
        "recording_id": str(recording.id),
        "transcript": transcript,
        "provider": provider,
        "status": status,
        "message": message,
    }


@router.get("/sessions/{session_id}/recordings/{recording_id}/play")
def play_recording(
    session_id: str,
    recording_id: str,
    request: Request,
    user_id: str | None = None,
    db: DBSession = Depends(get_db),
):
    # Verify session exists
    session = db.query(Session).filter(Session.id == uuid.UUID(session_id)).first()
    if not session:
        raise HTTPException(status_code=404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found."})

    ip_address = request.client.host if request.client else None

    try:
        url = AudioService.generate_presigned_url(
            db=db,
            recording_id=recording_id,
            user_id=user_id,
            ip_address=ip_address,
        )
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=900)
        return {"url": url, "expires_at": expires_at.isoformat()}
    except ValueError as e:
        if "deleted" in str(e) or "not found" in str(e):
            raise HTTPException(status_code=404, detail={"error_code": "RECORDING_NOT_FOUND", "message": str(e)})
        raise HTTPException(status_code=400, detail={"error_code": "RECORDING_ERROR", "message": str(e)})


@router.delete("/sessions/{session_id}/recordings/{recording_id}")
def delete_recording(
    session_id: str,
    recording_id: str,
    db: DBSession = Depends(get_db),
):
    # Verify session exists
    session = db.query(Session).filter(Session.id == uuid.UUID(session_id)).first()
    if not session:
        raise HTTPException(status_code=404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found."})

    success = AudioService.delete_recording(db=db, recording_id=recording_id)
    if not success:
        raise HTTPException(status_code=404, detail={"error_code": "RECORDING_NOT_FOUND", "message": "Recording not found."})

    return {"status": "DELETED"}


@router.get("/audio/file/{recording_id}")
def serve_local_audio(recording_id: str, db: DBSession = Depends(get_db)):
    recording = db.query(Recording).filter(Recording.id == uuid.UUID(recording_id)).first()
    if not recording or recording.deletion_completed_at is not None or not recording.s3_key:
        raise HTTPException(status_code=404, detail={"error_code": "RECORDING_NOT_FOUND", "message": "Recording not found or deleted."})

    local_path = recording.s3_key
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail={"error_code": "FILE_NOT_FOUND", "message": "Audio file not found on disk."})

    return FileResponse(local_path, media_type="audio/wav")


@router.post("/sessions/{session_id}/tts")
def generate_tts(
    session_id: str,
    payload: dict,
    db: DBSession = Depends(get_db),
):
    session = db.query(Session).filter(Session.id == uuid.UUID(session_id)).first()
    if not session:
        raise HTTPException(status_code=404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found."})

    text = payload.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail={"error_code": "EMPTY_TEXT", "message": "Text payload is empty."})

    lang = payload.get("language_code", "en-US")
    from app.services.tts import TTSService
    audio_bytes, provider = TTSService.text_to_speech(text, lang, db=db)

    headers = {"X-TTS-Provider": provider}
    return Response(content=audio_bytes, media_type="audio/wav", headers=headers)


@router.post("/webhooks/assemblyai/transcript")
async def assemblyai_webhook(payload: dict, db: DBSession = Depends(get_db)):
    """
    AssemblyAI POSTs here when transcription completes (async completion path).
    Idempotent: if TranscriptionJob is already 'completed', this is a no-op.
    """
    job_id = payload.get("transcript_id") or payload.get("id")
    if not job_id:
        return {"ok": True}

    from app.models.transcription_job import TranscriptionJob
    job = db.query(TranscriptionJob).filter_by(job_id=job_id).first()
    if not job or job.status == "completed":
        return {"ok": True}

    status = payload.get("status")
    if status == "completed":
        job.status = "completed"
        job.webhook_received_at = datetime.now(timezone.utc).replace(tzinfo=None)

        text = payload.get("text")
        if not text:
            try:
                import httpx
                resp = httpx.get(
                    f"https://api.assemblyai.com/v2/transcript/{job_id}",
                    headers={"Authorization": settings.assemblyai_api_key},
                    timeout=10.0
                )
                if resp.status_code == 200:
                    text = resp.json().get("text", "")
            except Exception as e:
                logger.error(f"AssemblyAI Webhook: Failed to fetch full transcript: {e}")

        if text:
            answer = db.query(Answer).filter_by(id=job.answer_id).first()
            if answer:
                answer.transcript_text = text
                answer.transcript_provider = "assemblyai"
                if not answer.answer_text or answer.answer_text.strip() == "":
                    answer.answer_text = text
                db.commit()
    elif status == "error":
        job.status = "error"
        job.error_message = payload.get("error", "Unknown error")
        db.commit()

    return {"ok": True}


@router.get("/sessions/{session_id}/answers/{answer_id_or_question_id}/transcript-status")
async def get_transcript_status(session_id: str, answer_id_or_question_id: str, db: DBSession = Depends(get_db)):
    """Frontend polls this only when the initial upload response was 'pending'."""
    uid = uuid.UUID(answer_id_or_question_id)
    answer = db.query(Answer).filter(Answer.id == uid).first()
    if not answer:
        answer = db.query(Answer).filter(Answer.question_id == uid).first()

    if not answer:
        return {"status": "unknown"}

    if answer.transcript_text:
        return {"status": "completed", "transcript": answer.transcript_text}

    from app.models.transcription_job import TranscriptionJob
    job = db.query(TranscriptionJob).filter_by(answer_id=answer.id).order_by(
        TranscriptionJob.created_at.desc()
    ).first()
    return {"status": job.status if job else "unknown"}
