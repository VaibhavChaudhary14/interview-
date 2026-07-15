import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.models.recording import Recording
from app.models.session import Session
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AudioService:
    @staticmethod
    def _get_s3_client():
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            kwargs = {
                "aws_access_key_id": settings.aws_access_key_id,
                "aws_secret_access_key": settings.aws_secret_access_key,
            }
            if settings.s3_endpoint_url:
                kwargs["endpoint_url"] = settings.s3_endpoint_url
            return boto3.client("s3", **kwargs)
        return None

    @classmethod
    def read_recording_bytes(cls, db: DBSession, recording_id: str) -> bytes | None:
        """
        Fetch raw audio bytes for a recording, using the same S3/local-fallback
        duality as upload_recording and delete_recording.

        Returns None if the recording is deleted, not found, or fetch fails —
        callers must handle None gracefully (e.g., store computation_error
        rather than crashing). Never raises.
        """
        from uuid import UUID as _UUID
        rec_id = _UUID(recording_id) if isinstance(recording_id, str) else recording_id
        recording = db.query(Recording).filter(Recording.id == rec_id).first()
        if not recording or recording.deletion_completed_at is not None or not recording.s3_key:
            logger.warning("read_recording_bytes: recording %s not available", recording_id)
            return None

        s3_client = cls._get_s3_client()
        if s3_client:
            # S3 path — mirrors upload_recording's S3 put_object
            try:
                obj = s3_client.get_object(
                    Bucket=settings.s3_bucket_name, Key=recording.s3_key
                )
                return obj["Body"].read()
            except ClientError as e:
                logger.error("Failed to read recording from S3 (%s): %s", recording.s3_key, e)
                return None
        else:
            # Local fallback path — s3_key is the absolute local path (set by upload_recording)
            local_path = Path(recording.s3_key)
            if local_path.exists():
                logger.debug("read_recording_bytes: local path %s", local_path)
                return local_path.read_bytes()
            logger.warning("read_recording_bytes: local file not found at %s", local_path)
            return None



    @classmethod
    def upload_recording(
        cls,
        db: DBSession,
        session_id: str,
        answer_id: str | None,
        file_content: bytes,
        consent_id: str | None = None,
    ) -> Recording:
        unique_id = uuid.uuid4()
        s3_key = f"recordings/{session_id}/{unique_id}.wav"

        s3_client = cls._get_s3_client()
        if s3_client:
            try:
                s3_client.put_object(
                    Bucket=settings.s3_bucket_name,
                    Key=s3_key,
                    Body=file_content,
                    ServerSideEncryption="AES256",
                )
                logger.info("Uploaded recording to S3: %s", s3_key)
            except ClientError as e:
                logger.error("Failed to upload to S3: %s", e)
                raise RuntimeError("Failed to upload recording to cloud storage") from e
        else:
            # Fallback to local storage
            local_dir = Path(settings.recordings_local_dir) / session_id
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_dir / f"{unique_id}.wav"
            with open(local_path, "wb") as f:
                f.write(file_content)
            logger.info("Saved recording locally to %s", local_path)
            # We'll use local path as the s3_key reference
            s3_key = str(local_path.resolve())

        recording = Recording(
            id=unique_id,
            session_id=uuid.UUID(session_id) if isinstance(session_id, str) else session_id,
            answer_id=uuid.UUID(answer_id) if isinstance(answer_id, str) and answer_id else answer_id,
            s3_key=s3_key,
            consent_id=uuid.UUID(consent_id) if isinstance(consent_id, str) and consent_id else consent_id,
        )
        db.add(recording)
        db.commit()
        db.refresh(recording)
        return recording

    @classmethod
    def generate_presigned_url(
        cls,
        db: DBSession,
        recording_id: str,
        user_id: str | None = None,
        ip_address: str | None = None,
    ) -> str:
        rec_id = uuid.UUID(recording_id) if isinstance(recording_id, str) else recording_id
        recording = db.query(Recording).filter(Recording.id == rec_id).first()
        if not recording:
            raise ValueError("Recording not found")

        if recording.deletion_completed_at is not None or not recording.s3_key:
            raise ValueError("Recording has been deleted")

        s3_client = cls._get_s3_client()
        if s3_client:
            try:
                url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": settings.s3_bucket_name, "Key": recording.s3_key},
                    ExpiresIn=900,  # 15 minutes
                )
            except ClientError as e:
                logger.error("Failed to generate presigned URL: %s", e)
                raise RuntimeError("Failed to generate playback URL") from e
        else:
            # For local files, return a local URL path
            url = f"/api/v1/audio/file/{recording_id}"

        # Write to audit log
        audit = AuditLog(
            user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            action="GENERATE_PRESIGNED_URL",
            target_recording_id=recording.id,
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        return url

    @classmethod
    def delete_recording(cls, db: DBSession, recording_id: str) -> bool:
        rec_id = uuid.UUID(recording_id) if isinstance(recording_id, str) else recording_id
        recording = db.query(Recording).filter(Recording.id == rec_id).first()
        if not recording:
            return False

        if recording.deletion_completed_at is not None:
            return True  # Already deleted

        s3_key = recording.s3_key
        if s3_key:
            s3_client = cls._get_s3_client()
            if s3_client:
                try:
                    s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)
                    logger.info("Deleted recording from S3: %s", s3_key)
                except ClientError as e:
                    logger.error("Failed to delete from S3: %s", e)
                    # We continue to mark deleted in DB so we don't loop forever,
                    # but log the failure.
            else:
                # Local file deletion
                local_path = Path(s3_key)
                if local_path.exists():
                    try:
                        local_path.unlink()
                        logger.info("Deleted local recording: %s", local_path)
                    except Exception as e:
                        logger.error("Failed to delete local file: %s", e)

        recording.s3_key = None
        recording.deletion_completed_at = datetime.now(timezone.utc)
        db.commit()
        return True

    @classmethod
    def delete_expired_recordings(cls, db: DBSession) -> int:
        recordings = (
            db.query(Recording)
            .filter(Recording.deletion_completed_at.is_(None))
            .all()
        )
        deleted_count = 0
        now = datetime.now(timezone.utc)

        for recording in recordings:
            session = db.query(Session).filter(Session.id == recording.session_id).first()
            if not session:
                continue

            # Determine retention limit
            if session.retention_days_override is not None:
                days = session.retention_days_override
            elif session.mode == "self_prep":
                days = 30
            else:
                days = 365  # Default for agency

            created_at = recording.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            limit = created_at + timedelta(days=days)
            if now > limit:
                cls.delete_recording(db, str(recording.id))
                deleted_count += 1

        return deleted_count
