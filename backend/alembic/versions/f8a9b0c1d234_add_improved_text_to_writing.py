"""add improved_text (Better Version) to writing submissions

Revision ID: f8a9b0c1d234
Revises: e7f8a9b0c123
Create Date: 2026-06-30

"""
from alembic import op
import sqlalchemy as sa


revision = "f8a9b0c1d234"
down_revision = "e7f8a9b0c123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "writing_submissions",
        sa.Column("improved_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("writing_submissions", "improved_text")
