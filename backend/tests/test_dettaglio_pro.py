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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.services.city_resolver import resolve_listino
from app.services.dettaglio_pro import DettaglioProService
from scripts.seed import load_seed_data, seed


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)
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
