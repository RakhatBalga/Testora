"""Idempotency key for Writing submissions.

Revision ID: m7a8b9c0d1e2
Revises: l6f7a8b9c0d1
"""
from alembic import op
import sqlalchemy as sa

revision = "m7a8b9c0d1e2"
down_revision = "l6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Expand only: a nullable column (no rewrite, no default) and a unique index
    # in which existing rows (all NULL) never collide.
    op.add_column("writing_submissions", sa.Column("submission_key", sa.String(), nullable=True))
    op.create_index(
        "uq_writing_submission_user_key", "writing_submissions", ["user_id", "submission_key"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_writing_submission_user_key", table_name="writing_submissions")
    op.drop_column("writing_submissions", "submission_key")
