import uuid
import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from app.models.role_family import RoleFamily
from app.models.session import Session
from app.models.answer import Answer
from app.models.question import Question
from app.models.transcription_job import TranscriptionJob
from app.models.provider_usage import ProviderUsage
from app.services.role_classifier import RoleClassifierService, ClassificationResult
from app.services.question_generator import QuestionGeneratorService


def test_keyword_match_high_confidence(db_session):
    classifier = RoleClassifierService(db_session)
    result = classifier.classify("Junior Backend Developer")
    assert result.method == "keyword"
    assert result.family_slug == "software_engineering"
    assert result.confidence == 1.0


def test_keyword_match_below_threshold_falls_to_llm(db_session):
    # Mock LLM fallback return value
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"slug": "ai_ml", "confidence": 0.85}'
    
    classifier = RoleClassifierService(db_session, llm_provider=mock_llm)
    result = classifier.classify("Something ambiguous NLP Scientist")
    assert result.method == "llm"
    assert result.family_slug == "ai_ml"
    assert result.confidence == 0.85


def test_llm_fallback_classifies_novel_role(db_session):
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"slug": "unclassified", "confidence": 0.3}'

    classifier = RoleClassifierService(db_session, llm_provider=mock_llm)
    result = classifier.classify("Ayurvedic practitioner")
    assert result.family_id is None
    assert result.family_slug is None
    assert result.method == "unclassified"


def test_llm_failure_degrades_gracefully(db_session):
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = Exception("LLM connection timed out")

    classifier = RoleClassifierService(db_session, llm_provider=mock_llm)
    result = classifier.classify("Some strange role name")
    assert result.family_id is None
    assert result.method == "unclassified"


def test_session_creation_stores_classification_metadata(client, db_session):
    payload = {
        "resume_id": None,
        "role": "Lead Frontend Engineer",
        "mode": "self_prep",
    }
    resp = client.post("/api/v1/sessions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["matched_family_id"] is not None
    assert data["classification_method"] == "keyword"

    # Verify fields in DB
    sess = db_session.query(Session).filter(Session.id == uuid.UUID(data["session_id"])).first()
    assert sess is not None
    assert sess.classification_method == "keyword"
    assert sess.matched_family_id is not None


def test_fallback_prompt_used_when_no_kb_collection():
    # If chunks is empty, QuestionGeneratorService must use FALLBACK_PROMPT_TEMPLATE
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"topic": "Product Roadmap", "question": "How do you align stakeholders?"}'
    
    generator = QuestionGeneratorService(mock_llm)
    result = generator.generate(
        role="Product Manager",
        topic="Product Roadmap",
        chunks=[],  # No chunks / skipped RAG
        resume_signals={"extracted_skills": ["Roadmapping"], "extracted_technologies": []},
        topics_already_asked=[],
        prev_answer=None,
        years_experience=3,
        mode="self_prep",
    )
    assert result["topic"] == "Product Roadmap"
    assert "question" in result
    
    # Assert generator.llm.generate was called with the Fallback Prompt structure
    prompt_sent = mock_llm.generate.call_args[0][0]
    assert "You are a supportive interview coach" in prompt_sent
    assert "No reference material is available" in prompt_sent


def test_webhook_idempotency(client, db_session):
    # Setup job and answer
    answ = Answer(
        id=uuid.uuid4(),
        question_id=uuid.uuid4(),
        answer_text="",
    )
    db_session.add(answ)
    db_session.commit()

    job = TranscriptionJob(
        id=uuid.uuid4(),
        job_id="test_job_123",
        answer_id=answ.id,
        status="completed",  # Already finished via sync poll
    )
    db_session.add(job)
    db_session.commit()

    # Call webhook
    payload = {
        "id": "test_job_123",
        "status": "completed",
        "text": "Late webhook transcribed text",
    }
    resp = client.post("/api/v1/webhooks/assemblyai/transcript", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    # Verify no overwrite happened
    db_session.refresh(answ)
    assert answ.transcript_text is None


def test_webhook_race_condition(client, db_session):
    answ = Answer(
        id=uuid.uuid4(),
        question_id=uuid.uuid4(),
        answer_text="",
    )
    db_session.add(answ)
    db_session.commit()

    job = TranscriptionJob(
        id=uuid.uuid4(),
        job_id="test_job_456",
        answer_id=answ.id,
        status="pending",
    )
    db_session.add(job)
    db_session.commit()

    # Webhook updates it
    payload = {
        "id": "test_job_456",
        "status": "completed",
        "text": "Transcribed text from webhook",
    }
    resp = client.post("/api/v1/webhooks/assemblyai/transcript", json=payload)
    assert resp.status_code == 200

    db_session.refresh(answ)
    assert answ.transcript_text == "Transcribed text from webhook"


def test_transcript_status_pending_then_completed(client, db_session):
    sess = Session(
        id=uuid.uuid4(),
        role="Backend Engineer",
        mode="self_prep",
    )
    db_session.add(sess)
    db_session.commit()

    answ = Answer(
        id=uuid.uuid4(),
        question_id=uuid.uuid4(),
        answer_text="",
    )
    db_session.add(answ)
    db_session.commit()

    job = TranscriptionJob(
        id=uuid.uuid4(),
        job_id="test_job_789",
        answer_id=answ.id,
        status="pending",
    )
    db_session.add(job)
    db_session.commit()

    # Verify it returns status pending
    resp = client.get(f"/api/v1/sessions/{sess.id}/answers/{answ.id}/transcript-status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

    # Simulate webhook completing the job
    payload = {
        "id": "test_job_789",
        "status": "completed",
        "text": "Polled transcript text",
    }
    client.post("/api/v1/webhooks/assemblyai/transcript", json=payload)

    # Verify it now returns status completed
    resp = client.get(f"/api/v1/sessions/{sess.id}/answers/{answ.id}/transcript-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["transcript"] == "Polled transcript text"


def test_provider_usage_tracking_and_alerting(db_session):
    with patch("app.models.provider_usage.logger") as mock_logger:
        ProviderUsage.record_usage(db_session, "assemblyai", 10.5)
        
        # Verify usage was persisted in DB
        today = datetime.now(timezone.utc).date()
        usage = db_session.query(ProviderUsage).filter(
            ProviderUsage.provider == "assemblyai",
            ProviderUsage.usage_date == today
        ).first()
        assert usage is not None
        assert usage.call_count == 1
        assert usage.total_seconds == 10.5

        # Check logs contain cost details.
        # provider_usage.py uses %-style lazy formatting; call_args[0][0] is the
        # format template, call_args[0][1] is the provider name argument.
        mock_logger.info.assert_called()
        log_format = mock_logger.info.call_args[0][0]
        log_args = mock_logger.info.call_args[0]
        assert "STT:" in log_format            # confirms it's an STT log line
        assert "cost_estimate" in log_format   # cost estimate is still logged
        assert "assemblyai" in log_args        # provider name passed as arg


        # Test threshold alert (>80% of 600 min, i.e. 480 mins = 28,800 seconds)
        ProviderUsage.record_usage(db_session, "assemblyai", 30000.0)
        mock_logger.warning.assert_called()
        warn_msg = mock_logger.warning.call_args[0][0]
        assert "ALARM: AssemblyAI usage has exceeded 80%" in warn_msg
