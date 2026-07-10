"""add essay_type to writing tasks

Revision ID: h2b3c4d5e6f7
Revises: g1a2b3c4d5e6
Create Date: 2026-07-10

"""
from alembic import op
import sqlalchemy as sa


revision = "h2b3c4d5e6f7"
down_revision = "g1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "writing_tasks",
        sa.Column("essay_type", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("writing_tasks", "essay_type")
