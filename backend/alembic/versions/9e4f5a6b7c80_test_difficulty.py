"""add difficulty column to tests

Revision ID: 9e4f5a6b7c80
Revises: 8d3e4f5a6b70
Create Date: 2026-06-24

Additive, nullable. Powers the difficulty badge/filter on the practice library.
Existing rows get NULL; the UI treats that as "Medium".
"""
from alembic import op
import sqlalchemy as sa

revision = "9e4f5a6b7c80"
down_revision = "8d3e4f5a6b70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tests", sa.Column("difficulty", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("tests", "difficulty")
