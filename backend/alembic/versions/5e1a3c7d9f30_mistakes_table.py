"""mistake memory table

Revision ID: 5e1a3c7d9f30
Revises: 4d9e8f2a6c11
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa


revision = "5e1a3c7d9f30"
down_revision = "4d9e8f2a6c11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mistakes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=True),
        sa.Column("skill", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("subskill", sa.String(), nullable=True),
        sa.Column("severity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("correction", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_mistakes_user_category", "mistakes", ["user_id", "category"])
    op.create_index("ix_mistakes_user_created", "mistakes", ["user_id", "created_at"])
    op.create_index("ix_mistakes_user_skill", "mistakes", ["user_id", "skill"])


def downgrade() -> None:
    op.drop_index("ix_mistakes_user_skill", table_name="mistakes")
    op.drop_index("ix_mistakes_user_created", table_name="mistakes")
    op.drop_index("ix_mistakes_user_category", table_name="mistakes")
    op.drop_table("mistakes")
