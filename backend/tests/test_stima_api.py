"""POST /api/v1/stima — API contract regression tests (01-03-PLAN.md).

Uses the real seeded DB (dev.db via app.main's SessionLocal is NOT used here;
these tests exercise the live app against whatever DB `DATABASE_URL` points
to in the test environment — the project's dev DB, migrated + seeded, per
the existing test_health.py / TestClient pattern). To keep these tests
self-contained and independent of dev.db state, we seed an isolated SQLite
file DB and point the app's SessionLocal at it for the duration of the
module.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.db import Base
from app.main import app
from scripts.seed import load_seed_data, seed


@pytest.fixture(autouse=True, scope="module")
def _seeded_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test_stima_api.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()

    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = testing_session_local
    # The router module imports SessionLocal by reference at call time via
    # `db_module.SessionLocal`, so patching the module attribute is enough
    # as long as the router does `from app.db import SessionLocal` inside
    # the request (it doesn't) — patch app.routers.stima's binding too.
    import app.routers.stima as stima_router

    stima_router.SessionLocal = testing_session_local

    yield

    db_module.SessionLocal = original_session_local
    stima_router.SessionLocal = original_session_local


@pytest.fixture()
def client():
    return TestClient(app)


def test_reggio_emilia_85mq_totale_oracle(client):
    response = client.post(
        "/api/v1/stima",
        json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["fallback"] is False
    assert not body["disclaimer"]
    assert len(body["categorie"]) == 4
    assert Decimal(str(body["totale"]["totale_min"])) == Decimal("47985")
    assert Decimal(str(body["totale"]["totale_max"])) == Decimal("70575")


def test_extra_are_fixed_single_values(client):
    response = client.post(
        "/api/v1/stima",
        json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"},
    )
    body = response.json()

    assert len(body["extra"]) >= 1
    for extra in body["extra"]:
        assert set(extra.keys()) == {"code", "nome", "importo", "iva_pct"}


def test_totale_reconciles_with_categorie_and_extra(client):
    response = client.post(
        "/api/v1/stima",
        json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"},
    )
    body = response.json()

    cards_min = sum(Decimal(str(c["totale_min"])) for c in body["categorie"])
    cards_max = sum(Decimal(str(c["totale_max"])) for c in body["categorie"])
    extras_gross = sum(
        Decimal(str(e["importo"])) * (Decimal("1") + Decimal(str(e["iva_pct"])))
        for e in body["extra"]
    )

    totale_min = Decimal(str(body["totale"]["totale_min"]))
    totale_max = Decimal(str(body["totale"]["totale_max"]))

    assert abs((cards_min + extras_gross) - totale_min) <= 1
    assert abs((cards_max + extras_gross) - totale_max) <= 1


def test_unknown_citta_falls_back_with_disclaimer(client):
    response = client.post(
        "/api/v1/stima",
        json={"citta": "Modena", "mq": 85, "tipo": "totale"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fallback"] is True
    assert body["disclaimer"]
    assert "Reggio Emilia" in body["disclaimer"]


@pytest.mark.parametrize(
    "payload",
    [
        {"citta": "Modena", "mq": 0, "tipo": "totale"},
        {"citta": "Modena", "mq": 5000, "tipo": "totale"},
        {"citta": "Modena", "mq": 85, "tipo": "strana"},
        {"citta": "", "mq": 85, "tipo": "totale"},
    ],
)
def test_invalid_input_returns_422(client, payload):
    response = client.post("/api/v1/stima", json=payload)
    assert response.status_code == 422


# --- catalogo domande (0014): il layer parametrico sul filo HTTP ------------


def test_risposte_assenti_lasciano_loracolo_intatto(client):
    """Il contratto pubblico non cambia: un client che posta ancora
    {citta, mq, tipo} riceve lo stesso identico numero di prima."""
    response = client.post(
        "/api/v1/stima",
        json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"},
    )

    assert response.status_code == 200
    body = response.json()
    assert Decimal(str(body["totale"]["totale_min"])) == Decimal("47985")
    assert body["input"]["risposte"] is None


def test_risposte_vuote_non_muovono_il_totale(client):
    response = client.post(
        "/api/v1/stima",
        json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale", "risposte": {}},
    )

    assert response.status_code == 200
    assert Decimal(str(response.json()["totale"]["totale_min"])) == Decimal("47985")


def test_risposte_tornano_nelleco_per_finire_nello_snapshot(client):
    """Una stima salvata deve restare spiegabile: le risposte che l'hanno
    prodotta vanno congelate insieme al risultato."""
    risposte = {"bagni": 3, "anno_costruzione": "pre_1980", "impianti": ["termico"]}
    response = client.post(
        "/api/v1/stima",
        json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale", "risposte": risposte},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["input"]["risposte"] == risposte
    assert Decimal(str(body["totale"]["totale_min"])) > Decimal("47985")


def test_risposte_restano_input_non_fidato(client):
    """`risposte` arriva dal client come `mq`, quindi va bloccato allo schema
    (ASVS V5) e non solo nel motore."""
    for risposte in (
        {"bagni": 99_999},  # numero fuori range
        {"bagni": -1},
        {"x" * 100: 1},  # chiave oltre il limite
        {"impianti": ["a" * 100]},  # codice opzione oltre il limite
        {"impianti": ["x"] * 50},  # lista oltre il limite
    ):
        response = client.post(
            "/api/v1/stima",
            json={"citta": "Reggio Emilia", "mq": 85, "tipo": "totale", "risposte": risposte},
        )
        assert response.status_code == 422, risposte


def test_nessun_leak_con_le_risposte_attive(client):
    """L'anti-leak vale anche sul ramo nuovo: le correzioni sono in
    euro-cliente e nulla del margine impresa deve affiorare."""
    response = client.post(
        "/api/v1/stima",
        json={
            "citta": "Reggio Emilia",
            "mq": 85,
            "tipo": "totale",
            "risposte": {"bagni": 3, "livello_finiture": "alto"},
        },
    )

    assert response.status_code == 200
    grezzo = response.text.lower()
    for vietata in ("coefficiente_impresa", "prezzo_impresa", "base_eur_mq", "moltiplicatore"):
        assert vietata not in grezzo
