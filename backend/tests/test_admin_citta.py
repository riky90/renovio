"""E2E tests (RED->GREEN, TDD) per /api/v1/admin/citta (ADM-03,
04-03-PLAN.md Task 2): CRUD ComuneListino (city->listino mapping) +
list/patch TipoRistrutturazione.

Copre: 403 su ogni route per non-admin (T-04-11); slug ricalcolato
server-side su create/patch (coerente con `city_resolver.resolve_listino`,
T-04-12); upsert idempotente su POST stesso comune_nome (D-24, non
duplica); DELETE elimina solo la riga indicata; collegamento CRUD<->motore
verificato via POST /api/v1/stima dopo la creazione di una mappatura.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
STIMA_URL = "/api/v1/stima"
CITTA_URL = "/api/v1/admin/citta"

ADMIN_EMAIL = "admin.citta@example.com"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    db_path = tmp_path / "test_admin_citta.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module
    import app.routers.stima as stima_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(stima_router_module, "SessionLocal", testing_session_local)

    return TestClient(app)


def _registra_admin(client, email=ADMIN_EMAIL, nome="Admin Citta"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def _registra_user(client, email="utente.normale.citta@example.com", nome="Utente Normale"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def _listino_re_id(client) -> int:
    from app.models.listino import Listino

    session_local = db_module.SessionLocal
    with session_local() as session:
        row = session.query(Listino).filter_by(citta_riferimento="Reggio Emilia").one()
        return row.id


class TestAdminCittaGuard403:
    """T-04-11: non-admin riceve 403/401 su OGNI route /admin/citta."""

    def test_get_citta_401_senza_sessione(self, client):
        response = client.get(CITTA_URL)
        assert response.status_code == 401

    def test_get_citta_403_per_non_admin(self, client):
        _registra_user(client)
        response = client.get(CITTA_URL)
        assert response.status_code == 403

    def test_post_citta_403_per_non_admin(self, client):
        _registra_user(client)
        response = client.post(CITTA_URL, json={"comune_nome": "X", "listino_id": 1})
        assert response.status_code == 403

    def test_patch_citta_403_per_non_admin(self, client):
        _registra_user(client)
        response = client.patch(f"{CITTA_URL}/1", json={"comune_nome": "X"})
        assert response.status_code == 403

    def test_delete_citta_403_per_non_admin(self, client):
        _registra_user(client)
        response = client.delete(f"{CITTA_URL}/1")
        assert response.status_code == 403

    def test_tipi_403_per_non_admin(self, client):
        _registra_user(client)
        assert client.get(f"{CITTA_URL}/tipi").status_code == 403
        assert client.patch(f"{CITTA_URL}/tipi/leggera", json={}).status_code == 403


class TestCrudComuneListino:
    """Task 2: CRUD mappatura citta->listino, slug ricalcolato server-side."""

    def test_get_citta_lista(self, client):
        _registra_admin(client)
        response = client.get(CITTA_URL)
        assert response.status_code == 200
        nomi = [row["comune_nome"] for row in response.json()]
        assert "Reggio Emilia" in nomi

    def test_post_citta_crea_mappatura_slug_ricalcolato(self, client):
        _registra_admin(client)
        listino_id = _listino_re_id(client)

        response = client.post(CITTA_URL, json={"comune_nome": "Reggio Nell'Emilia Est", "listino_id": listino_id})
        assert response.status_code in (200, 201)
        body = response.json()
        assert body["comune_slug"] == "reggio-nell-emilia-est"
        assert body["listino_id"] == listino_id

    def test_post_citta_collegamento_crud_motore(self, client):
        """Creare una mappatura citta->listino e poi risolverla via
        POST /api/v1/stima restituisce il listino mappato (niente fallback)."""
        _registra_admin(client)
        listino_id = _listino_re_id(client)

        client.post(CITTA_URL, json={"comune_nome": "Correggio", "listino_id": listino_id})

        stima_response = client.post(STIMA_URL, json={"citta": "Correggio", "mq": 85, "tipo": "totale"})
        assert stima_response.status_code == 200
        assert stima_response.json()["fallback"] is False

    def test_post_citta_upsert_idempotente_stesso_comune(self, client):
        _registra_admin(client)
        listino_id = _listino_re_id(client)

        client.post(CITTA_URL, json={"comune_nome": "Scandiano", "listino_id": listino_id})
        second = client.post(CITTA_URL, json={"comune_nome": "Scandiano", "listino_id": listino_id})
        assert second.status_code in (200, 201)

        rows = [r for r in client.get(CITTA_URL).json() if r["comune_slug"] == "scandiano"]
        assert len(rows) == 1

    def test_patch_citta_ricalcola_slug(self, client):
        _registra_admin(client)
        listino_id = _listino_re_id(client)
        created = client.post(CITTA_URL, json={"comune_nome": "Rubiera", "listino_id": listino_id}).json()

        response = client.patch(f"{CITTA_URL}/{created['id']}", json={"comune_nome": "Rubiera Nuova"})
        assert response.status_code == 200
        body = response.json()
        assert body["comune_nome"] == "Rubiera Nuova"
        assert body["comune_slug"] == "rubiera-nuova"

    def test_patch_citta_inesistente_404(self, client):
        _registra_admin(client)
        response = client.patch(f"{CITTA_URL}/999999", json={"comune_nome": "X"})
        assert response.status_code == 404

    def test_delete_citta_elimina_solo_la_riga(self, client):
        _registra_admin(client)
        listino_id = _listino_re_id(client)
        created = client.post(CITTA_URL, json={"comune_nome": "Cavriago", "listino_id": listino_id}).json()

        response = client.delete(f"{CITTA_URL}/{created['id']}")
        assert response.status_code in (200, 204)

        rimanenti = client.get(CITTA_URL).json()
        assert all(r["id"] != created["id"] for r in rimanenti)
        # Le altre mappature (es. Reggio Emilia dal seed) restano intatte.
        assert any(r["comune_nome"] == "Reggio Emilia" for r in rimanenti)

    def test_delete_citta_inesistente_404(self, client):
        _registra_admin(client)
        response = client.delete(f"{CITTA_URL}/999999")
        assert response.status_code == 404


class TestListPatchTipoRistrutturazione:
    """Task 2: list/patch TipoRistrutturazione (nome, ordine, range_pct)."""

    def test_get_tipi_lista(self, client):
        _registra_admin(client)
        response = client.get(f"{CITTA_URL}/tipi")
        assert response.status_code == 200
        codes = [row["code"] for row in response.json()]
        assert {"leggera", "moderata", "totale"}.issubset(set(codes))

    def test_patch_tipo_modifica_range_pct(self, client):
        _registra_admin(client)
        response = client.patch(f"{CITTA_URL}/tipi/leggera", json={"range_pct": "0.100"})
        assert response.status_code == 200
        assert float(response.json()["range_pct"]) == 0.1

    def test_patch_tipo_inesistente_404(self, client):
        _registra_admin(client)
        response = client.patch(f"{CITTA_URL}/tipi/mai-esistito", json={"range_pct": "0.1"})
        assert response.status_code == 404
