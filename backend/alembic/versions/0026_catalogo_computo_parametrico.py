"""catalogo domande per il computo parametrico: spegne gli effetti sostituiti dalle voci

Fase 11 (v3.0, MOT-02). Con il computo parametrico la quantita' delle voci
viene dalle grandezze della casa: gli effetti v2 che stimavano lo stesso costo
in euro "a sentimento" lo conterebbero due volte. Questa migrazione li
DISATTIVA (mai DELETE: restano a pannello, riaccendibili):

  - tutti gli `eur_per_scostamento` (bagni, locali, piano, porte, finestre,
    condizionatori, muri): ora sono voci del computo;
  - i `moltiplicatore_categoria` di `livello_finiture`: il livello ora sceglie
    le voci B/C/D tramite l'asse `finitura`, non scala la categoria;
  - la domanda `impianti` e i suoi moltiplicatori: sostituita dalle domande
    d'intervento (elettrico, riscaldamento, cucina...);
  - l'`eur_fisso_categoria` di `interventi_efficientamento.cambio_caldaia`:
    ora accende la grandezza `caldaia_nuova`;
  - gli effetti dell'asse `finitura` sulle porte interne: il tipo di porta
    lo sceglie `interv_porte`.

Struttura: i tre stepper dei muri ricevono `attributo_code` (diventano
grandezze del computo). Si scrive solo dove il valore e' ancora quello v2.

Su un DB vuoto (produzione ferma alla v1, catalogo seminato dopo le
migrazioni) non fa nulla: il seed crea il catalogo gia' nella forma v3.

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0026'
down_revision: Union[str, Sequence[str], None] = '0025'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PORTE = ("Porta interna in legno con anta mobile%", "Porta in legno scorrevole interno muro%")


def upgrade() -> None:
    bind = op.get_bind()
    effetto = sa.table(
        "effetto_opzione",
        sa.column("id", sa.Integer),
        sa.column("opzione_id", sa.Integer),
        sa.column("tipo_effetto", sa.String),
        sa.column("target_voce_id", sa.Integer),
        sa.column("attivo", sa.Boolean),
    )
    opzione = sa.table(
        "opzione_domanda",
        sa.column("id", sa.Integer),
        sa.column("domanda_code", sa.String),
        sa.column("code", sa.String),
    )
    domanda = sa.table(
        "domanda",
        sa.column("code", sa.String),
        sa.column("attiva", sa.Boolean),
        sa.column("attributo_code", sa.String),
    )
    voce = sa.table(
        "voce",
        sa.column("id", sa.Integer),
        sa.column("descrizione", sa.String),
        sa.column("sottocategoria_id", sa.Integer),
    )
    sottocategoria = sa.table(
        "sottocategoria",
        sa.column("id", sa.Integer),
        sa.column("categoria_code", sa.String),
    )

    def opzioni_di(domanda_code: str, codice: str | None = None):
        q = sa.select(opzione.c.id).where(opzione.c.domanda_code == domanda_code)
        if codice is not None:
            q = q.where(opzione.c.code == codice)
        return q

    bind.execute(
        effetto.update().where(effetto.c.tipo_effetto == "eur_per_scostamento").values(attivo=False)
    )
    bind.execute(
        effetto.update()
        .where(
            effetto.c.opzione_id.in_(opzioni_di("livello_finiture")),
            effetto.c.tipo_effetto == "moltiplicatore_categoria",
        )
        .values(attivo=False)
    )
    bind.execute(
        effetto.update().where(effetto.c.opzione_id.in_(opzioni_di("impianti"))).values(attivo=False)
    )
    bind.execute(domanda.update().where(domanda.c.code == "impianti").values(attiva=False))
    bind.execute(
        effetto.update()
        .where(
            effetto.c.opzione_id.in_(opzioni_di("interventi_efficientamento", "cambio_caldaia")),
            effetto.c.tipo_effetto == "eur_fisso_categoria",
        )
        .values(attivo=False)
    )

    voci_porte = sa.select(voce.c.id).where(
        voce.c.sottocategoria_id.in_(
            sa.select(sottocategoria.c.id).where(sottocategoria.c.categoria_code == "C-SERRAMENTI")
        ),
        sa.or_(*(voce.c.descrizione.like(p) for p in _PORTE)),
    )
    bind.execute(
        effetto.update()
        .where(
            effetto.c.opzione_id.in_(opzioni_di("finitura")),
            effetto.c.target_voce_id.in_(voci_porte),
        )
        .values(attivo=False)
    )

    for code in ("muri_da_recuperare", "muri_da_rifare_mq", "muri_da_creare_mq"):
        bind.execute(
            domanda.update()
            .where(domanda.c.code == code, domanda.c.attributo_code.is_(None))
            .values(attributo_code=code)
        )


def downgrade() -> None:
    """Riaccendere a mano dal pannello: la migrazione non sa quali di questi
    effetti fossero gia' spenti prima, e riaccenderli tutti sarebbe peggio."""
