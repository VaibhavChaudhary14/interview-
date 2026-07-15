"""
Migration 008 — Create feedbacks table and add indexes to sessions.

Stores per-session candidate feedback (rating_realistic, rating_feedback, comments).
Adds indexes on sessions.created_at and sessions.status to speed up time-windowed funnel analytics.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create feedbacks table
    op.create_table(
        "feedbacks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("rating_realistic", sa.Integer(), nullable=False),
        sa.Column("rating_feedback", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_feedbacks_session_id", "feedbacks", ["session_id"])

    # 2. Add indexes to sessions for analytics querying
    op.create_index("idx_sessions_created_at", "sessions", ["created_at"])


def downgrade():
    # 1. Remove indexes on sessions
    op.drop_index("idx_sessions_created_at", table_name="sessions")

    # 2. Drop feedbacks table
    op.drop_index("idx_feedbacks_session_id", table_name="feedbacks")
    op.drop_table("feedbacks")
