"""stima.budget_eur — budget dichiarato dall'utente, fuori dallo snapshot

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0024'
down_revision: Union[str, Sequence[str], None] = '0023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. SOLO additivo: una colonna nullable su `stima`.

    Il budget e' un parametro dell'utente (EUR, IVA inclusa), modificabile nel
    tempo: vive in colonna e non nello snapshot `risultato_json`, che resta
    scritto una volta. NULL = nessun budget dichiarato; nessun backfill.
    """
    op.add_column('stima', sa.Column('budget_eur', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('stima') as batch_op:
        batch_op.drop_column('budget_eur')
