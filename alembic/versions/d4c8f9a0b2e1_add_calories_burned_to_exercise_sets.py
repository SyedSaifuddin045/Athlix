"""Add calories_burned column to exercise_sets table

Revision ID: d4c8f9a0b2e1
Revises: f2dc2ae8aa2b
Create Date: 2026-06-29 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4c8f9a0b2e1"
down_revision: Union[str, Sequence[str], None] = "f2dc2ae8aa2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exercise_sets",
        sa.Column("calories_burned", sa.Float(), nullable=True),
        schema="app_schema",
    )


def downgrade() -> None:
    op.drop_column("exercise_sets", "calories_burned", schema="app_schema")
