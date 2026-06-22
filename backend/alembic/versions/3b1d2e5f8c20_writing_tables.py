"""writing tasks and submissions

Revision ID: 3b1d2e5f8c20
Revises: 2a9f1c4b7e10
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa


revision = "3b1d2e5f8c20"
down_revision = "2a9f1c4b7e10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "writing_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_type", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("min_words", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
    )
    op.create_table(
        "writing_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("writing_tasks.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("band", sa.Float(), nullable=True),
        sa.Column("feedback", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("writing_submissions")
    op.drop_table("writing_tasks")
