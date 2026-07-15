"""
Tests for TTS character-count usage tracking (Phase 0 cleanup — A.1).

Verifies that TTS calls log input character count in provider_usage, not
audio generation latency in seconds (the bug that existed before this fix).
"""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.provider_usage import ProviderUsage


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_tts_usage_logged_by_character_count(db_session):
    """
    TTS usage must track characters of input text, not seconds of generation.
    ElevenLabs and Sarvam both price TTS per character.
    """
    test_text = "Hello, this is a test sentence."  # 31 chars
    char_count = len(test_text)

    ProviderUsage.record_tts_usage(db_session, "elevenlabs", char_count)

    row = (
        db_session.query(ProviderUsage)
        .filter_by(provider="elevenlabs", call_type="tts")
        .first()
    )
    assert row is not None, "Expected a provider_usage row for TTS call"
    assert row.call_type == "tts"
    assert row.total_characters == char_count, (
        f"Expected total_characters={char_count}, got {row.total_characters}"
    )
    assert row.total_seconds == 0.0, (
        "TTS rows must not increment total_seconds (that field is for STT)"
    )
    assert row.call_count == 1


def test_tts_usage_accumulates_across_calls(db_session):
    """Multiple TTS calls on the same day accumulate in one row per provider."""
    ProviderUsage.record_tts_usage(db_session, "elevenlabs", 20)
    ProviderUsage.record_tts_usage(db_session, "elevenlabs", 15)

    row = (
        db_session.query(ProviderUsage)
        .filter_by(provider="elevenlabs", call_type="tts")
        .first()
    )
    assert row.total_characters == 35
    assert row.call_count == 2


def test_stt_and_tts_rows_are_separate(db_session):
    """STT and TTS for the same provider are stored in separate rows."""
    ProviderUsage.record_usage(db_session, "elevenlabs", 5.5)  # STT (seconds)
    ProviderUsage.record_tts_usage(db_session, "elevenlabs", 42)  # TTS (chars)

    rows = db_session.query(ProviderUsage).filter_by(provider="elevenlabs").all()
    assert len(rows) == 2

    call_types = {r.call_type for r in rows}
    assert call_types == {"stt", "tts"}

    stt_row = next(r for r in rows if r.call_type == "stt")
    tts_row = next(r for r in rows if r.call_type == "tts")
    assert stt_row.total_seconds == pytest.approx(5.5)
    assert tts_row.total_characters == 42


def test_tts_service_calls_record_tts_usage(db_session):
    """
    Integration: TTSService.text_to_speech() must call record_tts_usage,
    not record_usage (the STT method).
    """
    from app.services.tts import TTSService

    with patch("app.services.tts.ElevenLabsTTSProvider") as MockProvider:
        mock_instance = MagicMock()
        mock_instance.generate_speech.return_value = b"fake_audio"
        MockProvider.return_value = mock_instance

        # Patch settings to think elevenlabs key is present
        with patch("app.services.tts.settings") as mock_settings:
            mock_settings.elevenlabs_api_key = "test_key"
            mock_settings.sarvam_api_key = None

            text = "Test text for TTS"
            TTSService.text_to_speech(text, db=db_session)

    row = (
        db_session.query(ProviderUsage)
        .filter_by(provider="elevenlabs", call_type="tts")
        .first()
    )
    assert row is not None, "TTSService must create a TTS usage row"
    assert row.total_characters == len(text)
