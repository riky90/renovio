"""Test API delle scelte del wizard Pro (09-11, gap G3): `GET /me/opzioni-pro`
espone le domande a scelta del configuratore (es. `tipo_pavimento`) e
`POST /me/stime` valida `preferenze_pro.scelte` contro il catalogo prima di
scriverle in `risposte_pro_json`.

Fixture: stesso pattern di `test_dettaglio_pro_paywall.py`/`test_no_leak.py`
(engine-swap + TestClient, seed reale — serve perche' `domande_configuratore`
legge da `Domanda`/`OpzioneDomanda`/`EffettoOpzione` popolate dal seed, e la
verifica di A.6.2 legge da `Sottocategoria`/`Voce`/`CoefficienteQuantitaVoce`).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
STIME_URL = "/api/v1/me/stime"
OPZIONI_PRO_URL = "/api/v1/me/opzioni-pro"
ATTIVA_PRO_URL = "/api/v1/me/pro/attiva"

FORBIDDEN_KEYS = {
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
}
FORBIDDEN_KEY_SUBSTRINGS = ["effett", "coefficiente", "impresa", "tipo_effetto", "target_"]


def _assert_no_forbidden_keys(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, f"forbidden key '{key}' found in response"
            for forbidden in FORBIDDEN_KEY_SUBSTRINGS:
                assert forbidden not in key, f"forbidden substring '{forbidden}' found in key '{key}'"
            _assert_no_forbidden_keys(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_forbidden_keys(item)


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()

    db_path = tmp_path / "test_wizard_pro_scelte.db"
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


def _registra(client, email="wizard.pro@example.com", password="Password123", nome="Wizard Pro"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


def _registra_pro(client, email="wizard.pro@example.com") -> None:
    _registra(client, email=email)
    client.post(ATTIVA_PRO_URL)


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


class TestOpzioniProDomande:
    def test_opzioni_pro_espone_tipo_pavimento_con_default(self, client):
        _registra_pro(client)

        response = client.get(OPZIONI_PRO_URL)

        assert response.status_code == 200
        body = response.json()
        domanda = next((d for d in body["domande"] if d["code"] == "tipo_pavimento"), None)
        assert domanda is not None, "tipo_pavimento assente da /me/opzioni-pro"
        codici_opzione = {o["code"] for o in domanda["opzioni"]}
        assert "gres" in codici_opzione
        assert "parquet" in codici_opzione
        assert domanda["valore"] == "gres"  # default di catalogo (is_default)

    def test_opzioni_pro_esclude_domande_numeriche(self, client):
        _registra_pro(client)

        response = client.get(OPZIONI_PRO_URL)

        codici = {d["code"] for d in response.json()["domande"]}
        for numerica in ("bagni", "porte", "condizionatori"):
            assert numerica not in codici

    def test_opzioni_pro_anonimo_401(self, client):
        response = client.get(OPZIONI_PRO_URL)
        assert response.status_code == 401

    def test_opzioni_pro_free_403(self, client):
        _registra(client)

        response = client.get(OPZIONI_PRO_URL)

        assert response.status_code == 403

    def test_opzioni_pro_non_leaka_effetti_ne_coefficienti(self, client):
        _registra_pro(client)

        response = client.get(OPZIONI_PRO_URL)

        _assert_no_forbidden_keys(response.json())


class TestSalvaStimaConScelte:
    def test_scelta_pavimento_valida_arriva_al_dettaglio_pro(self, client):
        _registra_pro(client)

        created = client.post(
            STIME_URL,
            json={
                **_stima_payload(),
                "preferenze_pro": {
                    "risposte": {"bagni": 1, "porte": 5, "condizionatori": 2},
                    "scelte": {"tipo_pavimento": "parquet"},
                },
            },
        )
        assert created.status_code == 201
        stima_id = created.json()["id"]

        dettaglio = client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")
        assert dettaglio.status_code == 200
        body = dettaglio.json()
        assert body["risposte"]["tipo_pavimento"] == "parquet"

        a6 = next(
            sotto
            for cat in body["categorie"]
            for sotto in cat["sottocategorie"]
            if sotto["codice"] == "A.6"
        )
        codici_voce = {v["codice"] for v in a6["voci"]}
        assert "A.6.2" in codici_voce

    def test_scelta_pavimento_opzione_inesistente_400(self, client):
        _registra_pro(client)

        response = client.post(
            STIME_URL,
            json={**_stima_payload(), "preferenze_pro": {"scelte": {"tipo_pavimento": "legno"}}},
        )

        assert response.status_code == 400

    def test_scelta_domanda_inesistente_400(self, client):
        _registra_pro(client)

        response = client.post(
            STIME_URL,
            json={**_stima_payload(), "preferenze_pro": {"scelte": {"inesistente": "x"}}},
        )

        assert response.status_code == 400

    def test_scelta_su_domanda_numerica_400(self, client):
        _registra_pro(client)

        response = client.post(
            STIME_URL,
            json={**_stima_payload(), "preferenze_pro": {"scelte": {"bagni": "3"}}},
        )

        assert response.status_code == 400

    def test_scelte_oltre_20_chiavi_rifiutate(self, client):
        _registra_pro(client)

        troppe_scelte = {f"chiave_{i}": "valore" for i in range(21)}
        response = client.post(
            STIME_URL,
            json={**_stima_payload(), "preferenze_pro": {"scelte": troppe_scelte}},
        )

        assert response.status_code in (400, 422)

    def test_senza_scelte_comportamento_invariato(self, client):
        _registra_pro(client)

        response = client.post(
            STIME_URL,
            json={
                **_stima_payload(),
                "preferenze_pro": {"risposte": {"bagni": 1, "porte": 5, "condizionatori": 2}},
            },
        )

        assert response.status_code == 201
        stima_id = response.json()["id"]

        dettaglio = client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")
        assert dettaglio.status_code == 200
        assert "tipo_pavimento" not in dettaglio.json()["risposte"]
