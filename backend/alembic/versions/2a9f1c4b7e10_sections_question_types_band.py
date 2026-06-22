"""sections, question types, band score

Revision ID: 2a9f1c4b7e10
Revises: 1b67dbc1b72d
Create Date: 2026-06-21

Rebuilds the content tables: introduces sections, flexible question types
(JSON correct_answer), and a band column on attempts. Existing demo data is
dropped — re-run seed.py afterwards.
"""
from alembic import op
import sqlalchemy as sa


revision = "2a9f1c4b7e10"
down_revision = "1b67dbc1b72d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old content tables in FK-dependency order.
    op.drop_table("answer_records")
    op.drop_table("attempts")
    op.drop_table("questions")
    op.drop_table("tests")

    op.create_table(
        "tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("test_type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
    )

    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("passage", sa.Text(), nullable=True),
        sa.Column("audio_url", sa.String(), nullable=True),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id"), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("correct_answer", sa.JSON(), nullable=False),
    )

    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("band", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "answer_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("attempts.id"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("user_answer", sa.String(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("answer_records")
    op.drop_table("attempts")
    op.drop_table("questions")
    op.drop_table("sections")
    op.drop_table("tests")

    op.create_table(
        "tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("test_type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("audio_url", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
    )
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("correct_answer", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
    )
    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "answer_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("attempts.id"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("user_answer", sa.String(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
    )
