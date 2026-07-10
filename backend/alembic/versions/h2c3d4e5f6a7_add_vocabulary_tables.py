"""add vocabulary tables and native language

Revision ID: h2c3d4e5f6a7
Revises: g1a2b3c4d5e6
Create Date: 2026-07-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h2c3d4e5f6a7"
down_revision: Union[str, None] = "g1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("native_language", sa.String(), nullable=True))

    op.create_table(
        "saved_words",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("word", sa.String(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("source_ref", sa.String(), nullable=True),
        sa.Column("enrichment", sa.JSON(), nullable=True),
        sa.Column("enriched_at", sa.DateTime(), nullable=True),
        sa.Column("training", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "word", name="uq_saved_word_user_word"),
    )
    op.create_index("ix_saved_words_user_created", "saved_words", ["user_id", "created_at"])
    op.create_index("ix_saved_words_user_training", "saved_words", ["user_id", "training"])

    op.create_table(
        "daily_word_quizzes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("quiz_date", sa.Date(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("total", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "quiz_date", name="uq_daily_word_quiz_user_date"),
    )


def downgrade() -> None:
    op.drop_table("daily_word_quizzes")
    op.drop_index("ix_saved_words_user_training", table_name="saved_words")
    op.drop_index("ix_saved_words_user_created", table_name="saved_words")
    op.drop_table("saved_words")
    op.drop_column("users", "native_language")
