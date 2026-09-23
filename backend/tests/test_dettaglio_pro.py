"""DettaglioProService regression tests (03-03-PLAN.md Task 1/2).

Oracolo per-voce pinnato a mano dal seed reale (docs/seed-dettaglio-pro.json):
- A.1.1.1 (A-EDILE, um=mq, prezzo_unitario_cliente=45.00, coefficiente_qta_per_mq
  tipo=totale=0.6): mq=85 -> quantita=51.00, totale_voce=2295.00,
  range_pct(totale)=0.20 -> [1836, 2754].
- A.0.3 (A-EDILE, um=cad, prezzo_unitario_cliente=40.00, tipo=totale,
  domanda_mirata_key="bagni", default_conteggio=1): senza risposte ->
  quantita=1 -> [32, 48]; con risposte={"bagni": 3} -> quantita=3 -> [96, 144].
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.services.city_resolver import resolve_listino
from app.services.dettaglio_pro import DettaglioProService
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


def _find_voce(result, codice: str):
    for cat in result.categorie:
        for sotto in cat.sottocategorie:
            for voce in sotto.voci:
                if voce.codice == codice:
                    return voce
    raise AssertionError(f"voce {codice!r} non trovata nel risultato")


def test_oracolo_per_voce_coefficiente_qta_per_mq(session):
    listino, fallback = resolve_listino(session, "Reggio Emilia")
    assert fallback is False

    result = DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={})

    voce = _find_voce(result, "A.1.1.1")
    assert voce.quantita_stimata == Decimal("51.00")
    assert voce.prezzo_min == Decimal("1836")
    assert voce.prezzo_max == Decimal("2754")


def test_domanda_mirata_usa_default_conteggio_se_risposta_assente(session):
    listino, _ = resolve_listino(session, "Reggio Emilia")

    result = DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={})

    voce = _find_voce(result, "A.0.3")
    assert voce.quantita_stimata == Decimal("1.00")
    assert voce.prezzo_min == Decimal("32")
    assert voce.prezzo_max == Decimal("48")


def test_domanda_mirata_usa_risposta_esplicita_quando_presente(session):
    listino, _ = resolve_listino(session, "Reggio Emilia")

    result = DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={"bagni": 3})

    voce = _find_voce(result, "A.0.3")
    assert voce.quantita_stimata == Decimal("3.00")
    assert voce.prezzo_min == Decimal("96")
    assert voce.prezzo_max == Decimal("144")


def test_sottocategoria_senza_voci_stimate_compare_comunque(session):
    """Ogni Sottocategoria della categoria e' presente nel risultato, anche
    se (in teoria) non avesse voci — qui verifichiamo che tutte le
    sottocategorie seedate per A-EDILE compaiano, mai filtrate."""
    listino, _ = resolve_listino(session, "Reggio Emilia")

    result = DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={})

    edile = next(c for c in result.categorie if c.code == "A-EDILE")
    assert len(edile.sottocategorie) > 0
    for sotto in edile.sottocategorie:
        assert isinstance(sotto.voci, list)


def test_totali_a_range_sommano_bottom_up(session):
    """I totali (D-11, sempre a range) sono somme coerenti bottom-up:
    subtotale sottocategoria = somma voci; totale categoria = somma
    sottocategorie; totale generale = somma categorie. Fonte unica per
    schermata e PDF (03-RESEARCH.md Pitfall 2)."""
    listino, _ = resolve_listino(session, "Reggio Emilia")

    result = DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={})

    grand_min = Decimal("0")
    grand_max = Decimal("0")
    for cat in result.categorie:
        cat_min = Decimal("0")
        cat_max = Decimal("0")
        for sotto in cat.sottocategorie:
            assert sotto.totale_min == sum((v.prezzo_min for v in sotto.voci), Decimal("0"))
            assert sotto.totale_max == sum((v.prezzo_max for v in sotto.voci), Decimal("0"))
            cat_min += sotto.totale_min
            cat_max += sotto.totale_max
        assert cat.totale_min == cat_min
        assert cat.totale_max == cat_max
        grand_min += cat_min
        grand_max += cat_max

    assert result.totale_min == grand_min
    assert result.totale_max == grand_max
    # Un range reale: il minimo non supera il massimo, ed esiste un costo > 0.
    assert result.totale_min <= result.totale_max
    assert result.totale_max > Decimal("0")


def test_service_non_importa_il_motore_free():
    """D-01: guard statico — il sorgente non deve nominare la classe del
    motore di stima Free."""
    import inspect

    from app.services import dettaglio_pro as modulo

    sorgente = inspect.getsource(modulo)
    assert "EstimationService" not in sorgente


def test_nessun_campo_impresa_nel_risultato(session):
    listino, _ = resolve_listino(session, "Reggio Emilia")

    result = DettaglioProService.compute(session, listino, mq=85, tipo="totale", risposte={})

    result_repr = repr(result)
    assert "coefficiente_impresa" not in result_repr
    assert "prezzo_impresa" not in result_repr
    assert "base_eur_mq" not in result_repr


STIME_URL = "/api/v1/me/stime"
ATTIVA_PRO_URL = "/api/v1/me/pro/attiva"
REGISTRAZIONE_URL = "/api/v1/auth/registrati"


def _stima_payload() -> dict:
    return {
        "input": {"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"},
        "fallback": False,
        "disclaimer": None,
        "valuta": "EUR",
        "categorie": [],
        "extra": [],
        "totale": {
            "imponibile_min": "10000.00",
            "imponibile_max": "15000.00",
            "iva_min": "1000.00",
            "iva_max": "1500.00",
            "totale_min": "11000.00",
            "totale_max": "16500.00",
        },
    }


@pytest.fixture()
def http_client(monkeypatch, tmp_path):
    """Client HTTP end-to-end per l'integrazione POST-risposte -> GET
    (Task 2): stesso pattern engine-swap di test_dettaglio_pro_paywall.py."""
    limiter.reset()

    db_path = tmp_path / "test_dettaglio_pro_integration.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module
    import app.routers.dettaglio_pro as dettaglio_pro_router_module
    import app.routers.stime_salvate as stime_salvate_router_module
    import app.routers.subscription as subscription_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(dettaglio_pro_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(stime_salvate_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(subscription_router_module, "SessionLocal", testing_session_local)

    return TestClient(app)


def test_post_risposte_persiste_e_get_successivo_le_riflette(http_client):
    http_client.post(REGISTRAZIONE_URL, json={"email": "pro.int@example.com", "password": "Password123", "nome": "Pro"})
    http_client.post(ATTIVA_PRO_URL)
    created = http_client.post(STIME_URL, json=_stima_payload())
    stima_id = created.json()["id"]

    post_response = http_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"bagni": 3, "porte": 5, "condizionatori": 2},
    )
    assert post_response.status_code == 200
    assert post_response.json()["risposte"] == {"bagni": 3, "porte": 5, "condizionatori": 2}

    get_response = http_client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["risposte"] == {"bagni": 3, "porte": 5, "condizionatori": 2}

    edile = next(c for c in body["categorie"] if c["code"] == "A-EDILE")
    voce_bagni = next(
        v
        for sotto in edile["sottocategorie"]
        for v in sotto["voci"]
        if v["codice"] == "A.0.3"
    )
    assert Decimal(voce_bagni["quantita_stimata"]) == Decimal("3.00")


def test_risposte_salvate_distingue_zero_zero_zero_da_nessuna_risposta(http_client):
    """`{0, 0, 0}` e' una risposta legittima — "non ho bagni da rifare" — e non
    deve essere indistinguibile dal non aver mai risposto.

    Senza questo flag il client deduce lo stato dalla somma delle risposte e
    riapre il pannello domande addosso a chi ha appena risposto zero."""
    http_client.post(
        REGISTRAZIONE_URL,
        json={"email": "zero.pro@example.com", "password": "Password123", "nome": "Zero"},
    )
    http_client.post(ATTIVA_PRO_URL)
    stima_id = http_client.post(STIME_URL, json=_stima_payload()).json()["id"]

    prima = http_client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro").json()
    assert prima["risposte_salvate"] is False

    post_response = http_client.post(
        f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
        json={"bagni": 0, "porte": 0, "condizionatori": 0},
    )
    assert post_response.json()["risposte_salvate"] is True

    dopo = http_client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro").json()
    assert dopo["risposte_salvate"] is True
    assert dopo["risposte"] == {"bagni": 0, "porte": 0, "condizionatori": 0}
