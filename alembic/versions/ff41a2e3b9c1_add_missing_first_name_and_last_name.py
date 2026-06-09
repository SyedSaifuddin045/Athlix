"""Add missing first_name and last_name columns to users table

This migration is needed because the previous migration
(ec4d54e4f5b9) was created as a no-op stub and marked as
already run in the database. This actually adds the columns.

Revision ID: ff41a2e3b9c1
Revises: ec4d54e4f5b9
Create Date: 2026-06-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ff41a2e3b9c1"
down_revision: Union[str, Sequence[str], None] = "ec4d54e4f5b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("first_name", sa.Text(), nullable=True),
        schema="app_schema",
    )
    op.add_column(
        "users",
        sa.Column("last_name", sa.Text(), nullable=True),
        schema="app_schema",
    )


def downgrade() -> None:
    op.drop_column("users", "last_name", schema="app_schema")
    op.drop_column("users", "first_name", schema="app_schema")
