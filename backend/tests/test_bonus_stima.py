"""Gap G5: `bonus_out_per_stima` — detrazione sui lavori e costo netto a range."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.bonus import BonusFiscale
from app.schemas.stima import BonusOut
from app.services.arredo import ArredoService
from app.services.bonus_stima import bonus_out_per_stima
from app.services.city_resolver import resolve_listino
from app.services.estimation import EstimationService
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

STIMA_URL = "/api/v1/stima"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


def _stima(session):
    listino, _ = resolve_listino(session, "Reggio Emilia")
    return EstimationService.compute(session, listino, mq=85, tipo="totale", risposte=None)


def _out(session, arredo=None):
    r = _stima(session)
    return r, bonus_out_per_stima(
        session,
        categorie_lorde=r.categorie,
        extra_lordi=r.extra,
        arredo=arredo,
        destinazione="prima_casa",
        totale_min=r.totale_min,
        totale_max=r.totale_max,
    )


def _arredo_acceso(session):
    session.get(BonusFiscale, "MOBILI").attivo = True
    session.flush()
    a = ArredoService.compute(session, {"ambienti_arredo": ["cucina", "bagno"]})
    return (a.totale_min, a.totale_max)


class TestNetto:
    def test_senza_arredo_lavori_uguale_detrazione(self, session):
        r, out = _out(session)
        assert out is not None
        assert out.detrazione_lavori_min == out.detrazione_min
        assert out.detrazione_lavori_max == out.detrazione_max
        assert out.netto_min == r.totale_min - out.detrazione_min
        assert out.netto_max == r.totale_max - out.detrazione_max
        assert 0 <= out.netto_min <= out.netto_max

    def test_con_arredo_il_netto_esclude_la_detrazione_mobili(self, session):
        r, out = _out(session, arredo=_arredo_acceso(session))
        assert out.detrazione_lavori_min < out.detrazione_min
        assert out.detrazione_lavori_max < out.detrazione_max
        assert out.netto_min == r.totale_min - out.detrazione_lavori_min
        assert out.netto_max == r.totale_max - out.detrazione_lavori_max

    def test_solo_bonus_arredo_attivo_netto_uguale_totale(self, session):
        for b in session.query(BonusFiscale).all():
            b.attivo = b.code == "MOBILI"
        session.flush()
        a = ArredoService.compute(session, {"ambienti_arredo": ["cucina"]})
        r, out = _out(session, arredo=(a.totale_min, a.totale_max))
        assert out is not None
        assert out.detrazione_lavori_min == 0 and out.detrazione_lavori_max == 0
        assert out.netto_min == r.totale_min
        assert out.netto_max == r.totale_max

    def test_netto_mai_negativo(self, session):
        r = _stima(session)
        out = bonus_out_per_stima(
            session,
            categorie_lorde=r.categorie,
            extra_lordi=r.extra,
            arredo=None,
            destinazione="prima_casa",
            totale_min=Decimal("100"),
            totale_max=Decimal("200"),
        )
        assert out.netto_min == 0 and out.netto_max == 0

    def test_nessun_bonus_attivo_torna_none(self, session):
        for b in session.query(BonusFiscale).all():
            b.attivo = False
        session.flush()
        _, out = _out(session)
        assert out is None


def test_snapshot_senza_campi_nuovi_si_valida():
    out = BonusOut.model_validate(
        {
            "bonus": [],
            "detrazione_min": "1",
            "detrazione_max": "2",
            "rata_annua_min": "1",
            "rata_annua_max": "2",
            "disclaimer": "d",
        }
    )
    assert out.netto_min is None and out.detrazione_lavori_max is None


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test_bonus_stima.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.get(BonusFiscale, "MOBILI").attivo = True
        s.commit()
    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)
    import app.routers.stima as stima_router_module

    monkeypatch.setattr(stima_router_module, "SessionLocal", testing_session_local)
    with TestClient(app) as c:
        yield c


def test_post_stima_con_arredo_espone_netto(client):
    r = client.post(
        STIMA_URL,
        json={
            "citta": "Reggio Emilia",
            "mq": 85,
            "tipo": "totale",
            "risposte": {"ambienti_arredo": ["cucina", "bagno"]},
        },
    )
    assert r.status_code == 200
    bonus = r.json()["bonus"]
    for chiave in ("detrazione_lavori_min", "detrazione_lavori_max", "netto_min", "netto_max"):
        assert bonus[chiave] is not None
    assert Decimal(bonus["detrazione_lavori_max"]) < Decimal(bonus["detrazione_max"])
    assert Decimal(bonus["netto_max"]) == Decimal("70575") - Decimal(bonus["detrazione_lavori_max"])
