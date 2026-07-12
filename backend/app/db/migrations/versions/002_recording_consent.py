"""recording and consent schema

Revision ID: 002
Revises: 001
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    # 0. Create consent_policy_versions table
    consent_policy_versions = op.create_table(
        "consent_policy_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.String(), unique=True, nullable=False, index=True),
        sa.Column("consent_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    import uuid
    from datetime import datetime, timezone
    op.bulk_insert(
        consent_policy_versions,
        [
            {
                "id": uuid.uuid4(),
                "version": "v1.0",
                "consent_text": "This interview can be conducted by voice. If you allow it, we'll record your spoken answers to transcribe them and generate delivery feedback (pace, pauses, clarity). Recordings are stored securely and retained according to our retention policy.",
                "created_at": datetime.now(timezone.utc),
            },
            {
                "id": uuid.uuid4(),
                "version": "v1.2",
                "consent_text": "This interview can be conducted by voice. If you allow it, we'll record your spoken answers to transcribe them and generate delivery feedback (pace, pauses, clarity). Recordings are stored securely and retained according to our retention policy.",
                "created_at": datetime.now(timezone.utc),
            },
        ],
    )

    # 1. Modify sessions table
    op.add_column("sessions", sa.Column("mode", sa.String(), nullable=False, server_default="self_prep"))
    op.add_column("sessions", sa.Column("retention_days_override", sa.Integer(), nullable=True))
    op.alter_column("sessions", "resume_id", nullable=True)

    # 2. Create consents table
    op.create_table(
        "consents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("consent_text_version", sa.String(), nullable=False),
        sa.Column("consent_text_hash", sa.String(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("audio_recording_allowed", sa.Boolean(), nullable=False),
    )

    # 3. Create recordings table
    op.create_table(
        "recordings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("answer_id", UUID(as_uuid=True), sa.ForeignKey("answers.id"), nullable=True),
        sa.Column("s3_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consent_id", UUID(as_uuid=True), sa.ForeignKey("consents.id"), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deletion_completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_recording_id", UUID(as_uuid=True), sa.ForeignKey("recordings.id"), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
    )

    # 5. Modify answers table
    op.add_column("answers", sa.Column("recording_id", UUID(as_uuid=True), sa.ForeignKey("recordings.id"), nullable=True))
    op.add_column("answers", sa.Column("transcript_text", sa.Text(), nullable=True))
    op.add_column("answers", sa.Column("transcript_provider", sa.String(), nullable=True))


def downgrade():
    op.alter_column("sessions", "resume_id", nullable=False)
    op.drop_column("answers", "transcript_provider")
    op.drop_column("answers", "transcript_text")
    op.drop_column("answers", "recording_id")
    op.drop_table("audit_logs")
    op.drop_table("recordings")
    op.drop_table("consents")
    op.drop_column("sessions", "retention_days_override")
    op.drop_column("sessions", "mode")
    op.drop_table("consent_policy_versions")
