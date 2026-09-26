"""Test di conteggio CFG-02 (09-03-PLAN.md Task 1): il motore Pro non deve
sommare le alternative.

Questo file NON rilegge la logica del motore: conta, a partire dal
CATALOGO (`EffettoOpzione` con `tipo_effetto='includi'`), quali opzioni hanno
almeno una voce-bersaglio presente nel risultato di
`DettaglioProService.compute()`. Se per un asse (una domanda con `includi`)
compaiono voci di PIU' di un'opzione nello stesso computo, e' il bug della
fase: la somma delle alternative.

Deve FALLIRE sul motore prima dello swap (Task 3): il motore attuale non
legge affatto il catalogo Pro, quindi soffre di somma sia in A.6
(A.6.1/.2/.5/.6, mai filtrate da `risposte`) sia in una parte del GRES (la
selezione di `voce.livello` esiste solo per compatibilita', il catalogo con
`tipo_pavimento` non esiste nel motore attuale)."""

from __future__ import annotations

from decimal import Decimal
from itertools import product

import pytest
from sqlalchemy import create_engine

from app.db import Base
from app.models.dettaglio_pro import Sottocategoria, Voce
from app.models.domanda import Domanda, EffettoOpzione, OpzioneDomanda
from app.services.city_resolver import resolve_listino
from app.services.dettaglio_pro import DettaglioProService
from app.services.effetti import TIPO_INCLUDI
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

GRES = "PAVIMENTI E RIVESTIMENTI GRES"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


def _compute(session, **kwargs):
    listino, _ = resolve_listino(session, "Reggio Emilia")
    kwargs.setdefault("risposte", {})
    return DettaglioProService.compute(session, listino, mq=85, tipo="totale", **kwargs)


def _sotto_gres(session) -> Sottocategoria:
    return session.query(Sottocategoria).filter_by(categoria_code="B-FINITURE", nome=GRES).one()


def _sotto_a6(session) -> Sottocategoria:
    return session.query(Sottocategoria).filter_by(categoria_code="A-EDILE", codice="A.6").one()


def _tutte_le_voci_di(session, sotto: Sottocategoria) -> list[Voce]:
    return session.query(Voce).filter_by(sottocategoria_id=sotto.id).order_by(Voce.id).all()


def _identificatore(codice: str | None, descrizione: str) -> tuple[str | None, str]:
    """Chiave stabile di una voce: `codice` quando c'e' (A-EDILE), altrimenti
    la descrizione (B/C/D, senza codice)."""
    return (codice, descrizione)


def _identificatori_presenti(result) -> set[tuple[str | None, str]]:
    return {
        _identificatore(v.codice, v.descrizione)
        for cat in result.categorie
        for sotto in cat.sottocategorie
        for v in sotto.voci
    }


def _voci_di_sottocategoria_effetto(session, effetto: EffettoOpzione) -> list[Voce]:
    if effetto.target_voce_id is not None:
        voce = session.get(Voce, effetto.target_voce_id)
        return [voce] if voce is not None else []
    if effetto.target_sottocategoria_id is not None:
        return (
            session.query(Voce).filter_by(sottocategoria_id=effetto.target_sottocategoria_id).all()
        )
    return []


def _bersagli_per_opzione(session, domanda_code: str) -> dict[str, set[tuple[str | None, str]]]:
    """Dal catalogo: per ogni opzione ATTIVA della domanda, l'insieme delle
    voci-bersaglio dei suoi effetti `includi` (attivi)."""
    righe = (
        session.query(OpzioneDomanda, EffettoOpzione)
        .join(EffettoOpzione, EffettoOpzione.opzione_id == OpzioneDomanda.id)
        .filter(
            OpzioneDomanda.domanda_code == domanda_code,
            OpzioneDomanda.attiva.is_(True),
            EffettoOpzione.attivo.is_(True),
            EffettoOpzione.tipo_effetto == TIPO_INCLUDI,
        )
        .all()
    )
    bersagli: dict[str, set[tuple[str | None, str]]] = {}
    for opzione, effetto in righe:
        voci = _voci_di_sottocategoria_effetto(session, effetto)
        bersagli.setdefault(opzione.code, set()).update(
            _identificatore(v.codice, v.descrizione) for v in voci
        )
    return bersagli


def _domande_con_includi(session) -> list[str]:
    codici = (
        session.query(Domanda.code)
        .join(OpzioneDomanda, OpzioneDomanda.domanda_code == Domanda.code)
        .join(EffettoOpzione, EffettoOpzione.opzione_id == OpzioneDomanda.id)
        .filter(Domanda.attiva.is_(True), EffettoOpzione.tipo_effetto == TIPO_INCLUDI)
        .distinct()
        .all()
    )
    return [c[0] for c in codici]


def _opzioni_con_almeno_una_voce_presente(session, domanda_code: str, result) -> list[str]:
    presenti = _identificatori_presenti(result)
    bersagli = _bersagli_per_opzione(session, domanda_code)
    return [code for code, voci in bersagli.items() if voci & presenti]


def _codici_a6_presenti(result) -> set[str]:
    for cat in result.categorie:
        for sotto in cat.sottocategorie:
            if sotto.codice == "A.6" or sotto.nome == "PAVIMENTI E RIVESTIMENTI":
                return {v.codice for v in sotto.voci if v.codice}
    return set()


# --- comportamento di default e con risposta esplicita (behavior 1/2) -------


def test_default_a6_include_solo_gres(session):
    result = _compute(session)

    presenti = _codici_a6_presenti(result)
    assert "A.6.1" in presenti
    for pose in ("A.6.2", "A.6.5", "A.6.6"):
        assert pose not in presenti


def test_tipo_pavimento_parquet_include_solo_parquet(session):
    result = _compute(session, risposte={"tipo_pavimento": "parquet"})

    presenti = _codici_a6_presenti(result)
    assert "A.6.2" in presenti
    for pose in ("A.6.1", "A.6.5", "A.6.6"):
        assert pose not in presenti


# --- il conteggio vero (behavior 3): al massimo un'opzione per asse --------


FINITURA_OPZIONI = ["base", "medio", "alto"]
TIPO_PAVIMENTO_OPZIONI = ["gres", "parquet", "maxi_lastra", "mosaico"]


@pytest.mark.parametrize("finitura,tipo_pavimento", list(product(FINITURA_OPZIONI, TIPO_PAVIMENTO_OPZIONI)))
def test_nessun_asse_include_piu_di_unopzione(session, finitura, tipo_pavimento):
    result = _compute(
        session, risposte={"finitura": finitura, "tipo_pavimento": tipo_pavimento}
    )

    for domanda_code in _domande_con_includi(session):
        presenti = _opzioni_con_almeno_una_voce_presente(session, domanda_code, result)
        assert len(presenti) <= 1, (
            f"asse {domanda_code!r} con finitura={finitura!r} tipo_pavimento={tipo_pavimento!r}: "
            f"piu' di un'opzione presente nel computo: {presenti}"
        )


@pytest.mark.parametrize("livello", ["base", "medio", "alto"])
def test_nessun_asse_include_piu_di_unopzione_con_livelli(session, livello):
    result = _compute(session, livelli={"B-FINITURE": livello})

    for domanda_code in _domande_con_includi(session):
        presenti = _opzioni_con_almeno_una_voce_presente(session, domanda_code, result)
        assert len(presenti) <= 1


# --- gres con default: bersagli di medio + non governate (behavior 4) ------


def test_gres_default_include_bersagli_di_medio_piu_le_non_governate(session):
    sotto = _sotto_gres(session)
    tutte = _tutte_le_voci_di(session, sotto)
    bersagli = _bersagli_per_opzione(session, "finitura")

    governate = set()
    for voci in bersagli.values():
        governate |= voci
    attese = {
        _identificatore(v.codice, v.descrizione) for v in tutte
    } - governate | bersagli.get("medio", set())

    result = _compute(session)
    presenti_gres = set()
    for cat in result.categorie:
        for s in cat.sottocategorie:
            if s.nome == GRES:
                presenti_gres = {_identificatore(v.codice, v.descrizione) for v in s.voci}

    assert presenti_gres == attese


# --- livelli per categoria (behavior 5) -------------------------------------


def test_livelli_alto_gres_e_livello_scelto_categoria(session):
    bersagli = _bersagli_per_opzione(session, "finitura")

    result = _compute(session, livelli={"B-FINITURE": "alto"})

    presenti_gres = set()
    for cat in result.categorie:
        for s in cat.sottocategorie:
            if s.nome == GRES:
                presenti_gres = {_identificatore(v.codice, v.descrizione) for v in s.voci}

    assert bersagli["alto"] <= presenti_gres
    assert not (bersagli["medio"] & presenti_gres)

    per_code = {c.code: c for c in result.categorie}
    assert per_code["B-FINITURE"].livello_scelto == "alto"
    assert per_code["B-FINITURE"].livello_scelto_nome == "Lusso"


# --- quantita_per_unita di bagni (behavior 6/7) -----------------------------


MISCELATORE_BIDET = (
    "Miscelatore monocomando cromato per bidet, erogazione a doccetta orientabile, "
    "completo di scarico, senza nipples e rosoni"
)


def _voce_miscelatore_bidet(result):
    for cat in result.categorie:
        for sotto in cat.sottocategorie:
            for v in sotto.voci:
                if v.descrizione == MISCELATORE_BIDET:
                    return v
    raise AssertionError("miscelatore per bidet non trovato nel risultato")


def test_bagni_risposta_esplicita_aggiorna_la_quantita(session):
    result = _compute(session, risposte={"bagni": 3})

    voce = _voce_miscelatore_bidet(result)
    assert voce.quantita_stimata == Decimal("3.00")


def test_bagni_senza_risposta_usa_atteso_a_85_mq(session):
    from app.services.effetti import attese_per_mq

    atteso = attese_per_mq(session, 85)["bagni"]

    result = _compute(session)

    voce = _voce_miscelatore_bidet(result)
    assert voce.quantita_stimata == Decimal(atteso).quantize(Decimal("0.01"))


# --- neutralita' strutturale col catalogo Pro svuotato (behavior 8) --------


def test_catalogo_pro_svuotato_nessuna_voce_governata(session):
    session.query(EffettoOpzione).filter(
        EffettoOpzione.opzione_id.in_(
            session.query(OpzioneDomanda.id).filter(
                OpzioneDomanda.domanda_code.in_(["finitura", "tipo_pavimento"])
            )
        )
    ).delete(synchronize_session=False)
    session.query(OpzioneDomanda).filter(
        OpzioneDomanda.domanda_code.in_(["finitura", "tipo_pavimento"])
    ).delete(synchronize_session=False)
    session.query(Domanda).filter(Domanda.code.in_(["finitura", "tipo_pavimento"])).delete(
        synchronize_session=False
    )
    session.commit()

    sotto_gres = _sotto_gres(session)
    tutte_gres = _tutte_le_voci_di(session, sotto_gres)

    result = _compute(session)

    presenti_gres = set()
    for cat in result.categorie:
        for s in cat.sottocategorie:
            if s.nome == GRES:
                presenti_gres = {_identificatore(v.codice, v.descrizione) for v in s.voci}

    assert presenti_gres == {_identificatore(v.codice, v.descrizione) for v in tutte_gres}

    presenti_a6 = _codici_a6_presenti(result)
    for pose in ("A.6.1", "A.6.2", "A.6.5", "A.6.6"):
        assert pose in presenti_a6
