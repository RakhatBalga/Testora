"""goals table (target band, exam date, self-estimate)

Revision ID: 6f2a4b8c1d40
Revises: 5e1a3c7d9f30
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa


revision = "6f2a4b8c1d40"
down_revision = "5e1a3c7d9f30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("target_band", sa.Float(), nullable=False),
        sa.Column("current_band", sa.Float(), nullable=True),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("goals")
