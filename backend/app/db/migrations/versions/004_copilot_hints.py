"""add copilot hints to questions

Revision ID: 004
Revises: 003
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("questions", sa.Column("copilot_hints", JSONB(), nullable=True))


def downgrade():
    op.drop_column("questions", "copilot_hints")
