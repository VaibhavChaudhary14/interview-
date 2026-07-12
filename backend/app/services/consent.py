import hashlib
import uuid
from sqlalchemy.orm import Session as DBSession
from app.models.consent import Consent
from app.models.consent_policy_version import ConsentPolicyVersion


class ConsentService:
    @staticmethod
    def record_consent(
        db: DBSession,
        session_id: str,
        consent_text_version: str,
        audio_recording_allowed: bool,
        ip_address: str | None = None,
    ) -> Consent:
        policy = db.query(ConsentPolicyVersion).filter(ConsentPolicyVersion.version == consent_text_version).first()
        if not policy:
            raise ValueError(f"Unsupported consent version: {consent_text_version}")

        consent_text = policy.consent_text
        # Generate hash of consent text to verify what was agreed to
        consent_hash = hashlib.sha256(consent_text.encode("utf-8")).hexdigest()

        session_id_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id

        consent = Consent(
            session_id=session_id_uuid,
            consent_text_version=consent_text_version,
            consent_text_hash=consent_hash,
            audio_recording_allowed=audio_recording_allowed,
            ip_address=ip_address,
        )
        db.add(consent)
        db.commit()
        db.refresh(consent)
        return consent

    @staticmethod
    def get_consent_for_session(db: DBSession, session_id: str) -> Consent | None:
        session_id_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
        return db.query(Consent).filter(Consent.session_id == session_id_uuid).order_by(Consent.granted_at.desc()).first()

    @staticmethod
    def get_active_version(db: DBSession) -> ConsentPolicyVersion | None:
        # Returns the latest created policy version
        return db.query(ConsentPolicyVersion).order_by(ConsentPolicyVersion.created_at.desc()).first()
