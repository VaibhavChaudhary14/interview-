"""
Migration 007 — Create answer_metrics table.

Stores per-answer delivery metrics computed after transcription completes:
WPM, pause detection, filler word counts. Computed asynchronously via
AudioMetricsJob triggered from both the sync STT path and the AssemblyAI
webhook path.

computation_error is nullable — null means computation succeeded. If the job
fails (corrupt audio, librosa error, file unavailable), computation_error
stores the reason so the failure is visible rather than silently missing.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "answer_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("answer_id", UUID(as_uuid=True), sa.ForeignKey("answers.id"), unique=True, nullable=False),
        sa.Column("wpm", sa.Float(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("audio_duration_seconds", sa.Float(), nullable=True),
        sa.Column("pause_count", sa.Integer(), nullable=True),
        sa.Column("avg_pause_duration", sa.Float(), nullable=True),
        sa.Column("longest_pause_seconds", sa.Float(), nullable=True),
        sa.Column("filler_word_count", sa.Integer(), nullable=True),
        sa.Column("filler_word_breakdown", JSONB(), nullable=True, server_default="{}"),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("computation_error", sa.Text(), nullable=True),
    )
    op.create_index("idx_answer_metrics_answer_id", "answer_metrics", ["answer_id"])


def downgrade():
    op.drop_index("idx_answer_metrics_answer_id", table_name="answer_metrics")
    op.drop_table("answer_metrics")
