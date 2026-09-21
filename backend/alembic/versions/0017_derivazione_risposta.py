"""derivazione_risposta: una risposta che l'utente non sa, dedotta da una che sa

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0017'
down_revision: Union[str, Sequence[str], None] = '0016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. SOLO additivo (D-24): una `create_table`.

    Il problema che risolve: "Qual e' la classe energetica attuale?" ha come
    risposta di default "Non la so", e finche' resta tale non ha effetti — vale
    a dire che vale classe C, la neutra. Ma l'anno di costruzione, che l'utente
    sa quasi sempre, dice molto sulla classe: un immobile anteriore al 1980 non
    e' in classe C.

    Perche' una tabella e non tre righe di codice
    ---------------------------------------------
    "Prima del 1980 -> G" e' un numero di dominio, esattamente come un prezzo o
    un coefficiente: la regola non negoziabile #3 dice che quei numeri stanno
    in database e si cambiano dal pannello admin, non con un deploy. La mappa
    qui sotto e' per di piu' una BOZZA da confermare con l'esperto, che e' la
    ragione piu' forte per non cablarla.

    Perche' generica e non `classe_energetica_da_anno`
    --------------------------------------------------
    Le colonne descrivono la forma del problema — "quando la domanda X vale
    `non_so`, leggi la domanda Y e deduci l'opzione Z" — non il caso specifico.
    La stessa forma serve il giorno in cui l'impianto termico ignoto si deduce
    dall'anno, o la tipologia di solaio dal tipo di immobile. Una tabella con
    il nome del primo caso d'uso avrebbe costretto a una seconda tabella
    identica al secondo.

    La derivazione si applica in `risolvi_scelte()` DOPO i default e PRIMA
    della visibilita' e degli effetti: da li' in poi nessun consumatore sa che
    la risposta e' stata dedotta invece che digitata, ed e' il punto — l'arredo,
    i bonus e il motore vedono tutti la stessa risposta risolta.
    """
    op.create_table(
        "derivazione_risposta",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # La domanda la cui risposta va dedotta (es. `classe_energetica_attuale`).
        sa.Column("domanda_code", sa.String(length=64), nullable=False),
        # L'opzione che significa "non lo so" e fa scattare la deduzione. E'
        # dato e non convenzione: nulla obbliga a chiamarla `non_so`.
        sa.Column("quando_opzione_code", sa.String(length=64), nullable=False),
        # La domanda da cui si deduce (es. `anno_costruzione`) e la sua risposta.
        sa.Column("da_domanda_code", sa.String(length=64), nullable=False),
        sa.Column("da_opzione_code", sa.String(length=64), nullable=False),
        # L'opzione che ne risulta (es. `g`).
        sa.Column("opzione_code", sa.String(length=64), nullable=False),
        sa.Column("attiva", sa.Boolean(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["domanda_code"], ["domanda.code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["da_domanda_code"], ["domanda.code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Una sola deduzione per (domanda dedotta, trigger, risposta fonte):
        # due righe in conflitto sarebbero un errore di curatela silenzioso.
        sa.UniqueConstraint(
            "domanda_code",
            "quando_opzione_code",
            "da_domanda_code",
            "da_opzione_code",
            name="uq_derivazione_risposta",
        ),
    )


    # --- dato obsoleto: le due opzioni di `efficientamento` -----------------
    #
    # `efficientamento` smette di essere una scelta a tre valori (no / una o
    # due classi / tre o piu') e diventa un filtro si-no, con il punto di
    # arrivo e gli interventi in due domande a parte. Le opzioni `una_due` e
    # `tre_piu` restano quindi senza modo di essere scelte da un toggle.
    #
    # Il seed non le cancella di proposito (D-24: nessun DELETE implicito, per
    # non portarsi via effetti curati a mano). Ma qui la rimozione e' il senso
    # stesso della migrazione, ed e' meglio farla una volta in modo esplicito
    # che lasciare in tabella due opzioni raggiungibili solo da un client che
    # posti la risposta vecchia: `_opzioni_scelte` le applicherebbe ancora.
    #
    # Gli effetti vanno cancellati per primi a mano: su SQLite il CASCADE
    # dipende da `PRAGMA foreign_keys`, che non e' garantito qui.
    op.execute(
        """
        DELETE FROM effetto_opzione
        WHERE opzione_id IN (
            SELECT id FROM opzione_domanda
            WHERE domanda_code = 'efficientamento' AND code IN ('una_due', 'tre_piu')
        )
        """
    )
    op.execute(
        """
        DELETE FROM opzione_domanda
        WHERE domanda_code = 'efficientamento' AND code IN ('una_due', 'tre_piu')
        """
    )


def downgrade() -> None:
    """Le due opzioni cancellate non tornano: erano dato, non schema, e il
    seed le ricrea solo se il JSON torna a elencarle."""
    op.drop_table("derivazione_risposta")
