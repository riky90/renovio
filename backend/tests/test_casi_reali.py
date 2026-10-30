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
  4. LA MIGRAZIONE 0029 porta un DB seminato con la bozza esattamente ai
     valori del seed tarato, e torna indietro.
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


# --- 4. migrazione 0029 ----------------------------------------------------------


def _migrazione_0029():
    percorso = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0029_taratura_casi_reali.py"
    spec = importlib.util.spec_from_file_location("migrazione_0029", percorso)
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
    }


def test_migrazione_0029_porta_la_bozza_al_seed_tarato(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    with sessione_di_test(engine)() as s:
        seed(s, load_seed_data())
        s.commit()
    migrazione = _migrazione_0029()
    with engine.begin() as conn:
        tarato = _istantanea(conn)
        monkeypatch.setattr(migrazione.op, "get_bind", lambda: conn, raising=False)

        migrazione.downgrade()
        bozza = _istantanea(conn)
        assert ("mq_pareti", "superficie_calpestabile", "None", Decimal("2.9")) in bozza["termini"]
        assert bozza != tarato

        migrazione.upgrade()
        assert _istantanea(conn) == tarato


def test_migrazione_0029_non_tocca_una_regola_curata(monkeypatch):
    """Un valore cambiato dal pannello admin resta com'e'."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    with sessione_di_test(engine)() as s:
        seed(s, load_seed_data())
        s.commit()
    migrazione = _migrazione_0029()
    with engine.begin() as conn:
        monkeypatch.setattr(migrazione.op, "get_bind", lambda: conn, raising=False)
        migrazione.downgrade()
        conn.execute(text("UPDATE regola_voce SET fattore = 5 WHERE voce_codice = 'A.8.5'"))
        migrazione.upgrade()
        fattore = conn.execute(
            text("SELECT fattore FROM regola_voce WHERE voce_codice = 'A.8.5'")
        ).scalar_one()
    assert Decimal(str(fattore)) == 5


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
