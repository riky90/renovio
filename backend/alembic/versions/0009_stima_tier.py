"""stima.tier — congela il piano con cui la stima e' stata creata

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0009'
down_revision: Union[str, Sequence[str], None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. SOLO additivo: una colonna nullable su `stima` (D-24).

    Prima di questa revisione il tier non era registrato da nessuna parte e
    l'accesso al dettaglio Pro dipendeva dall'abbonamento CORRENTE: appena un
    utente si abbonava, tutte le sue stime Free storiche si comportavano da
    Pro. La colonna congela il piano al momento del salvataggio.

    Backfill in due passi, SQL portabile SQLite/Postgres:
      1. 'pro' alle stime di chi ha un abbonamento attivo oggi — chi e' Pro
         adesso ha quasi certamente creato quelle stime da Pro, e marcarle
         free gli toglierebbe un dettaglio che ha gia' visto;
      2. 'free' a tutto il resto.
    """
    op.add_column('stima', sa.Column('tier', sa.String(length=16), nullable=True))

    op.execute(
        """
        UPDATE stima SET tier = 'pro'
        WHERE user_id IN (
            SELECT user_id FROM subscription
            WHERE stato = 'attivo'
              AND (scaduta_il IS NULL OR scaduta_il > CURRENT_TIMESTAMP)
        )
        """
    )
    op.execute("UPDATE stima SET tier = 'free' WHERE tier IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('stima', 'tier')
