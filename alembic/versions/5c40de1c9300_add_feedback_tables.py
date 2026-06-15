"""Add feedback tables

Revision ID: 5c40de1c9300
Revises: 8f9c049a0bbb
Create Date: 2026-06-12 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c40de1c9300'
down_revision: Union[str, Sequence[str], None] = '8f9c049a0bbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('feedbacks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.Column('upvotes_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['app_schema.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='app_schema',
    )
    op.create_table('feedback_votes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('feedback_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['feedback_id'], ['app_schema.feedbacks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['app_schema.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('feedback_id', 'user_id', name='uq_feedback_vote'),
        schema='app_schema',
    )
    op.create_table('feedback_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('feedback_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['feedback_id'], ['app_schema.feedbacks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['app_schema.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='app_schema',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('feedback_comments', schema='app_schema')
    op.drop_table('feedback_votes', schema='app_schema')
    op.drop_table('feedbacks', schema='app_schema')
