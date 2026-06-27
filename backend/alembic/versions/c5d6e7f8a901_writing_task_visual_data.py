"""add structured visual data to writing tasks

Revision ID: c5d6e7f8a901
Revises: b4c5d6e7f890
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa


revision = "c5d6e7f8a901"
down_revision = "b4c5d6e7f890"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("writing_tasks", sa.Column("visual_data", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("writing_tasks", "visual_data")
