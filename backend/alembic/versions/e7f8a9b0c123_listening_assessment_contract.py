"""add versioned listening assessment contract

Revision ID: e7f8a9b0c123
Revises: d6e7f8a9b012
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa


revision = "e7f8a9b0c123"
down_revision = "d6e7f8a9b012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tests", sa.Column("content_version", sa.String(), server_default="legacy", nullable=False))
    op.add_column("tests", sa.Column("content_metadata", sa.JSON(), nullable=True))
    op.add_column("sections", sa.Column("section_metadata", sa.JSON(), nullable=True))
    op.add_column("questions", sa.Column("question_metadata", sa.JSON(), nullable=True))
    op.add_column("attempts", sa.Column("content_version", sa.String(), server_default="legacy", nullable=False))
    op.add_column("attempts", sa.Column("mode", sa.String(), server_default="exam", nullable=False))
    op.add_column("attempts", sa.Column("submission_key", sa.String(), nullable=True))
    op.create_unique_constraint("uq_attempt_submission_key", "attempts", ["user_id", "test_id", "submission_key"])
    op.create_table(
        "listening_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("content_version", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), server_default="practice", nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("current_section", sa.Integer(), server_default="0", nullable=False),
        sa.Column("audio_position", sa.Float(), server_default="0", nullable=False),
        sa.Column("max_audio_position", sa.Float(), server_default="0", nullable=False),
        sa.Column("status", sa.String(), server_default="in_progress", nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "user_id", "test_id", "content_version", "mode",
            name="uq_listening_progress_user_test_version_mode",
        ),
    )
    op.create_index("ix_listening_progress_user_updated", "listening_progress", ["user_id", "updated_at"])


def downgrade() -> None:
    op.drop_index("ix_listening_progress_user_updated", table_name="listening_progress")
    op.drop_table("listening_progress")
    op.drop_constraint("uq_attempt_submission_key", "attempts", type_="unique")
    op.drop_column("attempts", "submission_key")
    op.drop_column("attempts", "mode")
    op.drop_column("attempts", "content_version")
    op.drop_column("questions", "question_metadata")
    op.drop_column("sections", "section_metadata")
    op.drop_column("tests", "content_metadata")
    op.drop_column("tests", "content_version")
