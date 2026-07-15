"""
Migration 006 — Add call_type and total_characters to provider_usage.

provider_usage previously tracked only total_seconds, which conflated
STT (billed per second of audio) with TTS (billed per character of input
text by ElevenLabs and Sarvam). This migration adds the columns needed to
track TTS usage correctly, using server defaults so existing rows
(all of which are STT) are assigned call_type='stt' automatically.
"""
from alembic import op
import sqlalchemy as sa


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "provider_usage",
        sa.Column(
            "call_type",
            sa.String(),
            nullable=False,
            server_default="stt",
        ),
    )
    op.add_column(
        "provider_usage",
        sa.Column(
            "total_characters",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
    )


def downgrade():
    op.drop_column("provider_usage", "total_characters")
    op.drop_column("provider_usage", "call_type")
