"""Add first_name and last_name to users

Revision ID: ec4d54e4f5b9
Revises: 8f9c049a0bbb
Create Date: 2026-06-08 08:27:02.892144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec4d54e4f5b9'
down_revision: Union[str, Sequence[str], None] = '8f9c049a0bbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add first_name and last_name columns to users."""
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
    """Remove first_name and last_name columns from users."""
    op.drop_column("users", "last_name", schema="app_schema")
    op.drop_column("users", "first_name", schema="app_schema")
