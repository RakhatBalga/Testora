"""add evidence column to questions

Revision ID: a0f1b2c3d4e0
Revises: 9e4f5a6b7c80
Create Date: 2026-06-24

Additive, nullable JSON. Stores a list of {paragraph, text} evidence spans so
Reading Review can highlight where each answer is supported in the passage.
"""
from alembic import op
import sqlalchemy as sa

revision = "a0f1b2c3d4e0"
down_revision = "9e4f5a6b7c80"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("evidence", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "evidence")
