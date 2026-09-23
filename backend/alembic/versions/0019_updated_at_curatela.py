"""updated_at sulle nove tabelle curate: guardia di staleness per il re-import (D-11)

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-22 00:00:00.000000

"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0019'
down_revision: Union[str, Sequence[str], None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Le nove tabelle curate su cui D-11 chiede la guardia di staleness.
_TABELLE: tuple[str, ...] = (
    "sottocategoria",
    "voce",
    "coefficiente_qta_voce",
    "moltiplicatore",
    "extra",
    "categoria",
    "listino_categoria",
    "forfait_arredo",
    "lead",
)


def upgrade() -> None:
    """Upgrade schema: aggiunge `updated_at` alle nove tabelle curate.

    D-11 chiede di poter dire, riga per riga, se un record e' cambiato nel
    database dopo che un file di export e' stato generato — senza questa
    colonna la domanda non ha risposta.

    La colonna va aggiunta in tre passi, e non con un singolo `add_column`
    con `server_default=func.now()`: SQLite (il motore di sviluppo, e il
    default di `DATABASE_URL`) rifiuta `ALTER TABLE ... ADD COLUMN ...
    DEFAULT CURRENT_TIMESTAMP` con `Cannot add a column with non-constant
    default`, perche' in ADD COLUMN accetta solo default costanti.

    I tre passi sono:

    1. `add_column` della colonna come nullable e senza default — accettato
       da tutti i motori;
    2. backfill esplicito delle righe esistenti con l'istante della
       migrazione. Quell'istante e' anteriore a qualunque export generato
       dopo, quindi il primo re-import non marchera' tutto come superato:
       e' la proprieta' su cui si regge la guardia di staleness;
    3. `batch_alter_table` per stringere il vincolo a NOT NULL e installare
       `server_default=now()`. Su SQLite `batch_alter_table` ricostruisce la
       tabella (CREATE della nuova + copia + DROP + RENAME), e dentro un
       CREATE TABLE il default CURRENT_TIMESTAMP e' invece legale. Sugli
       altri motori degrada a un normale ALTER COLUMN.

    Il `server_default` del passo 3 non e' cosmetico: i modelli ORM
    dichiarano `server_default=func.now()` senza un default lato Python,
    quindi un INSERT che non valorizza `updated_at` (ogni riga nuova creata
    dall'import) si appoggia al default del database. Senza di esso lo
    schema migrato divergerebbe da quello costruito da `create_all` e quegli
    INSERT fallirebbero per violazione di NOT NULL.
    """
    # `datetime.now(timezone.utc)` e' consapevole del fuso; la colonna e' un
    # DateTime naive, quindi si scrive l'istante UTC senza tzinfo per restare
    # coerenti con quanto scrive `func.now()` su SQLite.
    adesso = datetime.now(timezone.utc).replace(tzinfo=None)

    for tabella in _TABELLE:
        op.add_column(tabella, sa.Column("updated_at", sa.DateTime(), nullable=True))
        op.execute(
            sa.text(f"UPDATE {tabella} SET updated_at = :adesso").bindparams(adesso=adesso)
        )
        with op.batch_alter_table(tabella) as batch:
            batch.alter_column(
                "updated_at",
                existing_type=sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            )


def downgrade() -> None:
    """Downgrade schema: nove `drop_column` speculari.

    Anche il drop passa dal batch: su SQLite `DROP COLUMN` nativo esiste solo
    dalla 3.35 e non copre le colonne coinvolte in indici o vincoli, mentre
    la ricostruzione della tabella funziona sempre ed e' simmetrica a quanto
    fa `upgrade`.
    """
    for tabella in reversed(_TABELLE):
        with op.batch_alter_table(tabella) as batch:
            batch.drop_column("updated_at")
