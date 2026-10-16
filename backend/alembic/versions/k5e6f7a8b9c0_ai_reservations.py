"""Add atomic AI quota counters and in-flight reservations."""
from alembic import op
import sqlalchemy as sa

revision = "k5e6f7a8b9c0"
down_revision = "j4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("ai_quota_buckets",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("kind", sa.String(32), primary_key=True),
        sa.Column("period", sa.String(16), primary_key=True),
        sa.Column("used", sa.Integer(), nullable=False),
        sa.CheckConstraint("used >= 0", name="ck_ai_quota_used"))
    op.create_table("ai_reservations",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("active_resource", sa.String(160), nullable=True, unique=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_ai_reservations_user_id", "ai_reservations", ["user_id"])


def downgrade():
    op.drop_table("ai_reservations")
    op.drop_table("ai_quota_buckets")
