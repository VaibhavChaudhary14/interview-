import os
import uuid
import tempfile
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.resume import Resume
from app.models.session import Session
from app.models.question import Question
from app.models.answer import Answer
from app.models.recording import Recording
from app.models.audit_log import AuditLog
from app.services.audio import AudioService


@pytest.fixture(scope="function", autouse=True)
def configure_test_audio_dir():
    # Use a temporary directory for local recordings during tests
    with tempfile.TemporaryDirectory() as tmpdir:
        original_local_dir = settings.recordings_local_dir
        settings.recordings_local_dir = tmpdir
        yield
        settings.recordings_local_dir = original_local_dir


def create_test_hierarchy(db_session, mode="self_prep"):
    resume = Resume(
        id=uuid.uuid4(),
        raw_text="Test resume content",
        extracted_skills=[],
        extracted_technologies=[],
        extracted_domains=[],
        years_experience_estimate=2,
    )
    db_session.add(resume)
    db_session.commit()

    session = Session(
        id=uuid.uuid4(),
        resume_id=resume.id,
        role="backend_engineer",
        mode=mode,
        status="IN_PROGRESS",
    )
    db_session.add(session)
    db_session.commit()

    question = Question(
        id=uuid.uuid4(),
        session_id=session.id,
        sequence=1,
        topic="API design",
        question_text="Explain REST principles.",
    )
    db_session.add(question)
    db_session.commit()

    answer = Answer(
        id=uuid.uuid4(),
        question_id=question.id,
        answer_text="REST is Representational State Transfer.",
        word_count=5,
    )
    db_session.add(answer)
    db_session.commit()

    return session, question, answer


def test_audio_service_upload_play_delete(db_session):
    session, question, answer = create_test_hierarchy(db_session)
    file_content = b"fake wav audio data"

    # 1. Test Upload
    recording = AudioService.upload_recording(
        db=db_session,
        session_id=str(session.id),
        answer_id=str(answer.id),
        file_content=file_content,
    )

    assert recording.id is not None
    assert recording.session_id == session.id
    assert recording.answer_id == answer.id
    assert os.path.exists(recording.s3_key)

    # Verify physical content matches
    with open(recording.s3_key, "rb") as f:
        assert f.read() == file_content

    # 2. Test Play / Presigned URL (Local fallback)
    url = AudioService.generate_presigned_url(
        db=db_session,
        recording_id=str(recording.id),
        user_id=None,
        ip_address="127.0.0.1",
    )

    assert url == f"/api/v1/audio/file/{recording.id}"

    # Verify audit log is recorded
    audit = db_session.query(AuditLog).filter(AuditLog.target_recording_id == recording.id).first()
    assert audit is not None
    assert audit.action == "GENERATE_PRESIGNED_URL"
    assert audit.ip_address == "127.0.0.1"

    # 3. Test Delete
    success = AudioService.delete_recording(db_session, str(recording.id))
    assert success is True

    db_session.refresh(recording)
    assert recording.deletion_completed_at is not None
    assert recording.s3_key is None
    # Verify local file is actually deleted
    assert not os.path.exists(url.split("/")[-1])

    # 4. Verify presigned URL cannot be generated after deletion
    with pytest.raises(ValueError, match="Recording has been deleted"):
        AudioService.generate_presigned_url(db_session, str(recording.id))


def test_retention_purging(db_session):
    # Setup 4 sessions:
    # 1. self_prep, recording created 31 days ago (should purge)
    # 2. self_prep, recording created 10 days ago (should NOT purge)
    # 3. agency, recording created 100 days ago (should NOT purge)
    # 4. agency with override=5, recording created 6 days ago (should purge)

    now = datetime.now(timezone.utc)

    # Session 1: self_prep, 31 days ago
    s1, _, a1 = create_test_hierarchy(db_session, mode="self_prep")
    r1 = AudioService.upload_recording(db_session, str(s1.id), str(a1.id), b"audio 1")
    r1.created_at = now - timedelta(days=31)

    # Session 2: self_prep, 10 days ago
    s2, _, a2 = create_test_hierarchy(db_session, mode="self_prep")
    r2 = AudioService.upload_recording(db_session, str(s2.id), str(a2.id), b"audio 2")
    r2.created_at = now - timedelta(days=10)

    # Session 3: agency, 100 days ago
    s3, _, a3 = create_test_hierarchy(db_session, mode="agency")
    r3 = AudioService.upload_recording(db_session, str(s3.id), str(a3.id), b"audio 3")
    r3.created_at = now - timedelta(days=100)

    # Session 4: agency with override=5, 6 days ago
    s4, _, a4 = create_test_hierarchy(db_session, mode="agency")
    s4.retention_days_override = 5
    r4 = AudioService.upload_recording(db_session, str(s4.id), str(a4.id), b"audio 4")
    r4.created_at = now - timedelta(days=6)

    db_session.commit()

    # Run purging
    purged_count = AudioService.delete_expired_recordings(db_session)
    assert purged_count == 2

    # Verify which recordings are deleted
    db_session.refresh(r1)
    db_session.refresh(r2)
    db_session.refresh(r3)
    db_session.refresh(r4)

    assert r1.deletion_completed_at is not None
    assert r2.deletion_completed_at is None
    assert r3.deletion_completed_at is None
    assert r4.deletion_completed_at is not None


def test_audio_endpoints(client, db_session):
    session, question, answer = create_test_hierarchy(db_session)

    # 1. Test POST upload endpoint
    file_data = b"uploaded audio wave bytes"
    resp = client.post(
        f"/api/v1/sessions/{session.id}/questions/{question.id}/audio",
        files={"file": ("recording.wav", file_data, "audio/wav")},
    )
    assert resp.status_code == 201
    data = resp.json()
    recording_id = data["recording_id"]
    assert recording_id is not None
    assert "transcript" in data
    assert "simulated transcription" in data["transcript"]

    # Verify link in answer model
    db_session.refresh(answer)
    assert str(answer.recording_id) == recording_id

    # 2. Test GET serve local file endpoint
    resp = client.get(f"/api/v1/audio/file/{recording_id}")
    assert resp.status_code == 200
    assert resp.content == file_data

    # 3. Test GET play endpoint
    resp = client.get(f"/api/v1/sessions/{session.id}/recordings/{recording_id}/play")
    assert resp.status_code == 200
    play_data = resp.json()
    assert play_data["url"] == f"/api/v1/audio/file/{recording_id}"
    assert "expires_at" in play_data

    # 4. Test DELETE endpoint
    resp = client.delete(f"/api/v1/sessions/{session.id}/recordings/{recording_id}")
    assert resp.status_code == 200
    assert resp.json() == {"status": "DELETED"}

    # 5. Verify serving local file returns 404 after deletion
    resp = client.get(f"/api/v1/audio/file/{recording_id}")
    assert resp.status_code == 404

    # 6. Verify play endpoint returns 404 after deletion
    resp = client.get(f"/api/v1/sessions/{session.id}/recordings/{recording_id}/play")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "RECORDING_NOT_FOUND"


def test_audio_upload_creates_stub_answer(client, db_session):
    # Setup test session and question, but do NOT create any answer row in database
    from app.models.resume import Resume
    from app.models.session import Session
    from app.models.question import Question

    resume = Resume(
        id=uuid.uuid4(),
        raw_text="Test resume",
        extracted_skills=[],
        extracted_technologies=[],
        years_experience_estimate=2,
    )
    db_session.add(resume)
    db_session.commit()

    session = Session(
        id=uuid.uuid4(),
        resume_id=resume.id,
        role="backend_engineer",
        mode="self_prep",
        status="IN_PROGRESS",
    )
    db_session.add(session)
    db_session.commit()

    question = Question(
        id=uuid.uuid4(),
        session_id=session.id,
        sequence=1,
        topic="API design",
        question_text="Explain REST.",
    )
    db_session.add(question)
    db_session.commit()

    # Verify no answer exists initially
    existing_answer = db_session.query(Answer).filter(Answer.question_id == question.id).first()
    assert existing_answer is None

    # Perform POST upload
    file_data = b"fresh audio bytes"
    resp = client.post(
        f"/api/v1/sessions/{session.id}/questions/{question.id}/audio",
        files={"file": ("recording.wav", file_data, "audio/wav")},
    )
    assert resp.status_code == 201
    data = resp.json()
    recording_id = data["recording_id"]
    transcript = data["transcript"]

    # Verify answer was created automatically
    db_session.expire_all()
    created_answer = db_session.query(Answer).filter(Answer.question_id == question.id).first()
    assert created_answer is not None
    assert str(created_answer.recording_id) == recording_id
    assert created_answer.answer_text == transcript
    assert len(created_answer.answer_text) > 0


def test_second_audio_upload_reuses_existing_stub_answer(client, db_session):
    # Setup test session and question, but do NOT create any answer row in database
    from app.models.resume import Resume
    from app.models.session import Session
    from app.models.question import Question

    resume = Resume(
        id=uuid.uuid4(),
        raw_text="Test resume",
        extracted_skills=[],
        extracted_technologies=[],
        years_experience_estimate=2,
    )
    db_session.add(resume)
    db_session.commit()

    session = Session(
        id=uuid.uuid4(),
        resume_id=resume.id,
        role="backend_engineer",
        mode="self_prep",
        status="IN_PROGRESS",
    )
    db_session.add(session)
    db_session.commit()

    question = Question(
        id=uuid.uuid4(),
        session_id=session.id,
        sequence=1,
        topic="API design",
        question_text="Explain REST.",
    )
    db_session.add(question)
    db_session.commit()

    # Upload first time
    resp = client.post(
        f"/api/v1/sessions/{session.id}/questions/{question.id}/audio",
        files={"file": ("recording1.wav", b"first audio", "audio/wav")},
    )
    assert resp.status_code == 201
    recording1_id = resp.json()["recording_id"]

    # Verify single answer exists
    db_session.expire_all()
    answers = db_session.query(Answer).filter(Answer.question_id == question.id).all()
    assert len(answers) == 1
    assert str(answers[0].recording_id) == recording1_id

    # Upload second time (retry scenario)
    resp = client.post(
        f"/api/v1/sessions/{session.id}/questions/{question.id}/audio",
        files={"file": ("recording2.wav", b"second audio retry", "audio/wav")},
    )
    assert resp.status_code == 201
    recording2_id = resp.json()["recording_id"]

    # Verify still exactly one answer exists and it has been updated to recording2_id
    db_session.expire_all()
    answers = db_session.query(Answer).filter(Answer.question_id == question.id).all()
    assert len(answers) == 1
    assert str(answers[0].recording_id) == recording2_id
    assert recording2_id != recording1_id

