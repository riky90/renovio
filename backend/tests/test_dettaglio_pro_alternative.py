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

import json
from decimal import Decimal
from itertools import product
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.db import Base
from app.models.dettaglio_pro import Sottocategoria, Voce
from app.models.domanda import Domanda, EffettoOpzione, OpzioneDomanda
from app.services.city_resolver import resolve_listino
from app.services.dettaglio_pro import DettaglioProService, SottocategoriaEstimata
from app.services.effetti import TIPO_ESCLUDI, TIPO_FATTORE_QUANTITA, TIPO_INCLUDI
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

FIXTURE_FAMIGLIE = Path(__file__).parent / "fixtures" / "famiglie_alternative_pro.json"

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


def _identificatore(
    sottocategoria_id: int, codice: str | None, descrizione: str
) -> tuple[int, str | None, str]:
    """Chiave stabile di una voce: la sua sottocategoria piu' `codice` (quando
    c'e', A-EDILE) o la descrizione (B/C/D, senza codice). La sottocategoria
    e' necessaria: il listino ha righe con descrizione identica in
    sottocategorie DIVERSE (wrinkle nota, non introdotta da questa fase — vedi
    09-02-SUMMARY.md), quindi `descrizione` sola non e' una chiave univoca."""
    return (sottocategoria_id, codice, descrizione)


def _identificatori_presenti(session, result) -> set[tuple[int, str | None, str]]:
    presenti = set()
    for cat in result.categorie:
        for sotto_result in cat.sottocategorie:
            sotto_id = _id_sottocategoria(session, cat.code, sotto_result)
            for v in sotto_result.voci:
                presenti.add(_identificatore(sotto_id, v.codice, v.descrizione))
    return presenti


def _id_sottocategoria(session, categoria_code: str, sotto_result: SottocategoriaEstimata) -> int:
    query = session.query(Sottocategoria).filter_by(categoria_code=categoria_code)
    if sotto_result.codice is not None:
        query = query.filter_by(codice=sotto_result.codice)
    else:
        query = query.filter_by(nome=sotto_result.nome)
    return query.one().id


def _voci_di_sottocategoria_effetto(session, effetto: EffettoOpzione) -> list[Voce]:
    if effetto.target_voce_id is not None:
        voce = session.get(Voce, effetto.target_voce_id)
        return [voce] if voce is not None else []
    if effetto.target_sottocategoria_id is not None:
        return (
            session.query(Voce).filter_by(sottocategoria_id=effetto.target_sottocategoria_id).all()
        )
    return []


def _bersagli_per_opzione(session, domanda_code: str) -> dict[str, set[tuple[int, str | None, str]]]:
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
    bersagli: dict[str, set[tuple[int, str | None, str]]] = {}
    for opzione, effetto in righe:
        voci = _voci_di_sottocategoria_effetto(session, effetto)
        bersagli.setdefault(opzione.code, set()).update(
            _identificatore(v.sottocategoria_id, v.codice, v.descrizione) for v in voci
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
    presenti = _identificatori_presenti(session, result)
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


def test_tipo_pavimento_parquet_include_parquet_e_la_quota_bagno_gres(session):
    """D-02 (09-07): A.6.1 (la posa gres del bagno) resta presente anche con
    parquet — non e' un'alternativa esclusiva ad A.6.2/.5/.6, e' la quota
    bagno che coesiste sempre con la scelta del resto della casa."""
    result = _compute(session, risposte={"tipo_pavimento": "parquet"})

    presenti = _codici_a6_presenti(result)
    assert "A.6.2" in presenti
    assert "A.6.1" in presenti
    for pose in ("A.6.5", "A.6.6"):
        assert pose not in presenti


# --- il conteggio vero (behavior 3): bersagli condivisi (09-10) ------------
#
# Da 09-09/09-10 due opzioni dello stesso asse possono avere BERSAGLI
# CONDIVISI (es. A.6.2 incluso sia da 'parquet' sia da 'laminato' sia da
# 'vinilico_lvt'), e la deduplica del gres a pavimento lascia sulla voce
# scartata sia il suo `includi` originale SIA un `escludi` che lo annulla
# (l'esclusione vince sempre). Il vecchio conteggio "al massimo un'opzione
# con una voce presente" romperebbe su questi casi legittimi. L'invariante
# corretto e' per-voce: ogni voce presente che e' bersaglio di un `includi`
# dell'asse deve essere bersaglio di un `includi` dell'opzione SCELTA (o del
# default) e non di un suo `escludi`.


def _opzioni_attive(session, domanda_code: str) -> list[str]:
    righe = (
        session.query(OpzioneDomanda.code)
        .filter(OpzioneDomanda.domanda_code == domanda_code, OpzioneDomanda.attiva.is_(True))
        .order_by(OpzioneDomanda.ordine, OpzioneDomanda.id)
        .all()
    )
    return [r[0] for r in righe]


def _opzione_scelta(session, domanda_code: str, risposte: dict) -> OpzioneDomanda | None:
    opzioni = session.query(OpzioneDomanda).filter_by(domanda_code=domanda_code, attiva=True).all()
    per_code = {o.code: o for o in opzioni}
    codice = risposte.get(domanda_code)
    if codice in per_code:
        return per_code[codice]
    return next((o for o in opzioni if o.is_default), None)


def _bersagli_escludi_per_opzione(session, domanda_code: str) -> dict[str, set[tuple[int, str | None, str]]]:
    righe = (
        session.query(OpzioneDomanda, EffettoOpzione)
        .join(EffettoOpzione, EffettoOpzione.opzione_id == OpzioneDomanda.id)
        .filter(
            OpzioneDomanda.domanda_code == domanda_code,
            OpzioneDomanda.attiva.is_(True),
            EffettoOpzione.attivo.is_(True),
            EffettoOpzione.tipo_effetto == TIPO_ESCLUDI,
        )
        .all()
    )
    bersagli: dict[str, set[tuple[int, str | None, str]]] = {}
    for opzione, effetto in righe:
        voci = _voci_di_sottocategoria_effetto(session, effetto)
        bersagli.setdefault(opzione.code, set()).update(
            _identificatore(v.sottocategoria_id, v.codice, v.descrizione) for v in voci
        )
    return bersagli


def _errori_bersagli_condivisi(
    session,
    domanda_code: str,
    presenti: set[tuple[int, str | None, str]],
    opzione_scelta: OpzioneDomanda | None,
) -> list[str]:
    bersagli_includi = _bersagli_per_opzione(session, domanda_code)
    if not bersagli_includi:
        return []
    unione: set[tuple[int, str | None, str]] = set()
    for voci in bersagli_includi.values():
        unione |= voci
    codice_scelto = opzione_scelta.code if opzione_scelta is not None else None
    bersagli_scelta = bersagli_includi.get(codice_scelto, set())
    escludi_scelta = _bersagli_escludi_per_opzione(session, domanda_code).get(codice_scelto, set())

    errori: list[str] = []
    for ident in presenti & unione:
        if ident not in bersagli_scelta:
            errori.append(f"{ident} presente ma non bersaglio di includi dell'opzione scelta {codice_scelto!r}")
        elif ident in escludi_scelta:
            errori.append(f"{ident} presente ma bersaglio di escludi dell'opzione scelta {codice_scelto!r}")
    return errori


@pytest.fixture()
def combinazioni(session):
    return list(product(_opzioni_attive(session, "finitura"), _opzioni_attive(session, "tipo_pavimento")))


def test_nessun_asse_include_piu_di_unopzione(session, combinazioni):
    for finitura, tipo_pavimento in combinazioni:
        risposte = {"finitura": finitura, "tipo_pavimento": tipo_pavimento}
        result = _compute(session, risposte=risposte)
        presenti = _identificatori_presenti(session, result)

        for domanda_code in _domande_con_includi(session):
            opzione_scelta = _opzione_scelta(session, domanda_code, risposte)
            errori = _errori_bersagli_condivisi(session, domanda_code, presenti, opzione_scelta)
            assert not errori, (
                f"asse {domanda_code!r} con finitura={finitura!r} tipo_pavimento={tipo_pavimento!r}: "
                + "; ".join(errori)
            )


def test_nessun_asse_include_piu_di_unopzione_con_livelli(session):
    """`livelli` differenzia il livello di finitura SOLO per le categorie con
    `livello_selezionabile=True` (B-FINITURE): le altre categorie (dove da
    09-07 l'asse finitura governa anche le famiglie di alternative
    sanitari/porte/condizionatori) restano sul default/risposta unica. Il
    controllo va quindi per CATEGORIA, non globalmente su tutto il
    risultato — e' esattamente cio' che rende legittimo differenziare il
    livello per categoria."""
    for livello in _opzioni_attive(session, "finitura"):
        result = _compute(session, livelli={"B-FINITURE": livello})

        for cat in result.categorie:
            presenti_categoria: set[tuple[int, str | None, str]] = set()
            for sotto in cat.sottocategorie:
                sotto_id = _id_sottocategoria(session, cat.code, sotto)
                for v in sotto.voci:
                    presenti_categoria.add(_identificatore(sotto_id, v.codice, v.descrizione))

            for domanda_code in _domande_con_includi(session):
                if domanda_code == "finitura" and cat.code == "B-FINITURE":
                    opzione_scelta = _opzione_scelta(session, domanda_code, {"finitura": livello})
                else:
                    opzione_scelta = _opzione_scelta(session, domanda_code, {})
                errori = _errori_bersagli_condivisi(session, domanda_code, presenti_categoria, opzione_scelta)
                assert not errori, (
                    f"asse {domanda_code!r} categoria {cat.code!r} livello={livello!r}: "
                    + "; ".join(errori)
                )


def _bersagli_finitura_in_sottocategoria(session, sotto_id: int) -> dict[str, set[tuple[int, str | None, str]]]:
    """Da 09-07 l'asse `finitura` governa anche voci FUORI da GRES (le
    famiglie di alternative sanitari/porte/condizionatori): questi due test
    (scritti per il mondo 09-02/09-03, dove finitura governava solo GRES)
    restano validi filtrando i bersagli alla sola sottocategoria in esame."""
    bersagli = _bersagli_per_opzione(session, "finitura")
    return {
        code: {ident for ident in voci if ident[0] == sotto_id} for code, voci in bersagli.items()
    }


def _escludi_finitura_in_sottocategoria(session, sotto_id: int) -> dict[str, set[tuple[int, str | None, str]]]:
    """Come `_bersagli_finitura_in_sottocategoria` ma per gli `escludi`: dal
    09-10 la deduplica del gres a pavimento lascia un `escludi` sulle voci
    scartate, che vince sempre sull'`includi` gemello (09-03)."""
    escludi = _bersagli_escludi_per_opzione(session, "finitura")
    return {
        code: {ident for ident in voci if ident[0] == sotto_id} for code, voci in escludi.items()
    }


# --- gres con default: bersagli di medio + non governate (behavior 4) ------


def test_gres_default_include_bersagli_di_medio_piu_le_non_governate(session):
    sotto = _sotto_gres(session)
    tutte = _tutte_le_voci_di(session, sotto)
    bersagli = _bersagli_finitura_in_sottocategoria(session, sotto.id)
    escludi = _escludi_finitura_in_sottocategoria(session, sotto.id)

    governate = set()
    for voci in bersagli.values():
        governate |= voci
    # Dal 09-10 i "bersagli" vivi di un'opzione sono i suoi includi MENO i
    # suoi escludi: la deduplica del gres a pavimento (una sola fornitura per
    # livello) lascia un includi+escludi sulle voci scartate, e l'escludi
    # vince sempre (09-03).
    bersagli_medio_vivi = bersagli.get("medio", set()) - escludi.get("medio", set())
    attese = (
        {_identificatore(sotto.id, v.codice, v.descrizione) for v in tutte} - governate
    ) | bersagli_medio_vivi

    result = _compute(session)
    presenti_gres = set()
    for cat in result.categorie:
        for s in cat.sottocategorie:
            if s.nome == GRES:
                presenti_gres = {_identificatore(sotto.id, v.codice, v.descrizione) for v in s.voci}

    assert presenti_gres == attese


# --- livelli per categoria (behavior 5) -------------------------------------


def test_livelli_alto_gres_e_livello_scelto_categoria(session):
    sotto = _sotto_gres(session)
    bersagli = _bersagli_finitura_in_sottocategoria(session, sotto.id)
    escludi = _escludi_finitura_in_sottocategoria(session, sotto.id)

    result = _compute(session, livelli={"B-FINITURE": "alto"})

    presenti_gres = set()
    for cat in result.categorie:
        for s in cat.sottocategorie:
            if s.nome == GRES:
                presenti_gres = {_identificatore(sotto.id, v.codice, v.descrizione) for v in s.voci}

    bersagli_alto_vivi = bersagli["alto"] - escludi.get("alto", set())
    bersagli_medio_vivi = bersagli["medio"] - escludi.get("medio", set())
    assert bersagli_alto_vivi <= presenti_gres
    assert not (bersagli_medio_vivi & presenti_gres)

    per_code = {c.code: c for c in result.categorie}
    assert per_code["B-FINITURE"].livello_scelto == "alto"
    assert per_code["B-FINITURE"].livello_scelto_nome == "Lusso"


# --- nuove opzioni pavimento (09-10, G1) ------------------------------------


def test_moquette_non_riduce_a6_1(session):
    """Moquette e' esclusa da OPZIONI_CON_QUOTA_BAGNO_A6_1 (09-09): non ha una
    posa dedicata nel computo, resta sulla posa generica A.6.1 a quantita'
    piena, come il gres di default."""
    result_gres = _compute(session, risposte={"tipo_pavimento": "gres"})
    result_moquette = _compute(session, risposte={"tipo_pavimento": "moquette"})

    def _quantita_a6_1(result):
        for cat in result.categorie:
            for sotto in cat.sottocategorie:
                if sotto.codice == "A.6":
                    for v in sotto.voci:
                        if v.codice == "A.6.1":
                            return v.quantita_stimata
        raise AssertionError("A.6.1 non presente")

    assert _quantita_a6_1(result_moquette) == _quantita_a6_1(result_gres)


def test_laminato_include_sottofondo_e_esclude_parquet(session):
    """Con laminato: la fornitura laminato, il sottofondo Unilin (bersaglio
    condiviso della stessa opzione, D-08), la posa A.6.2 e il battiscopa
    A.6.7 sono presenti; nessuna voce di PAVIMENTI PARQUET, la levigatura
    A.6.10, il vinilico LVT o la moquette."""
    result = _compute(session, risposte={"tipo_pavimento": "laminato"})
    codici_a6 = _codici_a6_presenti(result)

    presenti_pavimenti = set()
    presenti_parquet_sotto = set()
    for cat in result.categorie:
        for sotto in cat.sottocategorie:
            if sotto.nome == "PAVIMENTI":
                presenti_pavimenti |= {v.descrizione for v in sotto.voci}
            elif sotto.nome == "PAVIMENTI PARQUET":
                presenti_parquet_sotto |= {v.descrizione for v in sotto.voci}

    assert any("laminato" in d.lower() for d in presenti_pavimenti)
    assert any("sottofondo" in d.lower() for d in presenti_pavimenti)
    assert "A.6.2" in codici_a6
    assert "A.6.7" in codici_a6

    # nessuna voce di PAVIMENTI PARQUET (sottocategoria intera), nessun
    # vinilico LVT / moquette nella sottocategoria PAVIMENTI, nessuna
    # levigatura parquet A.6.10.
    assert presenti_parquet_sotto == set()
    assert not any("vinilico" in d.lower() for d in presenti_pavimenti)
    assert not any("moquette" in d.lower() for d in presenti_pavimenti)
    assert "A.6.10" not in codici_a6


# --- quantita_per_unita di bagni (behavior 6/7) -----------------------------


MISCELATORE_BIDET = (
    "Miscelatore monocomando cromato per bidet, erogazione a doccetta orientabile, "
    "completo di scarico, senza nipples e rosoni"
)

# Da 09-07 MISCELATORE_BIDET e' bersaglio dell'asse `finitura` (la famiglia
# 'sanitari_bidet' del file di taratura, per il match della parola-chiave
# 'bidet' sulla sua descrizione) — e la bozza attuale lo assegna a NESSUno
# dei tre livelli (eccedenza, escludi_sempre), un difetto di classificazione
# della bozza 09-01 (il match "bidet" cattura anche l'accessorio, non solo
# l'apparecchio) che non e' nello scope di questo piano correggere (Excel di
# decisioni). Le due prove sulla quantita' `bagni` (behavior 6/7 del piano)
# usano quindi un'altra voce con lo stesso effetto quantita_per_unita
# ('stepper_bagni') ma NON toccata da alcuna famiglia finitura, cosi' il
# comportamento verificato resta quello del layer quantita', non l'esito
# della curatela degli assi (che CFG-02 verifica altrove in questo file).
MISCELATORE_DOCCIA_VASCA = (
    "Miscelatore cromato monocomando da incasso per doccia/vasca: con corpo incassato, "
    "maniglia, cappuccio, rosone, doccia a sistema anticalcare, flessibile da 1500 mm e "
    "appendidoccia orientabile."
)


def _voce_per_descrizione(result, descrizione: str):
    for cat in result.categorie:
        for sotto in cat.sottocategorie:
            for v in sotto.voci:
                if v.descrizione == descrizione:
                    return v
    raise AssertionError(f"voce non trovata nel risultato: {descrizione[:60]!r}")


def test_bagni_risposta_esplicita_aggiorna_la_quantita(session):
    result = _compute(session, risposte={"bagni": 3})

    voce = _voce_per_descrizione(result, MISCELATORE_DOCCIA_VASCA)
    assert voce.quantita_stimata == Decimal("3.00")


def test_bagni_senza_risposta_usa_atteso_a_85_mq(session):
    from app.services.effetti import attese_per_mq

    atteso = attese_per_mq(session, 85)["bagni"]

    result = _compute(session)

    voce = _voce_per_descrizione(result, MISCELATORE_DOCCIA_VASCA)
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
                presenti_gres = {
                    _identificatore(sotto_gres.id, v.codice, v.descrizione) for v in s.voci
                }

    assert presenti_gres == {
        _identificatore(sotto_gres.id, v.codice, v.descrizione) for v in tutte_gres
    }

    presenti_a6 = _codici_a6_presenti(result)
    for pose in ("A.6.1", "A.6.2", "A.6.5", "A.6.6"):
        assert pose in presenti_a6


# --- CFG-02 per famiglia, su TUTTE le sottocategorie catalogo (09-07 Task 2) ---
#
# La fixture `famiglie_alternative_pro.json` (09-07 Task 1, applica_taratura.py)
# elenca, per ogni voce con un asse approvato nel file di taratura, la sua
# famiglia di alternative. Non ogni riga della fixture e' un'alternativa a
# scelta singola nel senso di CFG-02:
#   - 'comune' = voci sempre_inclusa, non governate da alcun asse: PIU' voci
#     della stessa sottocategoria coesistono per costruzione, non sono
#     alternative fra loro.
#   - 'stepper_*' (bagni/porte/condizionatori) = quantita' per unita', non
#     un asse a scelta singola: piu' voci con la stessa chiave coesistono.
#   - 'finitura:<sottocategoria>' = varieta' di SKU migrata da voce.livello
#     (09-02/09-03/09-04): un livello (es. 'medio') include DELIBERATAMENTE
#     piu' prodotti gres, verificato da test_gres_default_include_bersagli_di
#     _medio_piu_le_non_governate qui sopra — non e' un difetto di curatela.
# Le famiglie CHE RESTANO (sanitari_*, porte_apertura, condizionatori_marca,
# posa_pavimento_A6[:bagno], fornitura_pavimento_*, battiscopa) sono le vere
# alternative a scelta singola: al massimo una voce per famiglia in ogni
# computo, per costruzione di applica_assi() (Task 1, deduplica compresa).


def _famiglia_e_alternativa_a_scelta_singola(famiglia: str) -> bool:
    return famiglia != "comune" and not famiglia.startswith("stepper_") and not famiglia.startswith("finitura:")


@pytest.fixture(scope="module")
def famiglie_fixture() -> list[dict]:
    return json.loads(FIXTURE_FAMIGLIE.read_text(encoding="utf-8"))


def _risolvi_voce_naturale(session, listino_id: int, entry: dict) -> Voce | None:
    """Stessa regola di chiave naturale del seed (09-02)/applica_taratura
    (09-07): codice se esiste, altrimenti nome/descrizione esatta."""
    query_sotto = session.query(Sottocategoria).filter_by(
        listino_id=listino_id, categoria_code=entry["categoria_code"]
    )
    sotto = query_sotto.filter_by(codice=entry["sottocategoria"]).one_or_none()
    if sotto is None:
        sotto = query_sotto.filter_by(codice=None, nome=entry["sottocategoria"]).one_or_none()
    if sotto is None:
        return None
    query_voce = session.query(Voce).filter_by(sottocategoria_id=sotto.id)
    voce = query_voce.filter_by(codice=entry["voce"]).one_or_none()
    if voce is None:
        voce = query_voce.filter_by(codice=None, descrizione=entry["voce"]).one_or_none()
    return voce


class TestFamiglieAlternative:
    """CFG-02 per famiglia, su tutte le sottocategorie catalogo (non solo GRES
    e A.6): al massimo una voce per famiglia di alternative in ogni computo,
    per tutte le 12 combinazioni finitura x tipo_pavimento.

    Il gruppo e' per FAMIGLIA (non per sottocategoria+famiglia): la stessa
    famiglia puo' avere membri in sottocategorie diverse (es.
    'condizionatori_marca' assegna un tier anche a una voce di rimozione in
    A.0, per il match troppo ampio della parola-chiave 'condizionatore' sul
    computo) — resta comunque UNA scelta esclusiva, governata dallo stesso
    asse `finitura`, quindi lo stesso invariante <=1 vale sull'unione, non
    sottocategoria per sottocategoria."""

    @pytest.fixture()
    def gruppi(self, session, famiglie_fixture):
        """famiglia -> insieme degli identificatori delle sue voci, risolte
        sul DB di test seminato. Le famiglie non risolte (voce sparita dalla
        fixture rispetto al DB di test) sono saltate, non un errore: la
        fixture e' generata su dev.db, non sul DB in-memory."""
        listino, _ = resolve_listino(session, "Reggio Emilia")
        gruppi: dict[str, set[tuple[int, str | None, str]]] = {}
        for entry in famiglie_fixture:
            voce = _risolvi_voce_naturale(session, listino.id, entry)
            if voce is None:
                continue
            gruppi.setdefault(entry["famiglia"], set()).add(
                _identificatore(voce.sottocategoria_id, voce.codice, voce.descrizione)
            )
        return gruppi

    @pytest.fixture()
    def combinazioni(self, session):
        return list(product(_opzioni_attive(session, "finitura"), _opzioni_attive(session, "tipo_pavimento")))

    @pytest.fixture()
    def risultati_per_combinazione(self, session, combinazioni):
        """Un solo `_compute` per combinazione, riusato da tutti i test della
        classe invece di ricalcolare per ogni famiglia (09-10 Task 3)."""
        return {
            (finitura, tipo_pavimento): _compute(
                session, risposte={"finitura": finitura, "tipo_pavimento": tipo_pavimento}
            )
            for finitura, tipo_pavimento in combinazioni
        }

    def test_al_massimo_una_voce_per_famiglia(self, session, gruppi, risultati_per_combinazione):
        for (finitura, tipo_pavimento), result in risultati_per_combinazione.items():
            presenti = _identificatori_presenti(session, result)

            for famiglia, voci_famiglia in gruppi.items():
                if not _famiglia_e_alternativa_a_scelta_singola(famiglia):
                    continue
                incluse = voci_famiglia & presenti
                assert len(incluse) <= 1, (
                    f"famiglia={famiglia!r} con finitura={finitura!r} "
                    f"tipo_pavimento={tipo_pavimento!r}: piu' di una voce presente: {incluse}"
                )

    def test_ogni_famiglia_ha_almeno_una_combinazione_con_una_voce_inclusa(
        self, session, gruppi, risultati_per_combinazione
    ):
        mai_vista: list[str] = []
        for chiave_gruppo, voci_famiglia in gruppi.items():
            trovata = any(
                voci_famiglia & _identificatori_presenti(session, result)
                for result in risultati_per_combinazione.values()
            )
            if not trovata:
                mai_vista.append(chiave_gruppo)
        assert mai_vista == []

    def test_parquet_a6_1_presente_a_quota_bagno_e_voci_bagno_restano(self, session):
        sotto_a6 = _sotto_a6(session)
        a6_1 = session.query(Voce).filter_by(sottocategoria_id=sotto_a6.id, codice="A.6.1").one()
        coeff = (
            session.query(EffettoOpzione)
            .join(OpzioneDomanda, EffettoOpzione.opzione_id == OpzioneDomanda.id)
            .filter(
                OpzioneDomanda.domanda_code == "tipo_pavimento",
                OpzioneDomanda.code == "parquet",
                EffettoOpzione.tipo_effetto == TIPO_FATTORE_QUANTITA,
                EffettoOpzione.target_voce_id == a6_1.id,
            )
            .one()
        )
        fattore = coeff.valore

        result_gres = _compute(session, risposte={"tipo_pavimento": "gres"})
        result_parquet = _compute(session, risposte={"tipo_pavimento": "parquet"})

        def _quantita_a6_1(result) -> Decimal:
            for cat in result.categorie:
                for sotto in cat.sottocategorie:
                    if sotto.codice == "A.6":
                        for v in sotto.voci:
                            if v.codice == "A.6.1":
                                return v.quantita_stimata
            raise AssertionError("A.6.1 non presente")

        quantita_gres = _quantita_a6_1(result_gres)
        quantita_parquet = _quantita_a6_1(result_parquet)
        attesa = (quantita_gres * fattore).quantize(Decimal("0.01"))
        assert quantita_parquet == attesa

        # le voci del bagno (rivestimenti, non governate da tipo_pavimento)
        # restano presenti anche con parquet.
        sotto_gres = _sotto_gres(session)
        presenti_gres = set()
        for cat in result_parquet.categorie:
            for s in cat.sottocategorie:
                if s.nome == GRES:
                    presenti_gres = {v.codice or v.descrizione for v in s.voci}
        assert presenti_gres, "il bagno (rivestimento gres) deve restare presente con parquet"

    def test_voci_escluse_sempre_non_compaiono_in_nessuna_combinazione(self, session, combinazioni):
        escluse_ids = {
            row[0]
            for row in session.query(EffettoOpzione.target_voce_id)
            .join(OpzioneDomanda, EffettoOpzione.opzione_id == OpzioneDomanda.id)
            .filter(
                OpzioneDomanda.domanda_code == "finitura",
                EffettoOpzione.tipo_effetto == TIPO_ESCLUDI,
                EffettoOpzione.target_voce_id.isnot(None),
            )
            .distinct()
            .all()
        }
        if not escluse_ids:
            pytest.skip("nessuna voce escludi_sempre nella bozza corrente")

        escluse_identificatori = set()
        for voce_id in escluse_ids:
            voce = session.get(Voce, voce_id)
            if voce is not None:
                escluse_identificatori.add(
                    _identificatore(voce.sottocategoria_id, voce.codice, voce.descrizione)
                )

        for finitura, tipo_pavimento in combinazioni:
            result = _compute(session, risposte={"finitura": finitura, "tipo_pavimento": tipo_pavimento})
            presenti = _identificatori_presenti(session, result)
            assert not (escluse_identificatori & presenti), (
                f"voce escludi_sempre presente con finitura={finitura!r} "
                f"tipo_pavimento={tipo_pavimento!r}"
            )
