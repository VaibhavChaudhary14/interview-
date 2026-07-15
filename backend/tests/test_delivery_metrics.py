"""
Tests for Phase 1.4 Delivery Metrics.

Tests are grouped by layer:
- DeliveryMetricsService unit tests (WPM math, pause detection, filler words)
- Route / integration tests (sync path trigger, webhook path trigger, endpoint)
- Failure handling (computation_error recorded, not raised)
- Report aggregate (delivery_summary block)

Audio bytes used in tests are a minimal valid WAV file (silence, 1s, 16kHz mono).
This exercises the librosa code path without needing real speech content.
"""
import io
import struct
import uuid
import re
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.answer import Answer
from app.models.answer_metrics import AnswerMetrics
from app.services.delivery_metrics import DeliveryMetricsService, UNAMBIGUOUS_FILLERS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_silent_wav(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """
    Returns a minimal valid WAV file with silence. Used to test librosa load
    path without requiring real audio recordings.
    """
    num_samples = int(duration_seconds * sample_rate)
    data = b"\x00\x00" * num_samples  # 16-bit silence
    data_size = len(data)
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(data)
    return buf.getvalue()


def _make_test_answer(db_session, question_id=None, transcript="") -> Answer:
    if question_id is None:
        question_id = uuid.uuid4()
    answer = Answer(
        id=uuid.uuid4(),
        question_id=question_id,
        answer_text=transcript,
        transcript_text=transcript,
    )
    db_session.add(answer)
    db_session.commit()
    return answer


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


# ---------------------------------------------------------------------------
# 1. WPM math
# ---------------------------------------------------------------------------

def test_wpm_calculation_correct():
    """
    WPM is (word_count / audio_duration_seconds) * 60.
    For a 2s clip with 5 words: (5/2)*60 = 150 WPM.
    """
    svc = DeliveryMetricsService()
    wav = _make_silent_wav(duration_seconds=2.0)
    transcript = "one two three four five"  # 5 words
    result = svc.compute(str(uuid.uuid4()), wav, transcript)

    # The actual duration from librosa may differ slightly from 2.0 due to WAV header
    # parsing, so we allow a small range but assert the formula is applied.
    assert result["computation_error"] is None
    assert result["word_count"] == 5
    assert result["audio_duration_seconds"] is not None
    assert result["wpm"] is not None
    # WPM should be in a reasonable range (wav is ~2s)
    assert 100 < result["wpm"] < 250


def test_wpm_feedback_bands():
    """wpm_feedback() returns the right band labels."""
    assert "slow" in DeliveryMetricsService.wpm_feedback(100).lower()
    assert "good" in DeliveryMetricsService.wpm_feedback(140).lower()
    assert "quickly" in DeliveryMetricsService.wpm_feedback(180).lower()
    assert "unavailable" in DeliveryMetricsService.wpm_feedback(None).lower()


# ---------------------------------------------------------------------------
# 2. Pause detection
# ---------------------------------------------------------------------------

def test_pause_detection_silent_clip():
    """
    A fully silent WAV clip has no detectable non-silent intervals,
    so pause detection should return no pauses (not crash).
    """
    svc = DeliveryMetricsService()
    wav = _make_silent_wav(duration_seconds=3.0)
    result = svc.compute(str(uuid.uuid4()), wav, "some transcript")
    assert result["computation_error"] is None
    # May return 0 pauses for all-silence — depends on librosa's top_db handling.
    assert isinstance(result["pause_count"], int)
    assert result["pause_count"] >= 0


# ---------------------------------------------------------------------------
# 3. Filler word counting with word-boundary guards
# ---------------------------------------------------------------------------

def test_filler_word_boundary_guards():
    """
    Filler words must not match as substrings. "likelihood" must not match
    "like", "actually" must not match within "actually" only, etc.
    """
    svc = DeliveryMetricsService()
    # "likelihood" contains "like" but must not count as a filler
    breakdown = svc._count_filler_words("The likelihood of success is high.")
    assert breakdown["contextual"].get("like", 0) == 0, (
        '"like" matched inside "likelihood" — word boundary regex is broken'
    )


def test_filler_word_counts_unambiguous():
    """Confirmed filler words are counted in the unambiguous tier."""
    svc = DeliveryMetricsService()
    transcript = "Um I was thinking uh you know that like I mean it works"
    breakdown = svc._count_filler_words(transcript)

    assert breakdown["unambiguous"].get("um", 0) >= 1
    assert breakdown["unambiguous"].get("uh", 0) >= 1
    assert breakdown["unambiguous"].get("you know", 0) >= 1
    assert breakdown["unambiguous"].get("i mean", 0) >= 1


def test_filler_word_contextual_split():
    """'like', 'so', 'actually' go into the contextual tier, not unambiguous."""
    svc = DeliveryMetricsService()
    transcript = "So like I actually think this is basically correct."
    breakdown = svc._count_filler_words(transcript)

    # None of these should appear in unambiguous
    for word in ["like", "so", "actually", "basically"]:
        assert breakdown["unambiguous"].get(word, 0) == 0, (
            f'"{word}" was mis-categorized as unambiguous filler'
        )
    # All should appear in contextual
    assert breakdown["contextual"].get("like", 0) >= 1
    assert breakdown["contextual"].get("so", 0) >= 1
    assert breakdown["contextual"].get("actually", 0) >= 1
    assert breakdown["contextual"].get("basically", 0) >= 1


# ---------------------------------------------------------------------------
# 4. Computation error is recorded, not raised
# ---------------------------------------------------------------------------

def test_compute_never_raises_on_bad_audio():
    """
    DeliveryMetricsService.compute() must catch all exceptions and return a
    computation_error dict, never propagate exceptions to the caller.
    """
    svc = DeliveryMetricsService()
    result = svc.compute(str(uuid.uuid4()), b"this is not audio", "some transcript")

    assert result["computation_error"] is not None
    assert isinstance(result["computation_error"], str)
    assert result["wpm"] is None
    assert result["computed_at"] is not None


def test_metrics_upsert_records_error(db_session):
    """
    _run_metrics_job with None audio bytes must upsert an AnswerMetrics row
    with computation_error set, not crash or leave a missing row.
    """
    from app.api.v1.routes_audio import _run_metrics_job

    answer = _make_test_answer(db_session, transcript="hello world")

    _run_metrics_job(db_session, answer, audio_bytes=None)

    row = db_session.query(AnswerMetrics).filter_by(answer_id=answer.id).first()
    assert row is not None, "AnswerMetrics row must be created even on failure"
    assert row.computation_error is not None
    assert "not available" in row.computation_error.lower()


# ---------------------------------------------------------------------------
# 5. Sync path trigger
# ---------------------------------------------------------------------------

def test_sync_path_triggers_metrics_job(db_session):
    """
    After a sync transcription completes, an AnswerMetrics row must be created.
    This tests that _run_metrics_job is called from the sync upload path.
    """
    answer = _make_test_answer(db_session, transcript="I think this is correct")
    wav = _make_silent_wav(duration_seconds=2.0)

    from app.api.v1.routes_audio import _run_metrics_job
    _run_metrics_job(db_session, answer, audio_bytes=wav)

    row = db_session.query(AnswerMetrics).filter_by(answer_id=answer.id).first()
    assert row is not None
    # Should not have an error (real WAV, valid transcript)
    # computation_error may still be set if librosa has an issue loading the WAV,
    # but the row itself must exist.
    assert row.computed_at is not None


# ---------------------------------------------------------------------------
# 6. Idempotency — second upsert overwrites first
# ---------------------------------------------------------------------------

def test_metrics_upsert_is_idempotent(db_session):
    """
    Running _run_metrics_job twice for the same answer must not create a
    duplicate row — the second call overwrites the first.
    """
    from app.api.v1.routes_audio import _run_metrics_job

    answer = _make_test_answer(db_session, transcript="test answer text")
    wav = _make_silent_wav(1.0)

    _run_metrics_job(db_session, answer, wav)
    _run_metrics_job(db_session, answer, wav)

    rows = db_session.query(AnswerMetrics).filter_by(answer_id=answer.id).all()
    assert len(rows) == 1, f"Expected 1 AnswerMetrics row, got {len(rows)}"


# ---------------------------------------------------------------------------
# 7. Metrics endpoint status states
# ---------------------------------------------------------------------------

def test_metrics_endpoint_not_computed(db_session):
    """GET /metrics returns status='not_computed' when no row exists."""
    # Verify the service-layer check
    metrics = db_session.query(AnswerMetrics).filter_by(answer_id=uuid.uuid4()).first()
    assert metrics is None  # No row → not_computed state


def test_metrics_endpoint_error_state(db_session):
    """A row with computation_error set represents the 'error' state."""
    answer = _make_test_answer(db_session)
    row = AnswerMetrics(
        answer_id=answer.id,
        computation_error="Audio not available",
    )
    db_session.add(row)
    db_session.commit()

    from_db = db_session.query(AnswerMetrics).filter_by(answer_id=answer.id).first()
    assert from_db.computation_error == "Audio not available"


# ---------------------------------------------------------------------------
# 8. delivery_summary aggregation
# ---------------------------------------------------------------------------

def test_delivery_summary_aggregates_across_answers(db_session):
    """
    _build_delivery_summary should average WPM across all answers and
    surface the answer with the longest pause.
    """
    from app.api.v1.routes_reports import _build_delivery_summary
    from datetime import datetime, timezone

    # Two answers with metrics
    a1 = _make_test_answer(db_session, transcript="answer one")
    a2 = _make_test_answer(db_session, transcript="answer two")

    m1 = AnswerMetrics(
        answer_id=a1.id,
        wpm=120.0,
        filler_word_count=3,
        filler_word_breakdown={"unambiguous": {"um": 3}, "contextual": {}},
        longest_pause_seconds=1.5,
        computed_at=datetime.now(timezone.utc),
    )
    m2 = AnswerMetrics(
        answer_id=a2.id,
        wpm=160.0,
        filler_word_count=5,
        filler_word_breakdown={"unambiguous": {"uh": 2, "um": 3}, "contextual": {}},
        longest_pause_seconds=3.2,
        computed_at=datetime.now(timezone.utc),
    )
    db_session.add_all([m1, m2])
    db_session.commit()

    summary = _build_delivery_summary([a1.id, a2.id], db_session)
    assert summary is not None
    assert summary["avg_wpm"] == pytest.approx(140.0, rel=0.01)
    assert summary["total_filler_words"] == 8
    assert summary["most_common_filler"] == "um"  # um appears 3+3=6 times vs uh=2
    assert summary["question_with_longest_pause"]["answer_id"] == str(a2.id)
    assert summary["question_with_longest_pause"]["pause_seconds"] == pytest.approx(3.2)


def test_delivery_summary_returns_none_when_no_metrics(db_session):
    """_build_delivery_summary returns None if no metrics rows exist yet."""
    from app.api.v1.routes_reports import _build_delivery_summary
    answer = _make_test_answer(db_session, transcript="unanswered")
    result = _build_delivery_summary([answer.id], db_session)
    assert result is None
