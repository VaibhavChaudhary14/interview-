import os
import uuid
import logging
import tempfile
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession
from app.db.session import get_db
from app.models.session import Session
from app.models.answer import Answer
from app.models.recording import Recording
from app.models.question import Question
from app.models.answer_metrics import AnswerMetrics
from app.services.audio import AudioService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["audio"])


# ---------------------------------------------------------------------------
# Delivery Metrics Job
# ---------------------------------------------------------------------------

def _upsert_metrics(db: DBSession, answer_id, result: dict):
    """
    Get-or-create an AnswerMetrics row and set all fields from `result`.
    Idempotent: retrying after a transient failure overwrites the previous row.
    """
    existing = db.query(AnswerMetrics).filter_by(answer_id=answer_id).first()
    if existing:
        for key, value in result.items():
            setattr(existing, key, value)
    else:
        db.add(AnswerMetrics(answer_id=answer_id, **result))
    db.commit()


def _run_metrics_job(db: DBSession, answer: Answer, audio_bytes: bytes | None):
    """
    Compute and persist delivery metrics for a completed answer.

    Called synchronously from both the sync STT completion path and the
    AssemblyAI webhook path. At ~0.5s per 2-min answer this is fast enough
    to run inline. Move to FastAPI BackgroundTasks in Phase 2 if needed.

    If audio_bytes is None (recording deleted before webhook arrived, or S3
    error), records computation_error instead of crashing — the answer and
    transcript are unaffected.
    """
    from app.services.delivery_metrics import DeliveryMetricsService

    if not audio_bytes:
        _upsert_metrics(db, answer.id, {
            "computation_error": "Audio not available for metrics computation",
            "computed_at": datetime.now(timezone.utc),
        })
        return

    transcript = answer.transcript_text or answer.answer_text or ""
    result = DeliveryMetricsService().compute(str(answer.id), audio_bytes, transcript)
    _upsert_metrics(db, answer.id, result)


# ---------------------------------------------------------------------------
# Audio upload + transcription
# ---------------------------------------------------------------------------

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
        consent_id=None,
    )

    # Transcribe recording
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

    # ── Sync path metrics trigger ──────────────────────────────────────────
    # Only runs when transcription completed synchronously. Webhook path has
    # its own trigger in assemblyai_webhook() below.
    if status == "completed":
        try:
            _run_metrics_job(db, answer, content)
        except Exception as exc:
            # Metrics failure must never fail the upload response.
            logger.warning("Metrics job failed for answer %s: %s", answer.id, exc)

    return {
        "recording_id": str(recording.id),
        "transcript": transcript,
        "provider": provider,
        "status": status,
        "message": message,
    }


# ---------------------------------------------------------------------------
# Delivery metrics endpoint
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/answers/{answer_id}/metrics")
def get_answer_metrics(session_id: str, answer_id: str, db: DBSession = Depends(get_db)):
    """
    Returns delivery metrics for a single answer.
    The frontend should poll this after upload until status == "ready" or "error".
    Metrics are computed asynchronously after transcription completes.
    """
    # Verify session exists (lightweight auth guard)
    session = db.query(Session).filter(Session.id == uuid.UUID(session_id)).first()
    if not session:
        raise HTTPException(status_code=404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found."})

    metrics = db.query(AnswerMetrics).filter_by(answer_id=uuid.UUID(answer_id)).first()
    if not metrics:
        return {"status": "not_computed"}

    if metrics.computation_error:
        return {"status": "error", "message": "Delivery metrics unavailable for this answer."}

    return {
        "status": "ready",
        "wpm": metrics.wpm,
        "word_count": metrics.word_count,
        "audio_duration_seconds": metrics.audio_duration_seconds,
        "pause_count": metrics.pause_count,
        "avg_pause_duration": metrics.avg_pause_duration,
        "longest_pause_seconds": metrics.longest_pause_seconds,
        "filler_word_count": metrics.filler_word_count,
        "filler_word_breakdown": metrics.filler_word_breakdown,
        "computed_at": metrics.computed_at.isoformat() if metrics.computed_at else None,
    }


# ---------------------------------------------------------------------------
# Recording playback / deletion
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/recordings/{recording_id}/play")
def play_recording(
    session_id: str,
    recording_id: str,
    request: Request,
    user_id: str | None = None,
    db: DBSession = Depends(get_db),
):
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


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# AssemblyAI webhook (async transcription completion path)
# ---------------------------------------------------------------------------

@router.post("/webhooks/assemblyai/transcript")
async def assemblyai_webhook(payload: dict, db: DBSession = Depends(get_db)):
    """
    AssemblyAI POSTs here when transcription completes (async completion path).
    Idempotent: if TranscriptionJob is already 'completed', this is a no-op.
    Metrics job is triggered here as well as in the sync path — both paths
    must trigger it or webhook-completed answers never get delivery metrics.
    """
    from app.core.config import settings as _settings

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
                    headers={"Authorization": _settings.assemblyai_api_key},
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

                # ── Webhook path metrics trigger ───────────────────────────
                # Audio bytes must come from AudioService to work in both S3
                # and local-storage modes — never read recording.s3_key raw.
                if answer.recording_id:
                    try:
                        audio_bytes = AudioService.read_recording_bytes(db, str(answer.recording_id))
                        _run_metrics_job(db, answer, audio_bytes)
                    except Exception as exc:
                        logger.warning(
                            "Webhook metrics job failed for answer %s: %s", answer.id, exc
                        )

    elif status == "error":
        job.status = "error"
        job.error_message = payload.get("error", "Unknown error")
        db.commit()

    return {"ok": True}


# ---------------------------------------------------------------------------
# Transcript status polling
# ---------------------------------------------------------------------------

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
