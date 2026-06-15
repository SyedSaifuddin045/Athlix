"""merge feedback_tables and name_fields branches

Revision ID: 6112d91695e7
Revises: 5c40de1c9300, ff41a2e3b9c1
Create Date: 2026-06-15 22:03:04.322564

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6112d91695e7'
down_revision: Union[str, Sequence[str], None] = ('5c40de1c9300', 'ff41a2e3b9c1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
