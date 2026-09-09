"""user avatar_url

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0013'
down_revision: Union[str, Sequence[str], None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """SOLO additivo: una colonna nullable su `user`, come la 0008. Nessun
    dato esistente toccato (D-24), SQLite supporta ADD COLUMN nullable."""
    op.add_column('user', sa.Column('avatar_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user', 'avatar_url')
