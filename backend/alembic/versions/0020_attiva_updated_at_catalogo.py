"""attiva su opzione_domanda/attesa_immobile, updated_at sul catalogo domande (D-27, D-40, D-11)

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-24 00:00:00.000000

Questa migrazione usa due tecniche diverse per due motivi diversi:

- `attiva` (D-27, D-40) si aggiunge con un `add_column` diretto, senza batch:
  il default e' la costante `"1"`, non `func.now()`, e SQLite accetta senza
  obiezioni `ALTER TABLE ... ADD COLUMN ... DEFAULT 1 NOT NULL` — il vincolo
  che ha rotto la 0019 (`Cannot add a column with non-constant default`)
  scatta solo sui default non costanti come CURRENT_TIMESTAMP.
- `updated_at` sulle cinque tabelle del catalogo (`domanda`, `opzione_domanda`,
  `effetto_opzione`, `attesa_immobile`, `derivazione_risposta`) ripete
  identici i tre passi della 0019, perche' li' il default e' `func.now()`:
  1. `add_column` nullable, senza default;
  2. backfill esplicito delle righe esistenti con l'istante della migrazione,
     cosi' il primo re-import non marca tutto come cambiato dopo l'export
     (D-11, guardia di staleness);
  3. `batch_alter_table` per stringere a NOT NULL e installare
     `server_default=func.now()` — su SQLite questo passo ricostruisce la
     tabella (CREATE+copia+DROP+RENAME) e dentro un CREATE TABLE il default
     CURRENT_TIMESTAMP e' legale.

Una sola migrazione per entrambe le colonne (discrezione di CONTEXT): sono
la stessa causa — il catalogo domande diventa curabile dal pannello — e non
c'e' ragione di spezzarle in due revisioni.
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0020'
down_revision: Union[str, Sequence[str], None] = '0019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Le cinque tabelle del catalogo domande a cui questa migrazione aggiunge
# `updated_at` (D-11). `attiva` va solo sulle due che non ce l'hanno ancora
# (D-27, D-40): `domanda` ed `effetto_opzione` (come `attivo`) e
# `derivazione_risposta` ce l'hanno gia'.
_TABELLE_UPDATED_AT: tuple[str, ...] = (
    "domanda",
    "opzione_domanda",
    "effetto_opzione",
    "attesa_immobile",
    "derivazione_risposta",
)

_TABELLE_ATTIVA: tuple[str, ...] = (
    "opzione_domanda",
    "attesa_immobile",
)


def upgrade() -> None:
    """Upgrade schema: `attiva` su due tabelle, `updated_at` su cinque."""
    for tabella in _TABELLE_ATTIVA:
        op.add_column(
            tabella,
            sa.Column("attiva", sa.Boolean(), nullable=False, server_default="1"),
        )

    # `datetime.now(timezone.utc)` e' consapevole del fuso; la colonna e' un
    # DateTime naive, quindi si scrive l'istante UTC senza tzinfo per restare
    # coerenti con quanto scrive `func.now()` su SQLite (stesso pattern 0019).
    adesso = datetime.now(timezone.utc).replace(tzinfo=None)

    for tabella in _TABELLE_UPDATED_AT:
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
    """Downgrade schema: in ordine inverso, `updated_at` poi `attiva`."""
    for tabella in reversed(_TABELLE_UPDATED_AT):
        with op.batch_alter_table(tabella) as batch:
            batch.drop_column("updated_at")

    for tabella in reversed(_TABELLE_ATTIVA):
        with op.batch_alter_table(tabella) as batch:
            batch.drop_column("attiva")
