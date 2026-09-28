"""asse finitura da voce.livello + quantita_per_unita da domanda_mirata_key (CFG-03, QST-05)

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-26 00:00:00.000000

Il percorso senza perdita per i database che esistono gia' (dev.db e
produzione). Il 09-02 ha insegnato al seed a creare, su un DB NUOVO, la
domanda `finitura` e gli effetti `quantita_per_unita` sulle domande stepper
mirate (bagni/porte/condizionatori) leggendo un JSON di curatela. Ma un
database ESISTENTE non ripassa mai dal seed per queste righe (D-41: il seed e'
create-if-missing) — la curatela fatta a mano da pannello su `voce.livello`
(21 voci in dev.db, sconosciuta in produzione) e le chiavi mirate in
`coefficiente_qta_voce.domanda_mirata_key` restano lettera morta finche' non
diventano le stesse righe di `effetto_opzione` che il seed avrebbe creato.

Questa migrazione legge quella curatela e produce GLI STESSI effetti del
seed, con la STESSA chiave naturale (opzione, tipo_effetto, target_*,
tipo_code) — cosi' un seed successivo la riconosce e non duplica nulla
(idempotenza D-41).

Scelta fissata (Open Question 1 del RESEARCH): NESSUN DROP di colonna in
questa fase. `voce.livello`, `coefficiente_qta_voce.domanda_mirata_key` e
`stima.livelli_pro_json` restano dato storico, non letti dal motore (guard
nel 09-03). Questa migrazione non aggiunge e non toglie nessuna colonna:
nessun rischio del Pitfall 1 (ADD COLUMN con default non costante) perche'
non tocca lo schema, solo le righe di `domanda`/`opzione_domanda`/
`effetto_opzione`. Per questo usa `op.get_bind()` + `sa.table()`/`sa.column()`
locali, mai i modelli ORM: una migrazione dati non deve dipendere da come
saranno i modelli in futuro.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0021'
down_revision: Union[str, Sequence[str], None] = '0020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DOMANDA_FINITURA = "finitura"
OPZIONE_VALORE = "valore"
TIPO_INCLUDI = "includi"
TIPO_QUANTITA_PER_UNITA = "quantita_per_unita"

# Stessa forma dell'interfaccia del 09-02 (backend/seed_data/seed-domande.json):
# se una riga manca in `livello_finitura` (DB curato a mano, non ancora
# seminato con quella tabella) si usano questi letterali come fallback.
_LIVELLI_FALLBACK: dict[str, dict[str, object]] = {
    "base": {"nome": "Entry level", "ordine": 1, "is_default": False},
    "medio": {"nome": "Medio", "ordine": 2, "is_default": True},
    "alto": {"nome": "Lusso", "ordine": 3, "is_default": False},
}
_LIVELLI_VALIDI = frozenset(_LIVELLI_FALLBACK)


def _tabelle():
    """Definizioni locali delle tabelle toccate (mai i modelli ORM)."""
    voce = sa.table(
        "voce",
        sa.column("id"),
        sa.column("livello"),
    )
    coefficiente = sa.table(
        "coefficiente_qta_voce",
        sa.column("voce_id"),
        sa.column("tipo_code"),
        sa.column("domanda_mirata_key"),
    )
    domanda = sa.table(
        "domanda",
        sa.column("code"),
        sa.column("testo"),
        sa.column("help"),
        sa.column("tipo_controllo"),
        sa.column("gruppo"),
        sa.column("ordine"),
        sa.column("tier_minimo"),
        sa.column("obbligatoria"),
        sa.column("attiva"),
        sa.column("updated_at"),
    )
    opzione = sa.table(
        "opzione_domanda",
        sa.column("id"),
        sa.column("domanda_code"),
        sa.column("code"),
        sa.column("etichetta"),
        sa.column("descrizione"),
        sa.column("is_default"),
        sa.column("ordine"),
        sa.column("attiva"),
        sa.column("updated_at"),
    )
    effetto = sa.table(
        "effetto_opzione",
        sa.column("id"),
        sa.column("opzione_id"),
        sa.column("tipo_effetto"),
        sa.column("target_categoria_code"),
        sa.column("target_sottocategoria_id"),
        sa.column("target_voce_id"),
        sa.column("tipo_code"),
        sa.column("valore"),
        sa.column("attivo"),
        sa.column("updated_at"),
    )
    livello_finitura = sa.table(
        "livello_finitura",
        sa.column("code"),
        sa.column("nome"),
        sa.column("descrizione"),
        sa.column("ordine"),
        sa.column("is_default"),
    )
    tipo_ristrutturazione = sa.table(
        "tipo_ristrutturazione",
        sa.column("code"),
    )
    return voce, coefficiente, domanda, opzione, effetto, livello_finitura, tipo_ristrutturazione


def _effetto_esiste(bind, effetto, **chiave) -> bool:
    condizioni = [
        (effetto.c[colonna] == valore) if valore is not None else effetto.c[colonna].is_(None)
        for colonna, valore in chiave.items()
    ]
    riga = bind.execute(sa.select(effetto.c.id).where(*condizioni)).first()
    return riga is not None


def upgrade() -> None:
    """Trasforma la curatela in effetti (asse finitura + quantita mirate)."""
    bind = op.get_bind()
    adesso = datetime.now(timezone.utc).replace(tzinfo=None)
    (
        voce,
        coefficiente,
        domanda,
        opzione,
        effetto,
        livello_finitura,
        tipo_ristrutturazione,
    ) = _tabelle()

    # --- (A) voce.livello -> domanda "finitura" + effetti includi ---------
    voci_livellate = bind.execute(
        sa.select(voce.c.id, voce.c.livello).where(voce.c.livello.isnot(None))
    ).all()
    voci_valide = [(vid, liv) for vid, liv in voci_livellate if liv in _LIVELLI_VALIDI]

    if voci_valide:
        riga_domanda = bind.execute(
            sa.select(domanda.c.code).where(domanda.c.code == DOMANDA_FINITURA)
        ).first()
        if riga_domanda is None:
            bind.execute(
                sa.insert(domanda).values(
                    code=DOMANDA_FINITURA,
                    testo="Livello di finitura",
                    help="Cambia i materiali considerati nel computo, non le lavorazioni.",
                    tipo_controllo="scelta_singola",
                    gruppo="configuratore_pro",
                    ordine=200,
                    tier_minimo="pro",
                    obbligatoria=False,
                    attiva=True,
                    updated_at=adesso,
                )
            )

        livelli_presenti = sorted({liv for _, liv in voci_valide})
        opzione_id_per_livello: dict[str, int] = {}
        for liv in livelli_presenti:
            riga_opzione = bind.execute(
                sa.select(opzione.c.id).where(
                    opzione.c.domanda_code == DOMANDA_FINITURA,
                    opzione.c.code == liv,
                )
            ).first()
            if riga_opzione is not None:
                opzione_id_per_livello[liv] = riga_opzione[0]
                continue

            riga_livello = bind.execute(
                sa.select(
                    livello_finitura.c.nome,
                    livello_finitura.c.descrizione,
                    livello_finitura.c.ordine,
                    livello_finitura.c.is_default,
                ).where(livello_finitura.c.code == liv)
            ).first()
            if riga_livello is not None:
                nome, descrizione, ordine, is_default = riga_livello
            else:
                fallback = _LIVELLI_FALLBACK[liv]
                nome, descrizione, ordine, is_default = (
                    fallback["nome"],
                    None,
                    fallback["ordine"],
                    fallback["is_default"],
                )

            bind.execute(
                sa.insert(opzione).values(
                    domanda_code=DOMANDA_FINITURA,
                    code=liv,
                    etichetta=nome,
                    descrizione=descrizione,
                    is_default=bool(is_default),
                    ordine=ordine,
                    attiva=True,
                    updated_at=adesso,
                )
            )
            nuovo_id = bind.execute(
                sa.select(opzione.c.id).where(
                    opzione.c.domanda_code == DOMANDA_FINITURA,
                    opzione.c.code == liv,
                )
            ).scalar_one()
            opzione_id_per_livello[liv] = nuovo_id

        for voce_id, liv in voci_valide:
            opzione_id = opzione_id_per_livello[liv]
            if _effetto_esiste(
                bind,
                effetto,
                opzione_id=opzione_id,
                tipo_effetto=TIPO_INCLUDI,
                target_categoria_code=None,
                target_sottocategoria_id=None,
                target_voce_id=voce_id,
                tipo_code=None,
            ):
                continue
            bind.execute(
                sa.insert(effetto).values(
                    opzione_id=opzione_id,
                    tipo_effetto=TIPO_INCLUDI,
                    target_categoria_code=None,
                    target_sottocategoria_id=None,
                    target_voce_id=voce_id,
                    tipo_code=None,
                    valore=None,
                    attivo=True,
                    updated_at=adesso,
                )
            )

    # --- (B) coefficiente_qta_voce.domanda_mirata_key -> quantita_per_unita
    tutti_i_tipi = {
        riga[0] for riga in bind.execute(sa.select(tipo_ristrutturazione.c.code)).all()
    }

    righe_mirate = bind.execute(
        sa.select(
            coefficiente.c.voce_id,
            coefficiente.c.tipo_code,
            coefficiente.c.domanda_mirata_key,
        ).where(coefficiente.c.domanda_mirata_key.isnot(None))
    ).all()

    gruppi: dict[tuple[int, str], set[str]] = {}
    for voce_id, tipo_code, chiave in righe_mirate:
        gruppi.setdefault((voce_id, chiave), set()).add(tipo_code)

    _opzione_valore_cache: dict[str, int | None] = {}

    def _opzione_valore_id(chiave: str) -> int | None:
        if chiave not in _opzione_valore_cache:
            riga = bind.execute(
                sa.select(opzione.c.id).where(
                    opzione.c.domanda_code == chiave,
                    opzione.c.code == OPZIONE_VALORE,
                )
            ).first()
            _opzione_valore_cache[chiave] = riga[0] if riga is not None else None
        return _opzione_valore_cache[chiave]

    for (voce_id, chiave), tipi_presenti in gruppi.items():
        opzione_id = _opzione_valore_id(chiave)
        if opzione_id is None:
            # Nessuna domanda con questo code: chiave sconosciuta, saltata in
            # silenzio (stesso comportamento dei bersagli naturali rotti del
            # seed, D-24: mai un boot fallito per un dato di curatela).
            continue

        copre_tutti_i_tipi = bool(tutti_i_tipi) and tipi_presenti >= tutti_i_tipi
        tipi_da_scrivere: tuple[str | None, ...] = (None,) if copre_tutti_i_tipi else tuple(
            sorted(tipi_presenti)
        )

        for tipo_code in tipi_da_scrivere:
            if _effetto_esiste(
                bind,
                effetto,
                opzione_id=opzione_id,
                tipo_effetto=TIPO_QUANTITA_PER_UNITA,
                target_categoria_code=None,
                target_sottocategoria_id=None,
                target_voce_id=voce_id,
                tipo_code=tipo_code,
            ):
                continue
            bind.execute(
                sa.insert(effetto).values(
                    opzione_id=opzione_id,
                    tipo_effetto=TIPO_QUANTITA_PER_UNITA,
                    target_categoria_code=None,
                    target_sottocategoria_id=None,
                    target_voce_id=voce_id,
                    tipo_code=tipo_code,
                    valore=1,
                    attivo=True,
                    updated_at=adesso,
                )
            )


def downgrade() -> None:
    """Rimuove esattamente gli effetti che questa migrazione avrebbe creato.

    Non tocca `voce.livello` ne' `coefficiente_qta_voce.domanda_mirata_key`
    (dato storico, mai scritto da questa migrazione).

    WR-02 (code review 09-08): non cancella piu' `domanda`/`opzione_domanda`
    di `finitura`. `upgrade()` le crea SOLO se `riga_domanda is None` — su un
    DB dove `finitura` preesisteva (es. gia' seminata dal seed su un DB
    nuovo, D-41) l'upgrade e' un no-op per la sezione (A), ma il vecchio
    downgrade cancellava comunque domanda/opzioni, distruggendo curatela che
    l'upgrade non aveva mai scritto — un downgrade asimmetrico e non
    idempotente. Ora la sezione (A) del downgrade rimuove SOLO gli effetti
    `includi` il cui bersaglio e' una voce con `voce.livello == opzione.code`
    — esattamente cio' che la sezione (A) dell'upgrade crea, stesso principio
    della 0022 (il cui downgrade tocca solo effetti, mai domanda/opzione).
    """
    bind = op.get_bind()
    (
        voce,
        coefficiente,
        domanda,
        opzione,
        effetto,
        livello_finitura,
        tipo_ristrutturazione,
    ) = _tabelle()

    # --- (B) quantita_per_unita sulle chiavi mirate ------------------------
    chiavi_mirate = {
        riga[0]
        for riga in bind.execute(
            sa.select(coefficiente.c.domanda_mirata_key).where(
                coefficiente.c.domanda_mirata_key.isnot(None)
            )
        ).all()
    }
    for chiave in chiavi_mirate:
        riga_opzione = bind.execute(
            sa.select(opzione.c.id).where(
                opzione.c.domanda_code == chiave,
                opzione.c.code == OPZIONE_VALORE,
            )
        ).first()
        if riga_opzione is None:
            continue
        opzione_id = riga_opzione[0]
        voce_ids = {
            riga[0]
            for riga in bind.execute(
                sa.select(coefficiente.c.voce_id).where(
                    coefficiente.c.domanda_mirata_key == chiave
                )
            ).all()
        }
        if not voce_ids:
            continue
        bind.execute(
            sa.delete(effetto).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == TIPO_QUANTITA_PER_UNITA,
                effetto.c.valore == 1,
                effetto.c.target_voce_id.in_(voce_ids),
            )
        )

    # --- (A) solo gli effetti includi creati da QUESTA migrazione ----------
    # Bersaglio: voce.livello == opzione.code — la stessa condizione che la
    # sezione (A) dell'upgrade usa per crearli. Un `includi` curato a mano su
    # una voce SENZA livello (bersaglio non prodotto dall'upgrade) non viene
    # mai toccato; `domanda`/`opzione_domanda` restano sempre, anche se dopo
    # questo downgrade non hanno piu' alcun effetto `includi` residuo.
    opzioni_finitura = bind.execute(
        sa.select(opzione.c.id, opzione.c.code).where(opzione.c.domanda_code == DOMANDA_FINITURA)
    ).all()
    for opzione_id, opzione_code in opzioni_finitura:
        voci_del_livello = bind.execute(
            sa.select(voce.c.id).where(voce.c.livello == opzione_code)
        ).all()
        voce_ids = [riga[0] for riga in voci_del_livello]
        if not voce_ids:
            continue
        bind.execute(
            sa.delete(effetto).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == TIPO_INCLUDI,
                effetto.c.target_voce_id.in_(voce_ids),
            )
        )
