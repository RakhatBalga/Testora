"""add target band to users

Revision ID: b4c5d6e7f890
Revises: a0f1b2c3d4e0
Create Date: 2026-06-26

"""
from alembic import op
import sqlalchemy as sa


revision = "b4c5d6e7f890"
down_revision = "a0f1b2c3d4e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("target_band", sa.Float(), nullable=False, server_default="7.5"),
    )


def downgrade() -> None:
    op.drop_column("users", "target_band")
