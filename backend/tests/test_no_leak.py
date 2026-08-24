"""Domain-guard test (EST-05 / CLAUDE.md rule 1): the impresa secret must
never appear anywhere in the serialized POST /api/v1/stima response, for any
città (RE non-fallback and a fallback città) and any tipo.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.db import Base
from app.main import app
from scripts.seed import load_seed_data, seed

FORBIDDEN_SUBSTRINGS = [
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
]

FORBIDDEN_COEFFICIENT_VALUES = ["0.65", "0.6", "0.55", "0.5"]

FORBIDDEN_KEYS = {
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
}


@pytest.fixture(autouse=True, scope="module")
def _seeded_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test_no_leak.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()

    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = testing_session_local

    import app.routers.stima as stima_router

    stima_router.SessionLocal = testing_session_local

    yield

    db_module.SessionLocal = original_session_local
    stima_router.SessionLocal = original_session_local


@pytest.fixture()
def client():
    return TestClient(app)


def _assert_no_forbidden_keys(node) -> None:
    """Recurse the parsed JSON and assert no key matches the forbidden set
    at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, f"forbidden key '{key}' found in response"
            _assert_no_forbidden_keys(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_forbidden_keys(item)


@pytest.mark.parametrize(
    "citta,fallback_expected",
    [
        ("Reggio Emilia", False),
        ("Modena", True),
    ],
)
@pytest.mark.parametrize("tipo", ["leggera", "moderata", "totale"])
def test_response_never_leaks_impresa_secret(client, citta, fallback_expected, tipo):
    response = client.post(
        "/api/v1/stima",
        json={"citta": citta, "mq": 85, "tipo": tipo},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["fallback"] is fallback_expected

    raw_text = response.text

    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in raw_text, f"forbidden substring '{forbidden}' leaked in response"

    for coeff_value in FORBIDDEN_COEFFICIENT_VALUES:
        assert coeff_value not in raw_text, f"forbidden coefficient value '{coeff_value}' leaked in response"

    _assert_no_forbidden_keys(body)
