"""Controllo CFG-02 a MONDO APERTO (09-10-PLAN.md Task 1), gap G1/G2 di
09-HUMAN-UAT.md: il vecchio controllo di conteggio (`test_dettaglio_pro_alternative.py`)
elenca solo le famiglie che GIA' CONOSCE, quindi una voce pavimento dimenticata
dalla curatela passa il test invece di farlo fallire (variante "a-check-that-
cannot-fail" a mondo chiuso).

Qui il perimetro, gli assi, le combinazioni di opzioni e i gruppi di
lavorazione si DERIVANO dal catalogo seminato (`Domanda`/`OpzioneDomanda`/
`EffettoOpzione`), mai da una lista di codici scritta a mano nel test. La sola
eccezione, deliberata e piccola, e' `VOCI_COMUNI`: le pochissime voci che
DEVONO restare sempre incluse a prescindere da ogni asse (la quota bagno
D-02, il taglio della porta blindata, il materiale di posa). Ogni altra voce
del perimetro deve essere "governata" da un asse, o il controllo fallisce —
e' il default-deny che rende impossibile dimenticare una nuova voce pavimento
senza che il test se ne accorga.

Non rilegge la logica del motore: riusa `_compute`/`_identificatore`/
`_identificatori_presenti` da `test_dettaglio_pro_alternative.py` (stesso
precedente di quel file rispetto a `DettaglioProService.compute`)."""

from __future__ import annotations

import re
from decimal import Decimal
from itertools import product
from pathlib import Path

import pytest
from sqlalchemy import create_engine, or_

from app.db import Base
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Sottocategoria, Voce
from app.models.domanda import Domanda, EffettoOpzione, OpzioneDomanda
from app.services.effetti import (
    TIER_PRO,
    TIPO_ESCLUDI,
    TIPO_FATTORE_QUANTITA,
    TIPO_INCLUDI,
)
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test
from tests.test_dettaglio_pro_alternative import (
    _compute,
    _identificatore,
    _identificatori_presenti,
)

# --- perimetro S --------------------------------------------------------------

A6_CODICE = "A.6"
NOMI_PERIMETRO_B = frozenset(
    {
        "PAVIMENTI",
        "PAVIMENTI PARQUET",
        "PAVIMENTI E RIVESTIMENTI GRES",
        "BATTISCOPA",
        "MATERIALI DI POSA",
    }
)

# La SOLA lista scritta a mano: voci che restano sempre incluse a prescindere
# da ogni asse, con il motivo. Chiave = codice (A-EDILE) o descrizione esatta
# (B-FINITURE, senza codice). Una voce dimenticata qui e assente da ogni
# `includi`/`escludi` di un asse fa fallire test_perimetro_tutte_le_voci_classificate,
# non il contrario.
VOCI_COMUNI: dict[str, str] = {
    "A.6.1": "quota bagno D-02: posa del bagno sempre presente, ridotta da fattore_quantita",
    "A.6.11": "taglio porta blindata, non e' un'alternativa di pavimento",
    "Colle, stucchi distanziatori e cunei per la posa": (
        "materiale di posa del bagno e delle ceramiche"
    ),
}


def _voce_comune(voce: Voce) -> str | None:
    if voce.codice is not None and voce.codice in VOCI_COMUNI:
        return VOCI_COMUNI[voce.codice]
    return VOCI_COMUNI.get(voce.descrizione)


def _perimetro(session) -> list[Voce]:
    a6 = session.query(Sottocategoria).filter_by(categoria_code="A-EDILE", codice=A6_CODICE).one()
    sotto_ids: set[int] = {a6.id}

    for sotto in (
        session.query(Sottocategoria)
        .filter(Sottocategoria.categoria_code == "B-FINITURE", Sottocategoria.nome.in_(NOMI_PERIMETRO_B))
        .all()
    ):
        sotto_ids.add(sotto.id)

    # Ogni sottocategoria che contiene almeno una voce bersaglio di un
    # qualunque effetto dell'asse tipo_pavimento entra da sola: e' quello che
    # rende il perimetro capace di accorgersi di una NUOVA sottocategoria
    # pavimento, senza doverla scrivere qui a mano.
    for effetto in (
        session.query(EffettoOpzione)
        .join(OpzioneDomanda, EffettoOpzione.opzione_id == OpzioneDomanda.id)
        .filter(OpzioneDomanda.domanda_code == "tipo_pavimento")
        .all()
    ):
        if effetto.target_sottocategoria_id is not None:
            sotto_ids.add(effetto.target_sottocategoria_id)
        elif effetto.target_voce_id is not None:
            voce = session.get(Voce, effetto.target_voce_id)
            if voce is not None:
                sotto_ids.add(voce.sottocategoria_id)

    return (
        session.query(Voce)
        .filter(Voce.sottocategoria_id.in_(sotto_ids))
        .order_by(Voce.id)
        .all()
    )


# --- assi dal catalogo ---------------------------------------------------------


def _assi_pro(session) -> list[str]:
    """Le domande attive tier_minimo='pro' con almeno un `includi` attivo su
    un'opzione attiva. Oggi 'finitura' e 'tipo_pavimento' — mai scritte qui a
    mano, si leggono dal catalogo."""
    codici = (
        session.query(Domanda.code)
        .join(OpzioneDomanda, OpzioneDomanda.domanda_code == Domanda.code)
        .join(EffettoOpzione, EffettoOpzione.opzione_id == OpzioneDomanda.id)
        .filter(
            Domanda.attiva.is_(True),
            Domanda.tier_minimo == TIER_PRO,
            OpzioneDomanda.attiva.is_(True),
            EffettoOpzione.attivo.is_(True),
            EffettoOpzione.tipo_effetto == TIPO_INCLUDI,
        )
        .distinct()
        .all()
    )
    return [c[0] for c in codici]


def _opzioni_attive(session, domanda_code: str) -> list[str]:
    righe = (
        session.query(OpzioneDomanda.code)
        .filter(OpzioneDomanda.domanda_code == domanda_code, OpzioneDomanda.attiva.is_(True))
        .order_by(OpzioneDomanda.ordine, OpzioneDomanda.id)
        .all()
    )
    return [r[0] for r in righe]


def _bersaglio(voce: Voce):
    return or_(
        EffettoOpzione.target_voce_id == voce.id,
        EffettoOpzione.target_sottocategoria_id == voce.sottocategoria_id,
    )


def _voce_governata(session, voce: Voce, assi_domande: list[str]) -> bool:
    """Governata = bersaglio di un `includi` attivo di un'opzione attiva di un
    asse, oppure bersaglio di un `escludi` attivo su TUTTE le opzioni attive
    di un asse (esclusa sempre da quell'asse)."""
    for domanda_code in assi_domande:
        opzioni = (
            session.query(OpzioneDomanda)
            .filter_by(domanda_code=domanda_code, attiva=True)
            .all()
        )
        if not opzioni:
            continue
        opzione_ids = [o.id for o in opzioni]

        includi = (
            session.query(EffettoOpzione)
            .filter(
                EffettoOpzione.opzione_id.in_(opzione_ids),
                EffettoOpzione.attivo.is_(True),
                EffettoOpzione.tipo_effetto == TIPO_INCLUDI,
                _bersaglio(voce),
            )
            .first()
        )
        if includi is not None:
            return True

        opzioni_con_escludi = {
            row[0]
            for row in (
                session.query(EffettoOpzione.opzione_id)
                .filter(
                    EffettoOpzione.opzione_id.in_(opzione_ids),
                    EffettoOpzione.attivo.is_(True),
                    EffettoOpzione.tipo_effetto == TIPO_ESCLUDI,
                    _bersaglio(voce),
                )
                .distinct()
                .all()
            )
        }
        if opzione_ids and opzioni_con_escludi == set(opzione_ids):
            return True
    return False


# --- quota bagno D-02 su A.6.1 -------------------------------------------------


def _verifica_quota_bagno_a6_1(session) -> list[str]:
    a6 = session.query(Sottocategoria).filter_by(categoria_code="A-EDILE", codice=A6_CODICE).one()
    voci_a6 = {v.codice: v for v in session.query(Voce).filter_by(sottocategoria_id=a6.id).all()}
    a6_1 = voci_a6.get("A.6.1")
    if a6_1 is None:
        return ["A.6.1 non trovata nel catalogo: impossibile verificare la quota bagno D-02"]

    alternative_ids = [voci_a6[c].id for c in ("A.6.2", "A.6.5", "A.6.6") if c in voci_a6]

    opzioni = session.query(OpzioneDomanda).filter_by(domanda_code="tipo_pavimento", attiva=True).all()
    default = next((o for o in opzioni if o.is_default), None)

    problemi: list[str] = []
    for opz in opzioni:
        if default is not None and opz.id == default.id:
            continue
        include_alternativa = (
            session.query(EffettoOpzione)
            .filter(
                EffettoOpzione.opzione_id == opz.id,
                EffettoOpzione.attivo.is_(True),
                EffettoOpzione.tipo_effetto == TIPO_INCLUDI,
                EffettoOpzione.target_voce_id.in_(alternative_ids),
            )
            .first()
        )
        if include_alternativa is None:
            continue
        ha_fattore = (
            session.query(EffettoOpzione)
            .filter(
                EffettoOpzione.opzione_id == opz.id,
                EffettoOpzione.attivo.is_(True),
                EffettoOpzione.tipo_effetto == TIPO_FATTORE_QUANTITA,
                EffettoOpzione.target_voce_id == a6_1.id,
            )
            .first()
        )
        if ha_fattore is None:
            problemi.append(
                f"A.6.1 (quota bagno D-02): l'opzione tipo_pavimento={opz.code!r} include "
                "una posa alternativa (A.6.2/.5/.6) ma non ha fattore_quantita su A.6.1"
            )
    return problemi


# --- gruppi di lavorazione (derivati dal testo) --------------------------------


def _normalizza(testo: str) -> str:
    return re.sub(r"\s+", " ", testo.strip().lower())


def _gruppo_lavorazione(voce: Voce, categoria_code: str) -> str | None:
    testo = _normalizza(voce.descrizione)

    if "battiscopa" in testo or "zoccolino" in testo:
        return "battiscopa"
    if "levigatura" in testo:
        return "levigatura"
    if categoria_code == "A-EDILE" and "maxi lastra" in testo:
        return "posa_pavimento"
    if categoria_code == "A-EDILE" and testo.startswith("posa in opera dei rivestimenti"):
        return "posa_rivestimento"
    if (
        categoria_code == "A-EDILE"
        and testo.startswith("posa in opera")
        and any(k in testo for k in ("pavimentazion", "parquet", "mosaico"))
    ):
        return "posa_pavimento"
    if (
        categoria_code == "B-FINITURE"
        and voce.um == "mq"
        and "rivestiment" in testo
        and "per pavimentazion" not in testo
    ):
        return "fornitura_rivestimento"
    if (
        categoria_code == "B-FINITURE"
        and voce.um == "mq"
        and any(
            k in testo
            for k in (
                "pavimentazion",
                "pavimento",
                "pavimenti",
                "parquet",
                "moquette",
                "vinilico",
                "laminato",
                "tesserine",
            )
        )
    ):
        return "fornitura_pavimento"
    return None


# --- slot quota bagno (derivato dal catalogo) ----------------------------------


def _slot(session, voce: Voce, opzione_tipo_pavimento_scelta: OpzioneDomanda | None) -> str:
    if opzione_tipo_pavimento_scelta is None:
        return "casa"
    ha_fattore = (
        session.query(EffettoOpzione)
        .filter(
            EffettoOpzione.opzione_id == opzione_tipo_pavimento_scelta.id,
            EffettoOpzione.attivo.is_(True),
            EffettoOpzione.tipo_effetto == TIPO_FATTORE_QUANTITA,
            _bersaglio(voce),
        )
        .first()
    )
    return "bagno" if ha_fattore is not None else "casa"


def _verifica_una_voce_per_gruppo(
    session, result, risposte: dict, perimetro: list[Voce], sotto_cache: dict[int, Sottocategoria]
) -> list[str]:
    ident_to_voce = {
        _identificatore(v.sottocategoria_id, v.codice, v.descrizione): v for v in perimetro
    }
    presenti = _identificatori_presenti(session, result)
    voci_presenti = [ident_to_voce[i] for i in presenti if i in ident_to_voce]

    opzioni_tp = session.query(OpzioneDomanda).filter_by(domanda_code="tipo_pavimento", attiva=True).all()
    per_code = {o.code: o for o in opzioni_tp}
    codice_scelto = risposte.get("tipo_pavimento")
    if codice_scelto not in per_code:
        default = next((o for o in opzioni_tp if o.is_default), None)
        opzione_scelta = default
    else:
        opzione_scelta = per_code[codice_scelto]

    def sotto_di(voce: Voce) -> Sottocategoria:
        if voce.sottocategoria_id not in sotto_cache:
            sotto_cache[voce.sottocategoria_id] = session.get(Sottocategoria, voce.sottocategoria_id)
        return sotto_cache[voce.sottocategoria_id]

    gruppi: dict[tuple[str, str, str], list[Voce]] = {}
    for v in voci_presenti:
        sotto = sotto_di(v)
        gruppo = _gruppo_lavorazione(v, sotto.categoria_code)
        if gruppo is None:
            continue
        chiave = (sotto.categoria_code, gruppo, _slot(session, v, opzione_scelta))
        gruppi.setdefault(chiave, []).append(v)

    problemi: list[str] = []
    for (categoria_code, gruppo, slot_nome), voci in sorted(gruppi.items()):
        if len(voci) > 1:
            elenco = "; ".join(repr(v.codice or v.descrizione[:60]) for v in voci)
            problemi.append(
                f"gruppo {gruppo!r} ({categoria_code}, slot {slot_nome!r}): "
                f"piu' di una voce presente: {elenco}"
            )
    return problemi


# --- la funzione pura, riusata da tutti i test ---------------------------------


def violazioni(session, result, risposte: dict) -> list[str]:
    """Tutte le violazioni CFG-02 a mondo aperto per un dato risultato di
    `DettaglioProService.compute()`. Pura rispetto a `result`/`risposte`;
    legge il catalogo da `session` per perimetro/assi/gruppi/slot."""
    problemi: list[str] = []

    perimetro = _perimetro(session)
    sotto_cache: dict[int, Sottocategoria] = {}
    assi_domande = _assi_pro(session)

    non_classificate: list[str] = []
    for v in perimetro:
        if _voce_comune(v) is not None:
            continue
        if not _voce_governata(session, v, assi_domande):
            if v.sottocategoria_id not in sotto_cache:
                sotto_cache[v.sottocategoria_id] = session.get(Sottocategoria, v.sottocategoria_id)
            sotto = sotto_cache[v.sottocategoria_id]
            non_classificate.append(
                f"{v.codice or v.descrizione!r} in {sotto.nome!r} ({sotto.categoria_code})"
            )
    if non_classificate:
        problemi.append(
            "Voci non classificate (ne' governate da un asse ne' in VOCI_COMUNI): "
            + "; ".join(sorted(non_classificate))
        )

    problemi.extend(_verifica_quota_bagno_a6_1(session))
    problemi.extend(_verifica_una_voce_per_gruppo(session, result, risposte, perimetro, sotto_cache))

    return problemi


# --- fixture e test --------------------------------------------------------


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


def test_perimetro_tutte_le_voci_classificate(session):
    result = _compute(session, risposte={})
    probs = violazioni(session, result, {})
    non_classificate = [p for p in probs if p.startswith("Voci non classificate")]
    quota_bagno = [p for p in probs if p.startswith("A.6.1")]
    assert not (non_classificate or quota_bagno), "\n".join(non_classificate + quota_bagno)


def test_una_voce_per_lavorazione(session):
    combinazioni = list(
        product(_opzioni_attive(session, "finitura"), _opzioni_attive(session, "tipo_pavimento"))
    )
    tutte_le_violazioni: list[str] = []
    for finitura, tipo_pavimento in combinazioni:
        risposte = {"finitura": finitura, "tipo_pavimento": tipo_pavimento}
        result = _compute(session, risposte=risposte)
        probs = violazioni(session, result, risposte)
        for p in probs:
            if p.startswith("gruppo "):
                tutte_le_violazioni.append(
                    f"finitura={finitura!r} tipo_pavimento={tipo_pavimento!r}: {p}"
                )
    assert not tutte_le_violazioni, "\n".join(tutte_le_violazioni)


def test_voce_trappola_viene_segnalata(session):
    """Una voce mai vista dalla curatela (non nel foglio assi, non in
    VOCI_COMUNI) deve essere segnalata sia dal controllo A (non classificata)
    sia dal controllo B (seconda voce del gruppo battiscopa A-EDILE), anche
    dopo il fix dei dati del Task 2 — questo test non cambia fra RED e GREEN."""
    a6 = session.query(Sottocategoria).filter_by(categoria_code="A-EDILE", codice=A6_CODICE).one()
    trappola = Voce(
        sottocategoria_id=a6.id,
        codice=None,
        descrizione="Posa in opera di battiscopa in PVC",
        um="ml",
        prezzo_unitario_cliente=Decimal("10.00"),
        ordine=999,
    )
    session.add(trappola)
    session.flush()
    session.add(
        CoefficienteQuantitaVoce(
            voce_id=trappola.id,
            tipo_code="totale",
            coefficiente_qta_per_mq=Decimal("0.9"),
        )
    )
    session.commit()

    result = _compute(session, risposte={})
    probs = violazioni(session, result, {})

    non_classificate = "\n".join(p for p in probs if p.startswith("Voci non classificate"))
    assert "Posa in opera di battiscopa in PVC" in non_classificate, non_classificate

    gruppo_battiscopa = "\n".join(
        p for p in probs if p.startswith("gruppo 'battiscopa' (A-EDILE")
    )
    assert "Posa in opera di battiscopa in PVC" in gruppo_battiscopa, gruppo_battiscopa
