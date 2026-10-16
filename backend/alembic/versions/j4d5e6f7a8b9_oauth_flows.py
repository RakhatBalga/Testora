"""Persist short-lived, single-use Google authorization flows."""
from alembic import op
import sqlalchemy as sa

revision = "j4d5e6f7a8b9"
down_revision = "h2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "oauth_flows",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("verifier", sa.String(128), nullable=False),
        sa.Column("redirect_uri", sa.String(2048), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_oauth_flows_expires_at", "oauth_flows", ["expires_at"])


def downgrade():
    op.drop_table("oauth_flows")
