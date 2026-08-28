"""testo

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, Sequence[str], None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. SOLO additivo: nessuna tabella/seed esistente toccata (D-24)."""
    op.create_table(
        'testo',
        sa.Column('chiave', sa.String(length=100), nullable=False),
        sa.Column('valore', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('chiave'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('testo')
