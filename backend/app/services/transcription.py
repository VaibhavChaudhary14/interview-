import io
import time
import logging
from openai import OpenAI
from app.core.config import settings
from app.services.audio_providers import (
    AssemblyAIProvider,
    ElevenLabsSTTProvider,
    SarvamSTTProvider,
    SyncPollExhausted,
)
from app.models.provider_usage import ProviderUsage

logger = logging.getLogger(__name__)


class TranscriptionService:
    @classmethod
    def transcribe_audio(
        cls,
        file_content: bytes,
        filename: str = "audio.webm",
        db=None,
        answer_id=None,
    ) -> tuple[str, str]:
        """
        Transcribe the given audio file content using STT providers in order of priority:
        1. AssemblyAI (Dual-path: sync poll with webhook fallback)
        2. ElevenLabs
        3. Sarvam AI
        4. OpenAI Whisper (fallback)
        5. Mock transcription (safe fallback)

        Returns a tuple: (transcript_text, provider_name)
        """
        # 1. Try AssemblyAI
        if settings.assemblyai_api_key:
            start_time = time.time()
            try:
                provider = AssemblyAIProvider()
                text = provider.transcribe(file_content, filename, db=db, answer_id=answer_id)
                duration = time.time() - start_time
                ProviderUsage.record_usage(db, "assemblyai", duration)
                if text:
                    return text, "assemblyai"
            except SyncPollExhausted:
                duration = time.time() - start_time
                ProviderUsage.record_usage(db, "assemblyai", duration)
                raise
            except Exception as e:
                duration = time.time() - start_time
                logger.warning(f"AssemblyAI STT failed, trying next provider. Error: {e}")

        # 2. Try ElevenLabs
        if settings.elevenlabs_api_key:
            start_time = time.time()
            try:
                provider = ElevenLabsSTTProvider()
                text = provider.transcribe(file_content, filename)
                duration = time.time() - start_time
                ProviderUsage.record_usage(db, "elevenlabs", duration)
                if text:
                    return text, "elevenlabs"
            except Exception as e:
                duration = time.time() - start_time
                logger.warning(f"ElevenLabs STT failed, trying next provider. Error: {e}")

        # 3. Try Sarvam AI
        if settings.sarvam_api_key:
            start_time = time.time()
            try:
                provider = SarvamSTTProvider()
                text = provider.transcribe(file_content, filename)
                duration = time.time() - start_time
                ProviderUsage.record_usage(db, "sarvam", duration)
                if text:
                    return text, "sarvam"
            except Exception as e:
                duration = time.time() - start_time
                logger.warning(f"Sarvam STT failed, trying next provider. Error: {e}")

        # 4. Try OpenAI Whisper (fallback)
        if settings.openai_api_key:
            start_time = time.time()
            try:
                client = OpenAI(api_key=settings.openai_api_key)
                audio_file = io.BytesIO(file_content)
                audio_file.name = filename
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )
                duration = time.time() - start_time
                ProviderUsage.record_usage(db, "whisper", duration)
                logger.info("Successfully transcribed audio using Whisper API.")
                return transcription.text, "whisper"
            except Exception as e:
                duration = time.time() - start_time
                logger.warning(f"Whisper STT failed. Error: {e}")

        # 5. Safe Fallback
        logger.error("All STT providers failed or were unconfigured. Returning mock transcription.")
        return "This is a simulated transcription of the audio response. (Mock fallback triggered)", "mock"
