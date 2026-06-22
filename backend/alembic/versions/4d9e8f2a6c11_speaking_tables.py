"""speaking tasks and submissions

Revision ID: 4d9e8f2a6c11
Revises: 3b1d2e5f8c20
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa


revision = "4d9e8f2a6c11"
down_revision = "3b1d2e5f8c20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "speaking_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("part", sa.Integer(), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("prep_seconds", sa.Integer(), nullable=False),
        sa.Column("speak_seconds", sa.Integer(), nullable=False),
    )
    op.create_table(
        "speaking_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("speaking_tasks.id"), nullable=False),
        sa.Column("audio_url", sa.String(), nullable=False),
        sa.Column("transcript", sa.String(), nullable=True),
        sa.Column("band", sa.Float(), nullable=True),
        sa.Column("feedback", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("speaking_submissions")
    op.drop_table("speaking_tasks")
