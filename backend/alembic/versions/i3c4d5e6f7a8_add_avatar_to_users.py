"""add avatar to users

Revision ID: i3c4d5e6f7a8
Revises: h2b3c4d5e6f7
Create Date: 2026-07-10

"""
from alembic import op
import sqlalchemy as sa


revision = "i3c4d5e6f7a8"
down_revision = "h2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("avatar", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar")
