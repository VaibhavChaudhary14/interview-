import time
import logging
from app.core.config import settings
from app.services.audio_providers import (
    ElevenLabsTTSProvider,
    SarvamTTSProvider,
)
from app.models.provider_usage import ProviderUsage

logger = logging.getLogger(__name__)


class TTSService:
    @classmethod
    def text_to_speech(cls, text: str, language_code: str = "en-US", db=None) -> tuple[bytes, str]:
        """
        Convert text to speech using TTS providers in order of priority:
        1. ElevenLabs
        2. Sarvam AI
        3. Local/Mock fallback (returns simulated WAV audio bytes)

        Returns a tuple: (audio_bytes, provider_name)
        """
        # 1. Try ElevenLabs
        if settings.elevenlabs_api_key:
            start_time = time.time()
            try:
                provider = ElevenLabsTTSProvider()
                audio_bytes = provider.generate_speech(text, language_code)
                duration = time.time() - start_time
                ProviderUsage.record_usage(db, "elevenlabs", duration)
                if audio_bytes:
                    return audio_bytes, "elevenlabs"
            except Exception as e:
                duration = time.time() - start_time
                logger.warning(f"ElevenLabs TTS failed, trying next provider. Error: {e}")

        # 2. Try Sarvam AI
        if settings.sarvam_api_key:
            start_time = time.time()
            try:
                provider = SarvamTTSProvider()
                audio_bytes = provider.generate_speech(text, language_code)
                duration = time.time() - start_time
                ProviderUsage.record_usage(db, "sarvam", duration)
                if audio_bytes:
                    return audio_bytes, "sarvam"
            except Exception as e:
                duration = time.time() - start_time
                logger.warning(f"Sarvam TTS failed. Error: {e}")

        # 3. Safe Mock Fallback (returns a minimal valid 44-byte silent WAV)
        logger.error("All TTS providers failed or were unconfigured. Returning mock wave bytes.")
        mock_wav = (
            b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00"
            b"\x02\x00\x10\x00data\x00\x00\x00\x00"
        )
        return mock_wav, "mock"
