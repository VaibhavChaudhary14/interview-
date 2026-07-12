"""transcription jobs and classification

Revision ID: 003
Revises: 002
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime, timezone

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create role_families table
    role_families = op.create_table(
        "role_families",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("kb_collection_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Seed the role families
    op.bulk_insert(
        role_families,
        [
            {
                "id": uuid.uuid4(),
                "slug": "software_engineering",
                "name": "Software Engineering",
                "description": "Software development, programming, backend, frontend, systems engineering, design patterns, testing, databases, and deployment.",
                "keywords": ["swe", "software engineer", "backend", "frontend", "full stack", "developer", "programmer", "coder"],
                "kb_collection_name": "kb_backend_engineer",
                "created_at": datetime.now(timezone.utc),
            },
            {
                "id": uuid.uuid4(),
                "slug": "ai_ml",
                "name": "AI / ML Engineering",
                "description": "Machine learning, artificial intelligence, neural networks, computer vision, natural language processing, data science, and model training.",
                "keywords": ["ml engineer", "ai engineer", "machine learning", "data scientist", "deep learning", "nlp scientist"],
                "kb_collection_name": "kb_ai_ml_engineer",
                "created_at": datetime.now(timezone.utc),
            },
            {
                "id": uuid.uuid4(),
                "slug": "product_management",
                "name": "Product Management",
                "description": "Product strategy, roadmap planning, user research, backlog grooming, cross-functional leadership, and feature specifications.",
                "keywords": ["product manager", "pm", "product owner", "product lead"],
                "kb_collection_name": None,
                "created_at": datetime.now(timezone.utc),
            },
            {
                "id": uuid.uuid4(),
                "slug": "design",
                "name": "Design",
                "description": "User experience, user interface, graphic design, design systems, visual design, wireframing, and user research.",
                "keywords": ["designer", "ux", "ui", "product design", "visual designer"],
                "kb_collection_name": None,
                "created_at": datetime.now(timezone.utc),
            },
            {
                "id": uuid.uuid4(),
                "slug": "sales",
                "name": "Sales",
                "description": "Account management, outbound sales, customer relationship management, deal closing, SDR, business development, and lead qualification.",
                "keywords": ["sales", "account executive", "sdr", "bdr", "sales representative", "sales lead"],
                "kb_collection_name": None,
                "created_at": datetime.now(timezone.utc),
            },
        ],
    )

    # 2. Modify sessions table
    op.add_column("sessions", sa.Column("matched_family_id", UUID(as_uuid=True), sa.ForeignKey("role_families.id"), nullable=True))
    op.add_column("sessions", sa.Column("classification_method", sa.String(), nullable=True))
    op.add_column("sessions", sa.Column("classification_confidence", sa.Float(), nullable=True))

    # 3. Create transcription_jobs table
    op.create_table(
        "transcription_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", sa.String(), unique=True, nullable=False, index=True),
        sa.Column("answer_id", UUID(as_uuid=True), sa.ForeignKey("answers.id"), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("webhook_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_poll_exhausted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. Create provider_usage table
    op.create_table(
        "provider_usage",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False, index=True),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("usage_date", sa.Date(), nullable=False, index=True),
    )


def downgrade():
    op.drop_table("provider_usage")
    op.drop_table("transcription_jobs")
    op.drop_column("sessions", "classification_confidence")
    op.drop_column("sessions", "classification_method")
    op.drop_column("sessions", "matched_family_id")
    op.drop_table("role_families")
