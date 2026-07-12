import uuid
from unittest.mock import patch
from app.services.transcription import TranscriptionService
from app.services.tts import TTSService
from app.models.session import Session


def test_transcription_service_failover():
    # Mock settings so all keys are active
    with patch("app.services.transcription.settings") as mock_settings:
        mock_settings.assemblyai_api_key = "dummy_assembly"
        mock_settings.elevenlabs_api_key = "dummy_eleven"
        mock_settings.sarvam_api_key = "dummy_sarvam"
        mock_settings.openai_api_key = "dummy_openai"

        # 1. AssemblyAI succeeds
        with patch("app.services.audio_providers.AssemblyAIProvider.transcribe", return_value="assembly text"):
            text, provider = TranscriptionService.transcribe_audio(b"audio bytes")
            assert text == "assembly text"
            assert provider == "assemblyai"

        # 2. AssemblyAI fails, ElevenLabs succeeds
        with patch("app.services.audio_providers.AssemblyAIProvider.transcribe", side_effect=Exception("Assembly error")), \
             patch("app.services.audio_providers.ElevenLabsSTTProvider.transcribe", return_value="eleven text"):
            text, provider = TranscriptionService.transcribe_audio(b"audio bytes")
            assert text == "eleven text"
            assert provider == "elevenlabs"

        # 3. Assembly & Eleven fail, Sarvam succeeds
        with patch("app.services.audio_providers.AssemblyAIProvider.transcribe", side_effect=Exception("Assembly error")), \
             patch("app.services.audio_providers.ElevenLabsSTTProvider.transcribe", side_effect=Exception("Eleven error")), \
             patch("app.services.audio_providers.SarvamSTTProvider.transcribe", return_value="sarvam text"):
            text, provider = TranscriptionService.transcribe_audio(b"audio bytes")
            assert text == "sarvam text"
            assert provider == "sarvam"

        # 4. Assembly, Eleven & Sarvam fail, Whisper succeeds
        with patch("app.services.audio_providers.AssemblyAIProvider.transcribe", side_effect=Exception("Assembly error")), \
             patch("app.services.audio_providers.ElevenLabsSTTProvider.transcribe", side_effect=Exception("Eleven error")), \
             patch("app.services.audio_providers.SarvamSTTProvider.transcribe", side_effect=Exception("Sarvam error")), \
             patch("openai.resources.audio.transcriptions.Transcriptions.create") as mock_whisper:
            mock_whisper.return_value.text = "whisper text"
            text, provider = TranscriptionService.transcribe_audio(b"audio bytes")
            assert text == "whisper text"
            assert provider == "whisper"

        # 5. All fail, returns mock
        with patch("app.services.audio_providers.AssemblyAIProvider.transcribe", side_effect=Exception("Assembly error")), \
             patch("app.services.audio_providers.ElevenLabsSTTProvider.transcribe", side_effect=Exception("Eleven error")), \
             patch("app.services.audio_providers.SarvamSTTProvider.transcribe", side_effect=Exception("Sarvam error")), \
             patch("openai.resources.audio.transcriptions.Transcriptions.create", side_effect=Exception("Whisper error")):
            text, provider = TranscriptionService.transcribe_audio(b"audio bytes")
            assert "mock fallback" in text.lower()
            assert provider == "mock"


def test_tts_service_failover():
    with patch("app.services.tts.settings") as mock_settings:
        mock_settings.elevenlabs_api_key = "dummy_eleven"
        mock_settings.sarvam_api_key = "dummy_sarvam"

        # 1. ElevenLabs succeeds
        with patch("app.services.audio_providers.ElevenLabsTTSProvider.generate_speech", return_value=b"eleven audio"):
            audio, provider = TTSService.text_to_speech("hello")
            assert audio == b"eleven audio"
            assert provider == "elevenlabs"

        # 2. ElevenLabs fails, Sarvam succeeds
        with patch("app.services.audio_providers.ElevenLabsTTSProvider.generate_speech", side_effect=Exception("Eleven error")), \
             patch("app.services.audio_providers.SarvamTTSProvider.generate_speech", return_value=b"sarvam audio"):
            audio, provider = TTSService.text_to_speech("hello")
            assert audio == b"sarvam audio"
            assert provider == "sarvam"

        # 3. All fail, mock fallback
        with patch("app.services.audio_providers.ElevenLabsTTSProvider.generate_speech", side_effect=Exception("Eleven error")), \
             patch("app.services.audio_providers.SarvamTTSProvider.generate_speech", side_effect=Exception("Sarvam error")):
            audio, provider = TTSService.text_to_speech("hello")
            assert len(audio) > 0
            assert provider == "mock"


def test_tts_endpoint(client, db_session):
    # Pre-create a session
    sess = Session(
        id=uuid.uuid4(),
        role="Backend Engineer",
        mode="self_prep",
    )
    db_session.add(sess)
    db_session.commit()

    with patch("app.services.tts.TTSService.text_to_speech", return_value=(b"wav bytes", "elevenlabs")):
        resp = client.post(
            f"/api/v1/sessions/{sess.id}/tts",
            json={"text": "Hello world", "language_code": "en-US"},
        )
        assert resp.status_code == 200
        assert resp.content == b"wav bytes"
        assert resp.headers.get("X-TTS-Provider") == "elevenlabs"
