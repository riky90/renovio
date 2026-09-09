"""Domain-guard test (EST-05 / CLAUDE.md rule 1): the impresa secret must
never appear anywhere in the serialized POST /api/v1/stima response, for any
città (RE non-fallback and a fallback città) and any tipo.
"""

from __future__ import annotations

import json

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

    # Il blocco `bonus` (0011) viene ESCLUSO dallo scan a sottostringhe, ed e'
    # l'unica esclusione del file. Motivo: le aliquote fiscali abitano lo stesso
    # intervallo numerico dei coefficienti impresa e li COINCIDONO davvero — il
    # coefficiente di D-PRODOTTI e' 0.5 e il bonus ristrutturazione prima casa
    # e' il 50%, cioe' "0.5000". Nessuno scan testuale (ne' un confronto per
    # valore) puo' distinguere i due, quindi tenerli insieme renderebbe il test
    # rosso per una collisione di cifre invece che per una fuga.
    #
    # La garanzia non si indebolisce, si sposta: il blocco bonus e' un DTO a
    # campi chiusi (`BonusOut`/`BonusDettaglioOut` in schemas/stima.py) e qui
    # sotto se ne verifica l'elenco esatto delle chiavi. Aggiungere un campo a
    # quel DTO rompe questo test, che e' esattamente il comportamento voluto:
    # nessun campo nuovo entra nella risposta senza passare da qui.
    bonus = body.get("bonus")
    corpo_senza_bonus = {k: v for k, v in body.items() if k != "bonus"}
    raw_text = json.dumps(corpo_senza_bonus)

    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in raw_text, f"forbidden substring '{forbidden}' leaked in response"

    for coeff_value in FORBIDDEN_COEFFICIENT_VALUES:
        assert coeff_value not in raw_text, f"forbidden coefficient value '{coeff_value}' leaked in response"

    _assert_no_forbidden_keys(body)

    if bonus is not None:
        assert set(bonus) == {
            "bonus",
            "detrazione_min",
            "detrazione_max",
            "rata_annua_min",
            "rata_annua_max",
            "disclaimer",
        }
        for dettaglio in bonus["bonus"]:
            assert set(dettaglio) == {
                "code",
                "nome",
                "descrizione",
                "base_min",
                "base_max",
                "aliquota_pct",
                "tetto_spesa_eur",
                "tetto_modalita",
                "tetto_raggiunto",
                "rate_annuali",
                "detrazione_min",
                "detrazione_max",
                "rata_annua_min",
                "rata_annua_max",
            }
