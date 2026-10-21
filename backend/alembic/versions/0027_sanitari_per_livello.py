"""asse finitura sui sanitari: porta i bersagli di RUBINETTERIE allo stato v3

Fase 11 (v3.0). La curatela v2 dell'asse `finitura` sui sanitari era
incoerente (niente bidet ai livelli base e medio, vaso sospeso senza
cassetta). Il seed v3 la riscrive per codice voce, ma il seed e'
create-if-missing: su un DB gia' seminato in v2 le vecchie righe resterebbero
accanto alle nuove, e un `escludi` v2 vincerebbe su un `includi` v3.

Questa migrazione lascia ACCESI solo gli `includi` dell'insieme v3 e spegne
ogni altro effetto dell'asse `finitura` sulle voci di RUBINETTERIE (`B.6.x`).
Le righe v3 che non esistono ancora le crea il seed al boot. Mai DELETE.

Su un DB vuoto non fa nulla.

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0027'
down_revision: Union[str, Sequence[str], None] = '0026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (opzione di `finitura`, codice voce) che restano `includi` attivi.
_SANITARI_V3: frozenset[tuple[str, str]] = frozenset(
    [(o, c) for o in ("base",) for c in ("B.6.1", "B.6.2", "B.6.3", "B.6.4", "B.6.6", "B.6.7", "B.6.8")]
    + [
        (o, c)
        for o in ("medio", "alto")
        for c in ("B.6.1", "B.6.2", "B.6.3", "B.6.4", "B.6.6", "B.6.9", "B.6.10", "B.6.11", "B.6.12")
    ]
)


def upgrade() -> None:
    bind = op.get_bind()
    righe = bind.execute(
        sa.text(
            "SELECT e.id, o.code, e.tipo_effetto, v.codice"
            " FROM effetto_opzione e"
            " JOIN opzione_domanda o ON o.id = e.opzione_id"
            " JOIN voce v ON v.id = e.target_voce_id"
            " WHERE o.domanda_code = 'finitura' AND v.codice LIKE 'B.6.%'"
        )
    ).fetchall()
    for effetto_id, opzione_code, tipo_effetto, codice in righe:
        attivo = tipo_effetto == "includi" and (opzione_code, codice) in _SANITARI_V3
        bind.execute(
            sa.text("UPDATE effetto_opzione SET attivo = :attivo WHERE id = :id"),
            {"attivo": attivo, "id": effetto_id},
        )


def downgrade() -> None:
    """Riaccendere a mano dal pannello: la migrazione non sa quali di queste
    righe fossero gia' spente prima."""
