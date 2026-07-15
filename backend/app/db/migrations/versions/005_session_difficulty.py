"""add difficulty to sessions

Revision ID: 005
Revises: 004
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    # enums need an explicit type creation step in Postgres that SQLite doesn't require
    difficulty_enum = sa.Enum(
        "beginner", "intermediate", "advanced", name="session_difficulty"
    )
    difficulty_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "sessions",
        sa.Column(
            "difficulty",
            difficulty_enum,
            nullable=False,
            server_default="intermediate",
        ),
    )


def downgrade():
    op.drop_column("sessions", "difficulty")
    sa.Enum(name="session_difficulty").drop(op.get_bind(), checkfirst=True)
