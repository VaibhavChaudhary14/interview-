import uuid
import pytest
from app.models.resume import Resume
from app.models.session import Session
from app.models.consent import Consent
from app.models.consent_policy_version import ConsentPolicyVersion
from app.services.consent import ConsentService


def create_test_session(db_session):
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
        mode="self_prep",
        status="CREATED",
    )
    db_session.add(session)
    db_session.commit()
    return session


def seed_test_policies(db_session):
    # Check if already seeded to prevent duplicates in some test runs
    existing = db_session.query(ConsentPolicyVersion).first()
    if existing:
        return
    p1 = ConsentPolicyVersion(
        version="v1.0",
        consent_text="This is version 1.0 consent text."
    )
    p2 = ConsentPolicyVersion(
        version="v1.2",
        consent_text="This is version 1.2 consent text."
    )
    db_session.add(p1)
    db_session.add(p2)
    db_session.commit()


def test_consent_service_record_and_get_valid(db_session):
    seed_test_policies(db_session)
    session = create_test_session(db_session)
    consent_version = "v1.0"

    consent = ConsentService.record_consent(
        db=db_session,
        session_id=str(session.id),
        consent_text_version=consent_version,
        audio_recording_allowed=True,
        ip_address="127.0.0.1",
    )

    assert consent.id is not None
    assert consent.session_id == session.id
    assert consent.consent_text_version == consent_version
    assert consent.audio_recording_allowed is True
    assert consent.ip_address == "127.0.0.1"
    assert len(consent.consent_text_hash) == 64  # SHA-256 length

    retrieved = ConsentService.get_consent_for_session(db_session, str(session.id))
    assert retrieved is not None
    assert retrieved.id == consent.id


def test_consent_service_record_invalid_version(db_session):
    seed_test_policies(db_session)
    session = create_test_session(db_session)
    with pytest.raises(ValueError, match="Unsupported consent version"):
        ConsentService.record_consent(
            db=db_session,
            session_id=str(session.id),
            consent_text_version="v99.0-invalid",
            audio_recording_allowed=True,
        )


def test_consent_api_get_not_found_before_creation(client, db_session):
    seed_test_policies(db_session)
    session = create_test_session(db_session)
    resp = client.get(f"/api/v1/sessions/{session.id}/consent")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "CONSENT_NOT_FOUND"


def test_consent_api_post_valid_consent(client, db_session):
    seed_test_policies(db_session)
    session = create_test_session(db_session)
    payload = {
        "consent_text_version": "v1.2",
        "audio_recording_allowed": True,
    }
    resp = client.post(f"/api/v1/sessions/{session.id}/consent", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["audio_recording_allowed"] is True
    assert data["consent_text_version"] == "v1.2"
    assert data["consent_id"] is not None

    # Retrieve and verify
    get_resp = client.get(f"/api/v1/sessions/{session.id}/consent")
    assert get_resp.status_code == 200
    assert get_resp.json()["consent_id"] == data["consent_id"]


def test_consent_api_post_invalid_version(client, db_session):
    seed_test_policies(db_session)
    session = create_test_session(db_session)
    payload = {
        "consent_text_version": "invalid-v3.0",
        "audio_recording_allowed": True,
    }
    resp = client.post(f"/api/v1/sessions/{session.id}/consent", json=payload)
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_code"] == "INVALID_CONSENT_VERSION"


def test_consent_api_get_active_version(client, db_session):
    seed_test_policies(db_session)
    session = create_test_session(db_session)
    resp = client.get(f"/api/v1/sessions/{session.id}/consent/active-version")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "v1.2"  # latest seeded policy
    assert "This is version 1.2 consent text" in data["consent_text"]


# ---------------------------------------------------------------------------
# Append-only policy version enforcement (Phase 0 cleanup — A.2)
# ---------------------------------------------------------------------------

def test_create_policy_version_success(db_session):
    """create_policy_version() with a new version string succeeds."""
    policy = ConsentService.create_policy_version(db_session, "v2.0", "New policy text v2.0")
    assert policy.version == "v2.0"
    assert policy.consent_text == "New policy text v2.0"
    assert policy.id is not None

    # Confirm it's persisted
    from_db = db_session.query(ConsentPolicyVersion).filter_by(version="v2.0").first()
    assert from_db is not None
    assert from_db.consent_text == "New policy text v2.0"


def test_policy_version_cannot_be_overwritten(db_session):
    """
    create_policy_version() raises ValueError if the version string already
    exists — policy versions are append-only. The original text must be
    preserved unchanged in the DB.

    Note: there is no HTTP endpoint for creating policy versions; this is a
    service-layer concern. The test calls the service directly, which is the
    complete and correct enforcement surface.
    """
    # First creation succeeds
    ConsentService.create_policy_version(db_session, "v1.0", "Original text A")

    # Second creation with same version string, different text, must raise
    with pytest.raises(ValueError) as exc_info:
        ConsentService.create_policy_version(db_session, "v1.0", "Tampered text B")

    assert "v1.0" in str(exc_info.value)
    assert "already exists" in str(exc_info.value)

    # Original text must be completely unchanged
    from_db = db_session.query(ConsentPolicyVersion).filter_by(version="v1.0").first()
    assert from_db is not None
    assert from_db.consent_text == "Original text A", (
        "Policy text was silently overwritten — audit hash integrity would be broken"
    )


def test_policy_version_different_versions_both_succeed(db_session):
    """Creating two distinct version strings is the correct upgrade path."""
    ConsentService.create_policy_version(db_session, "v1.0", "Policy text v1.0")
    ConsentService.create_policy_version(db_session, "v1.1", "Updated policy text v1.1")

    all_versions = db_session.query(ConsentPolicyVersion).all()
    version_strings = {p.version for p in all_versions}
    assert "v1.0" in version_strings
    assert "v1.1" in version_strings

