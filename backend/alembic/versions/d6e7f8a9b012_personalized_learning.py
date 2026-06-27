"""add personalized learning profile, diagnostic, plan, and review state

Revision ID: d6e7f8a9b012
Revises: c5d6e7f8a901
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa


revision = "d6e7f8a9b012"
down_revision = "c5d6e7f8a901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("current_level", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("current_level_source", sa.String(), nullable=True))
    op.add_column("users", sa.Column("exam_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("weekly_study_days", sa.Integer(), server_default="3", nullable=False))
    op.add_column("users", sa.Column("daily_study_minutes", sa.Integer(), server_default="30", nullable=False))
    op.add_column("users", sa.Column("primary_focus", sa.String(), server_default="balanced", nullable=False))
    op.add_column("users", sa.Column("onboarding_completed", sa.Boolean(), server_default=sa.false(), nullable=False))

    op.create_table(
        "diagnostic_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(), server_default="not_started", nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("writing_submission_id", sa.Integer(), nullable=True),
        sa.Column("reading_attempt_id", sa.Integer(), nullable=True),
        sa.Column("provisional_level", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_diagnostic_sessions_user_started", "diagnostic_sessions", ["user_id", "started_at"])

    op.create_table(
        "study_plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("stable_key", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("skill", sa.String(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("href", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_ref", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "week_start", "stable_key", name="uq_study_plan_user_week_key"),
    )
    op.create_index("ix_study_plan_user_date", "study_plan_items", ["user_id", "scheduled_date"])
    op.create_index("ix_study_plan_user_status", "study_plan_items", ["user_id", "status"])

    op.create_table(
        "mistake_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("skill", sa.String(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), server_default="new", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "skill", "source_id", name="uq_mistake_review_source"),
    )
    op.create_index("ix_mistake_reviews_user_status", "mistake_reviews", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_mistake_reviews_user_status", table_name="mistake_reviews")
    op.drop_table("mistake_reviews")
    op.drop_index("ix_study_plan_user_status", table_name="study_plan_items")
    op.drop_index("ix_study_plan_user_date", table_name="study_plan_items")
    op.drop_table("study_plan_items")
    op.drop_index("ix_diagnostic_sessions_user_started", table_name="diagnostic_sessions")
    op.drop_table("diagnostic_sessions")
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "primary_focus")
    op.drop_column("users", "daily_study_minutes")
    op.drop_column("users", "weekly_study_days")
    op.drop_column("users", "exam_date")
    op.drop_column("users", "current_level_source")
    op.drop_column("users", "current_level")
