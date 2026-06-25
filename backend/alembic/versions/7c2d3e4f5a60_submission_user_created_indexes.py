"""indexes on (user_id, created_at) for submission/attempt tables

Analytics filter by user_id and order by created_at on every dashboard load;
without these composite indexes those queries sequentially scan and degrade as
data grows.

Revision ID: 7c2d3e4f5a60
Revises: 6a1b2c3d4e50
Create Date: 2026-06-23
"""
from alembic import op

revision = "7c2d3e4f5a60"
down_revision = "6a1b2c3d4e50"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_writing_submissions_user_created",
        "writing_submissions",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_speaking_submissions_user_created",
        "speaking_submissions",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_attempts_user_created",
        "attempts",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_attempts_user_created", table_name="attempts")
    op.drop_index("ix_speaking_submissions_user_created", table_name="speaking_submissions")
    op.drop_index("ix_writing_submissions_user_created", table_name="writing_submissions")
