"""add primary_goal to user_profiles

Revision ID: 18af4fbd352f
Revises: c8d9e0f1a2b3
Create Date: 2026-06-26 12:22:46.142557

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '18af4fbd352f'
down_revision: Union[str, Sequence[str], None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('primary_goal', sa.String(), nullable=True), schema='app_schema')


def downgrade() -> None:
    op.drop_column('user_profiles', 'primary_goal', schema='app_schema')
