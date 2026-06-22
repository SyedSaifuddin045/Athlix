"""Add waitlist_entries table

Revision ID: 7d3b1c1a0f0a
Revises: 6112d91695e7
Create Date: 2026-06-22 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7d3b1c1a0f0a"
down_revision: Union[str, Sequence[str], None] = "6112d91695e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "waitlist_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("clerk_user_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_waitlist_email"),
        schema="app_schema",
    )


def downgrade() -> None:
    op.drop_table("waitlist_entries", schema="app_schema")
