"""user profile fields (cognome, telefono, citta)

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, Sequence[str], None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. SOLO additivo: tre colonne profilo nullable su `user`,
    nessun dato esistente toccato (D-24). SQLite supporta ADD COLUMN nullable."""
    op.add_column('user', sa.Column('cognome', sa.String(length=200), nullable=True))
    op.add_column('user', sa.Column('telefono', sa.String(length=40), nullable=True))
    op.add_column('user', sa.Column('citta', sa.String(length=200), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user', 'citta')
    op.drop_column('user', 'telefono')
    op.drop_column('user', 'cognome')
