"""test simulator fields: review flags, duration, breakdown

Revision ID: 6a1b2c3d4e50
Revises: 5e1a3c7d9f30
Create Date: 2026-06-23 09:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6a1b2c3d4e50"
down_revision: Union[str, Sequence[str], None] = "5e1a3c7d9f30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("attempts", sa.Column("duration_seconds", sa.Integer(), nullable=True))
    op.add_column("attempts", sa.Column("breakdown", sa.JSON(), nullable=True))
    op.add_column(
        "answer_records",
        sa.Column("marked_for_review", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("answer_records", "marked_for_review")
    op.drop_column("attempts", "breakdown")
    op.drop_column("attempts", "duration_seconds")
