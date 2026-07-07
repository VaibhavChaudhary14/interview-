"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "resumes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("extracted_skills", JSONB, default=list),
        sa.Column("extracted_technologies", JSONB, default=list),
        sa.Column("extracted_domains", JSONB, default=list),
        sa.Column("years_experience_estimate", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("resume_id", UUID(as_uuid=True), sa.ForeignKey("resumes.id"), nullable=False),
        sa.Column("role", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False, default="CREATED"),
        sa.Column("max_questions", sa.Integer, default=8),
        sa.Column("questions_asked", sa.Integer, default=0),
        sa.Column("retrieval_queries", JSONB, default=list),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "questions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("topic", sa.String, nullable=False),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("source_chunk_ids", JSONB, default=list),
        sa.Column("generation_strategy", sa.String, default="initial"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "answers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("question_id", UUID(as_uuid=True), sa.ForeignKey("questions.id"), unique=True, nullable=False),
        sa.Column("answer_text", sa.Text, nullable=False),
        sa.Column("word_count", sa.Integer, default=0),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), unique=True, nullable=False),
        sa.Column("topics_covered", JSONB, default=list),
        sa.Column("insights", JSONB, default=dict),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("idx_sessions_resume_id", "sessions", ["resume_id"])
    op.create_index("idx_questions_session_id", "questions", ["session_id"])
    op.create_index("idx_answers_question_id", "answers", ["question_id"])
    op.create_index("uq_reports_session_id", "reports", ["session_id"], unique=True)
    op.create_index("idx_sessions_status", "sessions", ["status"])


def downgrade():
    op.drop_table("reports")
    op.drop_table("answers")
    op.drop_table("questions")
    op.drop_table("sessions")
    op.drop_table("resumes")
