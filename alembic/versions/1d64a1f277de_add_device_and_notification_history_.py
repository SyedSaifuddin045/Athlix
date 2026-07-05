"""add device and notification_history tables

Revision ID: 1d64a1f277de
Revises: d4c8f9a0b2e1
Create Date: 2026-07-05 12:44:14.938877

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1d64a1f277de"
down_revision: Union[str, Sequence[str], None] = "d4c8f9a0b2e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("push_token", sa.Text(), nullable=False),
        sa.Column("device_name", sa.String(length=128), nullable=True),
        sa.Column("app_version", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app_schema.users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="app_schema",
    )
    op.create_index(
        op.f("ix_app_schema_devices_user_id"),
        "devices",
        ["user_id"],
        unique=False,
        schema="app_schema",
    )
    op.create_table(
        "notification_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider_response", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app_schema.users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="app_schema",
    )
    op.create_index(
        op.f("ix_app_schema_notification_history_user_id"),
        "notification_history",
        ["user_id"],
        unique=False,
        schema="app_schema",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_app_schema_notification_history_user_id"),
        table_name="notification_history",
        schema="app_schema",
    )
    op.drop_table("notification_history", schema="app_schema")
    op.drop_index(
        op.f("ix_app_schema_devices_user_id"),
        table_name="devices",
        schema="app_schema",
    )
    op.drop_table("devices", schema="app_schema")
