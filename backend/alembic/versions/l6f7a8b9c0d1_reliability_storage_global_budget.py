"""Blob storage in Postgres, global AI budget, stale-grading reconciliation, token versions.

Revision ID: l6f7a8b9c0d1
Revises: k5e6f7a8b9c0
"""
from alembic import op
import sqlalchemy as sa

revision = "l6f7a8b9c0d1"
down_revision = "k5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stored_files",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("size", sa.Integer, nullable=False),
        sa.Column("data", sa.LargeBinary, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_stored_files_owner_id", "stored_files", ["owner_id"])
    op.create_table(
        "ai_global_budget",
        sa.Column("period", sa.String(16), primary_key=True),
        sa.Column("used", sa.Integer, nullable=False),
        sa.CheckConstraint("used >= 0", name="ck_ai_global_budget_used"),
    )
    op.add_column("ai_reservations", sa.Column("charged", sa.Boolean, nullable=False, server_default=sa.false()))
    # Before this migration every Writing/Speaking reservation consumed a lifetime
    # review (vocabulary ones never did). A reservation still "reserved" now belongs
    # to a grading a deploy may have killed, so mark it charged: the stale sweep then
    # refunds it. Quota-exempt users have no such bucket row, and the refund only
    # touches a bucket with used > 0, so they are unaffected.
    op.execute(
        sa.text("UPDATE ai_reservations SET charged = :yes WHERE status = 'reserved' AND kind IN ('writing', 'speaking')")
        .bindparams(yes=True)
    )
    op.add_column("writing_submissions", sa.Column("status_updated_at", sa.DateTime, nullable=True))
    op.add_column("users", sa.Column("token_version", sa.Integer, nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("users", "token_version")
    op.drop_column("writing_submissions", "status_updated_at")
    op.drop_column("ai_reservations", "charged")
    op.drop_table("ai_global_budget")
    op.drop_index("ix_stored_files_owner_id", table_name="stored_files")
    op.drop_table("stored_files")
