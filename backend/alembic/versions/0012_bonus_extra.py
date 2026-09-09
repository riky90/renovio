"""bonus_extra: mapping extra -> bonus

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0012'
down_revision: Union[str, Sequence[str], None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Un solo `create_table`, nessuna colonna su tabelle esistenti: rischio
    zero su SQLite (D-24), stime salvate intatte.

    Le righe (quale extra e' detraibile, con quale bonus, per quale quota) non
    stanno qui ma nel seed idempotente, cosi' restano curabili dal pannello
    admin senza una nuova migrazione.
    """
    op.create_table(
        'bonus_extra',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('bonus_code', sa.String(length=32), nullable=False),
        sa.Column('extra_code', sa.String(length=32), nullable=False),
        sa.Column('quota_ammissibile_pct', sa.Numeric(precision=5, scale=4),
                  server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['bonus_code'], ['bonus_fiscale.code']),
        sa.ForeignKeyConstraint(['extra_code'], ['extra.code']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bonus_code', 'extra_code', name='uq_bonus_extra'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('bonus_extra')
