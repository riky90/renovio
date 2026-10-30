"""Casi d'oro: il computo parametrico confrontato con quattro computi reali
(TAR-01, fase 11).

Le fixture in `tests/fixtures/casi_reali/` vengono da `docs/casi-reali/`
(`scripts/estrai_casi_reali.py`); gli input del wizard sono dedotti dalle
quantita' e motivati nella fixture (`deduzioni`). Il confronto e' in
`scripts/confronta_casi_reali.py`, il report in
`.planning/prove/2026-11-taratura/`.

Cosa va dimostrato:

  1. L'EDILE STA NELLA SOGLIA: per ogni caso dentro la soglia lo scarto
     dell'imponibile edile dal reale e' entro +/-15%.
  2. IL TOTALE REALE CADE NEL RANGE mostrato all'utente.
  3. LE REGOLE "DEVE ESSERE PRESENTE" delle note del file: con un bagno
     rifatto entrano rimozione sanitari, linee idriche, impermeabilizzazione,
     montaggio sanitari e box doccia.
  4. LE MIGRAZIONI 0029 E 0030 portano un DB seminato con la bozza
     esattamente ai valori del seed tarato, e tornano indietro.
  4b. LE DOMANDE PRO dei lavori a corpo (bagni nuovi e ciechi, varchi,
     velette, carta da parati, terrazzi) e il clima "solo predisposizione"
     portano le loro voci, e il pannello Pro le mostra.
  5. LE FIXTURE NON PORTANO IL PREZZO IMPRESA (regola di dominio 1).
"""

from __future__ import annotations

import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.db import Base
from app.services.city_resolver import resolve_listino
from scripts.confronta_casi_reali import FIXTURE_DIR, carica_casi, confronta
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

SOGLIA_EDILE_PCT = Decimal("15")
CASI = {c["caso"]: c for c in carica_casi()}


@pytest.fixture(scope="module")
def engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    with sessione_di_test(engine)() as s:
        seed(s, load_seed_data())
    return engine


@pytest.fixture(scope="module")
def confronti(engine):
    with sessione_di_test(engine)() as s:
        listino, _ = resolve_listino(s, "Reggio Emilia")
        return {nome: confronta(s, listino, caso) for nome, caso in CASI.items()}


def test_ci_sono_i_quattro_casi():
    assert sorted(CASI) == ["caso-01", "caso-02", "caso-03", "caso-04"]


# --- 1. soglia sull'edile ------------------------------------------------------


@pytest.mark.parametrize("nome", sorted(CASI))
def test_edile_entro_la_soglia(confronti, nome):
    c = confronti[nome]
    scarto = c.scarto_pct("A-EDILE")
    assert scarto is not None
    if not c.nella_soglia:
        pytest.skip(f"{nome} e' un caso di frontiera: {CASI[nome]['soglia']['motivo']}")
    assert abs(scarto) <= SOGLIA_EDILE_PCT, f"{nome}: edile {scarto:+.1f}%"


# --- 2. totale nel range ------------------------------------------------------------

#: Casi in cui il totale reale cade fuori dal range, con la causa. Sono
#: `xfail(strict=True)`: se una taratura li rimette dentro, il test lo dice e la
#: voce va tolta da qui.
FUORI_RANGE: dict[str, str] = {}


@pytest.mark.parametrize("nome", sorted(CASI))
def test_totale_reale_nel_range(confronti, nome, request):
    if nome in FUORI_RANGE:
        request.applymarker(pytest.mark.xfail(reason=FUORI_RANGE[nome], strict=True))
    c = confronti[nome]
    assert c.nel_range, (
        f"{nome}: reale {c.totale_reale_ivato} fuori da {c.range_min}-{c.range_max}"
    )


# --- 3. regole "deve essere presente" -------------------------------------------


@pytest.mark.parametrize("nome", ["caso-01", "caso-04"])
def test_bagno_rifatto_porta_le_sue_voci(engine, nome):
    from app.services.computo import computo_free

    inp = CASI[nome]["input"]
    with sessione_di_test(engine)() as s:
        listino, _ = resolve_listino(s, "Reggio Emilia")
        computo = computo_free(s, listino, mq=inp["mq"], tipo=inp["tipo"], risposte=inp["risposte"])
    presenti = {v.codice for v in computo.voci}
    for codice in ("A.0.5", "A.0.11", "A.7.1", "A.8.5", "A.10.5"):
        assert codice in presenti, f"{nome}: bagno rifatto senza {codice}"
    assert presenti & {f"A.0.{n}" for n in range(3, 11)}


# --- 4. migrazioni 0029 e 0030 -----------------------------------------------

_MIGRAZIONI = ("0029_taratura_casi_reali", "0030_domande_pro_lavori_a_corpo")


def _migrazione(nome: str):
    percorso = Path(__file__).resolve().parents[1] / "alembic" / "versions" / f"{nome}.py"
    spec = importlib.util.spec_from_file_location(f"migrazione_{nome}", percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _istantanea(conn) -> dict:
    return {
        "termini": sorted(
            (r[0], r[1], str(r[2]), Decimal(str(r[3])).normalize())
            for r in conn.execute(
                text("SELECT grandezza_code, sorgente_code, per_grandezza_code, fattore FROM termine_grandezza")
            )
        ),
        "grandezze": sorted(
            tuple(r) for r in conn.execute(text("SELECT code, nome, descrizione FROM grandezza"))
        ),
        "regole": sorted(
            (r[0], r[1], r[2], Decimal(str(r[3])).normalize(), r[4], r[5])
            for r in conn.execute(
                text(
                    "SELECT voce_codice, tipo_regola, grandezza_code, fattore,"
                    " condizione_grandezza_code, nota FROM regola_voce"
                )
            )
        ),
        "posa_finitura": sorted(
            tuple(r)
            for r in conn.execute(
                text(
                    "SELECT o.code, v.codice FROM effetto_opzione e"
                    " JOIN opzione_domanda o ON o.id = e.opzione_id"
                    " JOIN voce v ON v.id = e.target_voce_id"
                    " WHERE o.domanda_code = 'finitura' AND v.codice LIKE 'A.6.%'"
                )
            )
        ),
    }


def _db_seminato():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    with sessione_di_test(engine)() as s:
        seed(s, load_seed_data())
        s.commit()
    return engine


def _scendi(migrazioni, conn, monkeypatch):
    for m in reversed(migrazioni):
        monkeypatch.setattr(m.op, "get_bind", lambda: conn, raising=False)
        m.downgrade()


def _sali(migrazioni, conn, monkeypatch):
    for m in migrazioni:
        monkeypatch.setattr(m.op, "get_bind", lambda: conn, raising=False)
        m.upgrade()


def test_migrazioni_portano_la_bozza_al_seed_tarato(monkeypatch):
    """Dal seed attuale si scende alla bozza (downgrade 0030 e 0029) e si
    risale: si deve tornare esattamente al seed. Cioe' le migrazioni portano
    un DB seminato con la bozza ai valori del seed tarato, e tornano indietro."""
    migrazioni = [_migrazione(n) for n in _MIGRAZIONI]
    with _db_seminato().begin() as conn:
        tarato = _istantanea(conn)
        _scendi(migrazioni, conn, monkeypatch)
        bozza = _istantanea(conn)
        assert ("mq_pareti", "superficie_calpestabile", "None", Decimal("2.9")) in bozza["termini"]
        assert ("base", "A.6.3") in bozza["posa_finitura"]
        assert bozza != tarato

        _sali(migrazioni, conn, monkeypatch)
        assert _istantanea(conn) == tarato
    assert ("base", "A.6.4") in tarato["posa_finitura"]


def test_migrazioni_non_toccano_una_regola_curata(monkeypatch):
    """Un valore cambiato dal pannello admin resta com'e'."""
    migrazioni = [_migrazione(n) for n in _MIGRAZIONI]
    with _db_seminato().begin() as conn:
        _scendi(migrazioni, conn, monkeypatch)
        conn.execute(text("UPDATE regola_voce SET fattore = 5 WHERE voce_codice = 'A.8.5'"))
        conn.execute(text("UPDATE regola_voce SET fattore = 2 WHERE voce_codice = 'A.3.8'"))
        _sali(migrazioni, conn, monkeypatch)
        curate = dict(
            conn.execute(
                text("SELECT voce_codice, fattore FROM regola_voce WHERE voce_codice IN ('A.8.5', 'A.3.8')")
            ).all()
        )
        tipo_a38 = conn.execute(
            text("SELECT tipo_regola FROM regola_voce WHERE voce_codice = 'A.3.8'")
        ).scalar_one()
    assert Decimal(str(curate["A.8.5"])) == 5
    assert Decimal(str(curate["A.3.8"])) == 2 and tipo_a38 == "fisso"


# --- 4b. domande Pro dei lavori a corpo ------------------------------------------


def test_pannello_pro_mostra_le_domande_dei_lavori_a_corpo(engine):
    from app.services.dettaglio_pro import domande_configuratore

    with sessione_di_test(engine)() as s:
        codici = {d.code for d in domande_configuratore(s, mq=85, risposte={})}
    assert {
        "bagni_nuovi", "bagni_ciechi", "varchi_n", "velette_ml", "carta_parati_mq", "terrazzi_mq",
    } <= codici


@pytest.mark.parametrize(
    "risposte,voce",
    [
        ({"varchi_n": 2}, "A.3.8"),
        ({"velette_ml": 8}, "A.5.3"),
        ({"carta_parati_mq": 30}, "A.1.11.1"),
        ({"terrazzi_mq": 12}, "A.7.2"),
        ({"interv_bagni": "tutti", "bagni": 1, "bagni_ciechi": 1}, "A.10.13"),
    ],
)
def test_risposta_pro_porta_la_sua_voce(engine, risposte, voce):
    from app.services.computo import computo_free

    with sessione_di_test(engine)() as s:
        listino, _ = resolve_listino(s, "Reggio Emilia")
        senza = {v.codice for v in computo_free(s, listino, mq=85, tipo="moderata", risposte={}).voci}
        con = {v.codice for v in computo_free(s, listino, mq=85, tipo="moderata", risposte=risposte).voci}
    assert voce not in senza
    assert voce in con


def test_bagno_nuovo_non_smonta_niente(engine):
    from app.services.computo import computo_free

    base = {"interv_bagni": "tutti", "bagni": 1, "interv_cucina": "no"}
    with sessione_di_test(engine)() as s:
        listino, _ = resolve_listino(s, "Reggio Emilia")
        rifatto = {v.codice for v in computo_free(s, listino, mq=85, tipo="moderata", risposte=base).voci}
        nuovo = {
            v.codice
            for v in computo_free(s, listino, mq=85, tipo="moderata", risposte={**base, "bagni_nuovi": 1}).voci
        }
    smontaggi = {"A.0.5", "A.0.6", "A.0.7", "A.0.11", "A.1.10"}
    assert smontaggi <= rifatto
    assert not (smontaggi & nuovo)
    assert {"A.7.1", "A.8.5", "A.10.5"} <= nuovo


def test_clima_solo_predisposizione(engine):
    from app.services.computo import computo_free

    with sessione_di_test(engine)() as s:
        listino, _ = resolve_listino(s, "Reggio Emilia")
        voci = {
            v.codice: v
            for v in computo_free(
                s, listino, mq=85, tipo="moderata",
                risposte={"interv_clima": "predisposizione", "split_predisposti": 3},
            ).voci
        }
    assert voci["A.8.21"].quantita == 3
    assert "A.10.1" not in voci  # nessun montaggio
    assert not any(c.startswith("D.1.") and c in voci for c in ("D.1.1", "D.1.2", "D.1.3"))


# --- 5. niente prezzo impresa -----------------------------------------------------


def test_fixture_senza_prezzo_impresa():
    for percorso in FIXTURE_DIR.glob("caso-*.json"):
        testo = percorso.read_text(encoding="utf-8").lower()
        for vietata in ("impresa", "guadagno", "coefficiente", "fee"):
            assert vietata not in testo, f"{percorso.name} contiene '{vietata}'"
        for voce in json.loads(testo)["voci"]:
            assert set(voce) <= {
                "foglio", "codice", "riga", "impianto", "descrizione", "um", "quantita",
                "quantita_testo", "prezzo", "totale", "codice_nel_file",
                "descrizione_modificata", "codici_candidati",
            }
