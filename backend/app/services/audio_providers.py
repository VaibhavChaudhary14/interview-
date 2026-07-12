import logging
import base64
import time
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


# ── STT Providers ─────────────────────────────────────────────────────────────

class BaseSTTProvider:
    def transcribe(self, file_content: bytes, filename: str) -> str:
        raise NotImplementedError


class SyncPollExhausted(Exception):
    def __init__(self, transcript_id: str):
        super().__init__(f"Sync polling exhausted for job {transcript_id}")
        self.transcript_id = transcript_id


class AssemblyAIProvider(BaseSTTProvider):
    def transcribe(self, file_content: bytes, filename: str, db=None, answer_id=None) -> str:
        if not settings.assemblyai_api_key:
            raise ValueError("AssemblyAI API key is missing.")

        logger.info("AssemblyAI: Uploading file...")
        upload_resp = httpx.post(
            "https://api.assemblyai.com/v2/upload",
            headers={
                "Authorization": settings.assemblyai_api_key,
                "Content-Type": "application/octet-stream",
            },
            content=file_content,
            timeout=30.0,
        )
        if upload_resp.status_code != 200:
            raise Exception(f"AssemblyAI upload failed: {upload_resp.text}")

        upload_url = upload_resp.json()["upload_url"]
        logger.info(f"AssemblyAI: Uploaded successfully. URL: {upload_url}")

        # Build request json payload
        payload = {
            "audio_url": upload_url,
            "speech_models": ["universal-3-5-pro", "universal-2"],
        }
        if settings.base_webhook_url:
            payload["webhook_url"] = f"{settings.base_webhook_url}/api/v1/webhooks/assemblyai/transcript"

        # Submit transcription request
        submit_resp = httpx.post(
            "https://api.assemblyai.com/v2/transcript",
            headers={
                "Authorization": settings.assemblyai_api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10.0,
        )
        if submit_resp.status_code != 200:
            raise Exception(f"AssemblyAI submission failed: {submit_resp.text}")

        transcript_id = submit_resp.json()["id"]
        logger.info(f"AssemblyAI: Submitted job {transcript_id}. Webhook URL configured: {settings.base_webhook_url}")

        if db is not None and answer_id is not None:
            try:
                import uuid
                from app.models.transcription_job import TranscriptionJob
                job = TranscriptionJob(
                    id=uuid.uuid4(),
                    job_id=transcript_id,
                    answer_id=uuid.UUID(str(answer_id)),
                    status="pending",
                    sync_poll_exhausted=False,
                )
                db.add(job)
                db.commit()
            except Exception as e:
                logger.error(f"AssemblyAI: Failed to create TranscriptionJob record: {e}")

        # Poll status: 5 attempts x 3 seconds (total 15s)
        for attempt in range(5):
            time.sleep(3.0)
            logger.info(f"AssemblyAI: Sync polling attempt {attempt + 1}/5 for job {transcript_id}...")
            poll_resp = httpx.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers={"Authorization": settings.assemblyai_api_key},
                timeout=10.0,
            )
            if poll_resp.status_code != 200:
                raise Exception(f"AssemblyAI polling failed: {poll_resp.text}")

            status_data = poll_resp.json()
            status = status_data.get("status")
            if status == "completed":
                logger.info("AssemblyAI: Transcription completed synchronously.")
                text = status_data.get("text", "")
                if db is not None:
                    try:
                        from app.models.transcription_job import TranscriptionJob
                        job = db.query(TranscriptionJob).filter_by(job_id=transcript_id).first()
                        if job:
                            job.status = "completed"
                            db.commit()
                    except Exception as e:
                        logger.error(f"AssemblyAI: Failed to update job to completed: {e}")
                return text
            elif status == "error":
                err_msg = status_data.get("error", "Unknown error")
                if db is not None:
                    try:
                        from app.models.transcription_job import TranscriptionJob
                        job = db.query(TranscriptionJob).filter_by(job_id=transcript_id).first()
                        if job:
                            job.status = "error"
                            job.error_message = err_msg
                            db.commit()
                    except Exception as e:
                        logger.error(f"AssemblyAI: Failed to update job to error: {e}")
                raise Exception(f"AssemblyAI job error: {err_msg}")

        # If sync polling exhausted, mark in DB and raise SyncPollExhausted
        if db is not None:
            try:
                from app.models.transcription_job import TranscriptionJob
                job = db.query(TranscriptionJob).filter_by(job_id=transcript_id).first()
                if job:
                    job.sync_poll_exhausted = True
                    db.commit()
            except Exception as e:
                logger.error(f"AssemblyAI: Failed to update job to exhausted: {e}")

        logger.info(f"AssemblyAI: Sync polling exhausted for job {transcript_id}. Switching to async webhook path.")
        raise SyncPollExhausted(transcript_id)


class ElevenLabsSTTProvider(BaseSTTProvider):
    def transcribe(self, file_content: bytes, filename: str) -> str:
        if not settings.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key is missing.")

        logger.info("ElevenLabs STT: Requesting transcription...")
        files = {"file": (filename, file_content, "audio/webm")}
        data = {"model_id": "scribe_v2"}
        resp = httpx.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": settings.elevenlabs_api_key},
            files=files,
            data=data,
            timeout=30.0,
        )
        if resp.status_code != 200:
            raise Exception(f"ElevenLabs STT failed with status {resp.status_code}: {resp.text}")

        logger.info("ElevenLabs STT: Transcription completed.")
        return resp.json().get("text", "")


class SarvamSTTProvider(BaseSTTProvider):
    def transcribe(self, file_content: bytes, filename: str) -> str:
        if not settings.sarvam_api_key:
            raise ValueError("Sarvam AI API key is missing.")

        logger.info("Sarvam STT: Requesting transcription...")
        files = {"file": (filename, file_content, "audio/webm")}
        data = {"model": "saaras:v3", "mode": "transcribe"}

        # Try primary key
        resp = httpx.post(
            "https://api.sarvam.ai/speech-to-text",
            headers={"api-subscription-key": settings.sarvam_api_key},
            files=files,
            data=data,
            timeout=30.0,
        )
        if resp.status_code != 200 and settings.sarvam_api_key_fallback:
            logger.warning("Sarvam STT: Primary key failed. Retrying with fallback key...")
            resp = httpx.post(
                "https://api.sarvam.ai/speech-to-text",
                headers={"api-subscription-key": settings.sarvam_api_key_fallback},
                files=files,
                data=data,
                timeout=30.0,
            )

        if resp.status_code != 200:
            raise Exception(f"Sarvam STT failed with status {resp.status_code}: {resp.text}")

        logger.info("Sarvam STT: Transcription completed.")
        return resp.json().get("transcript", "")


# ── TTS Providers ─────────────────────────────────────────────────────────────

class BaseTTSProvider:
    def generate_speech(self, text: str, language_code: str = "en-US") -> bytes:
        raise NotImplementedError


class ElevenLabsTTSProvider(BaseTTSProvider):
    def generate_speech(self, text: str, language_code: str = "en-US") -> bytes:
        if not settings.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key is missing.")

        logger.info("ElevenLabs TTS: Generating speech...")
        resp = httpx.post(
            "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM",
            headers={
                "xi-api-key": settings.elevenlabs_api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
            },
            timeout=30.0,
        )
        if resp.status_code != 200:
            raise Exception(f"ElevenLabs TTS failed: {resp.text}")

        return resp.content


class SarvamTTSProvider(BaseTTSProvider):
    def generate_speech(self, text: str, language_code: str = "en-US") -> bytes:
        if not settings.sarvam_api_key:
            raise ValueError("Sarvam AI API key is missing.")

        logger.info("Sarvam TTS: Generating speech...")
        lang_code = "hi-IN" if language_code.startswith("hi") else "en-IN"

        # Try primary key
        resp = httpx.post(
            "https://api.sarvam.ai/text-to-speech",
            headers={
                "api-subscription-key": settings.sarvam_api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model": "bulbul:v3",
                "target_language_code": lang_code,
                "speaker": "shubh",
            },
            timeout=30.0,
        )
        if resp.status_code != 200 and settings.sarvam_api_key_fallback:
            logger.warning("Sarvam TTS: Primary key failed. Retrying with fallback key...")
            resp = httpx.post(
                "https://api.sarvam.ai/text-to-speech",
                headers={
                    "api-subscription-key": settings.sarvam_api_key_fallback,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model": "bulbul:v3",
                    "target_language_code": lang_code,
                    "speaker": "shubh",
                },
                timeout=30.0,
            )

        if resp.status_code != 200:
            raise Exception(f"Sarvam TTS failed: {resp.text}")

        data = resp.json()
        audios = data.get("audios", [])
        if not audios:
            raise Exception("Sarvam TTS returned empty audio list.")

        return base64.b64decode(audios[0])
