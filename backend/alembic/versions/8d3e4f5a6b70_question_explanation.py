"""add explanation column to questions

Revision ID: 8d3e4f5a6b70
Revises: 7c2d3e4f5a60
Create Date: 2026-06-24

Additive, nullable column powering review-mode explanations for Reading/Listening
questions. Safe: existing rows get NULL and the API treats it as optional.
"""
from alembic import op
import sqlalchemy as sa

revision = "8d3e4f5a6b70"
down_revision = "7c2d3e4f5a60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("explanation", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "explanation")
