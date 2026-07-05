"""add user_notification_settings table

Revision ID: 7facd4fee157
Revises: 1d64a1f277de
Create Date: 2026-07-05 13:42:33.859018

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '7facd4fee157'
down_revision: Union[str, Sequence[str], None] = '1d64a1f277de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user_notification_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('morning_motivation_enabled', sa.Boolean(), nullable=False),
        sa.Column('inactivity_nudge_enabled', sa.Boolean(), nullable=False),
        sa.Column('milestone_enabled', sa.Boolean(), nullable=False),
        sa.Column('timezone', sa.String(length=64), nullable=False),
        sa.Column('preferred_send_hour', sa.Integer(), nullable=False),
        sa.Column('inactivity_threshold_hours', sa.Integer(), nullable=False),
        sa.Column('detected_timezone', sa.String(length=64), nullable=True),
        sa.Column('typical_workout_hour', sa.Integer(), nullable=True),
        sa.Column('typical_workout_days', sa.JSON(), nullable=True),
        sa.Column('last_milestone_workout_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['app_schema.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='app_schema',
    )
    op.create_index(
        op.f('ix_app_schema_user_notification_settings_user_id'),
        'user_notification_settings', ['user_id'],
        unique=True, schema='app_schema',
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_app_schema_user_notification_settings_user_id'),
        table_name='user_notification_settings', schema='app_schema',
    )
    op.drop_table('user_notification_settings', schema='app_schema')
