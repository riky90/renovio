"""E2E tests (RED->GREEN, TDD) per /api/v1/admin/listini (ADM-01,
04-02-PLAN.md): creazione Listino per citta nuova + mappatura
ComuneListino (Task 2), CRUD categoria base_eur_mq/coefficiente_impresa
(Task 2), CRUD voce prezzo/UM a chiave naturale stabile (Task 3).

Copre: 403 su ogni route per non-admin (T-04-07); creazione listino+citta
risolvibile subito da /api/v1/stima senza fallback (D-13); upsert
idempotente su categoria (D-24, non duplica su stessa chiave naturale);
DELETE elimina solo la riga indicata; VoceAdminIn non accetta/non muta
descrizione (Pitfall 2).

Fino a quando `routers/admin/listini.py` non ha le route implementate,
queste richieste ritornano 404 -> RED come atteso.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from scripts.seed import load_seed_data, seed

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LOGOUT_URL = "/api/v1/auth/logout"
STIMA_URL = "/api/v1/stima"
LISTINI_URL = "/api/v1/admin/listini"

ADMIN_EMAIL = "admin.listini@example.com"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    db_path = tmp_path / "test_admin_listini.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

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


def _registra_admin(client, email=ADMIN_EMAIL, nome="Admin Listini"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def _registra_user(client, email="utente.normale@example.com", nome="Utente Normale"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


class TestAdminGuard403:
    """T-04-07: non-admin riceve 403 su OGNI route /admin/listini."""

    def test_get_listini_403_per_non_admin(self, client):
        _registra_user(client)
        response = client.get(LISTINI_URL)
        assert response.status_code == 403

    def test_post_listini_403_per_non_admin(self, client):
        _registra_user(client)
        response = client.post(LISTINI_URL, json={"nome": "X", "citta_riferimento": "X"})
        assert response.status_code == 403

    def test_patch_listino_403_per_non_admin(self, client):
        _registra_user(client)
        response = client.patch(f"{LISTINI_URL}/1", json={"nome": "X"})
        assert response.status_code == 403

    def test_categorie_403_per_non_admin(self, client):
        _registra_user(client)
        assert client.get(f"{LISTINI_URL}/1/categorie").status_code == 403
        assert client.post(f"{LISTINI_URL}/1/categorie", json={}).status_code == 403
        assert client.patch(f"{LISTINI_URL}/categorie/1", json={}).status_code == 403
        assert client.delete(f"{LISTINI_URL}/categorie/1").status_code == 403

    def test_voci_403_per_non_admin(self, client):
        _registra_user(client)
        assert client.get(f"{LISTINI_URL}/categorie/1/voci").status_code == 403
        assert client.patch(f"{LISTINI_URL}/voci/1", json={}).status_code == 403
        assert client.delete(f"{LISTINI_URL}/voci/1").status_code == 403

    def test_get_listini_401_senza_sessione(self, client):
        response = client.get(LISTINI_URL)
        assert response.status_code == 401


class TestCreazioneListinoECitta:
    """Task 2: POST /admin/listini crea Listino + ComuneListino (D-13),
    citta nuova subito risolvibile da /api/v1/stima senza fallback."""

    def test_post_listini_crea_listino_e_comune_listino(self, client):
        _registra_admin(client)

        response = client.post(
            LISTINI_URL,
            json={"nome": "Parma", "citta_riferimento": "Parma", "is_default": False},
        )
        assert response.status_code in (200, 201)
        body = response.json()
        assert body["nome"] == "Parma"
        assert body["citta_riferimento"] == "Parma"
        assert body["is_default"] is False
        assert "id" in body

        # EstimationService richiede una riga listino_categoria per OGNI
        # categoria (base_eur_mq/coefficiente_impresa) — il CRUD categoria
        # e' un percorso separato dalla creazione del Listino (D-09, upload
        # bulk vs ritocco puntuale); qui simuliamo il ritocco puntuale.
        for categoria_code in ("A-EDILE", "B-FINITURE", "C-SERRAMENTI", "D-PRODOTTI"):
            cat_response = client.post(
                f"{LISTINI_URL}/{body['id']}/categorie",
                json={"categoria_code": categoria_code, "base_eur_mq": "100.00", "coefficiente_impresa": "0.6"},
            )
            assert cat_response.status_code in (200, 201)

        stima_response = client.post(STIMA_URL, json={"citta": "Parma", "mq": 85, "tipo": "totale"})
        assert stima_response.status_code == 200
        assert stima_response.json()["fallback"] is False

    def test_get_listini_lista(self, client):
        _registra_admin(client)
        client.post(LISTINI_URL, json={"nome": "Bologna", "citta_riferimento": "Bologna"})

        response = client.get(LISTINI_URL)
        assert response.status_code == 200
        nomi = [row["nome"] for row in response.json()]
        assert "Bologna" in nomi
        assert "Reggio Emilia" in nomi

    def test_patch_listino_modifica_nome_e_is_default(self, client):
        _registra_admin(client)
        created = client.post(LISTINI_URL, json={"nome": "Modena", "citta_riferimento": "Modena"}).json()

        response = client.patch(f"{LISTINI_URL}/{created['id']}", json={"nome": "Modena (aggiornato)"})
        assert response.status_code == 200
        assert response.json()["nome"] == "Modena (aggiornato)"

    def test_patch_listino_inesistente_404(self, client):
        _registra_admin(client)
        response = client.patch(f"{LISTINI_URL}/999999", json={"nome": "X"})
        assert response.status_code == 404


class TestCrudCategoria:
    """Task 2: CRUD listino_categoria — Out espone base_eur_mq/coefficiente_impresa."""

    def _listino_re_id(self, client) -> int:
        rows = client.get(LISTINI_URL).json()
        return next(r["id"] for r in rows if r["citta_riferimento"] == "Reggio Emilia")

    def test_get_categorie_espone_coefficiente_e_base(self, client):
        _registra_admin(client)
        listino_id = self._listino_re_id(client)

        response = client.get(f"{LISTINI_URL}/{listino_id}/categorie")
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) >= 4
        for row in rows:
            assert "base_eur_mq" in row
            assert "coefficiente_impresa" in row

    def test_post_categoria_nuovo_listino(self, client):
        _registra_admin(client)
        listino = client.post(LISTINI_URL, json={"nome": "Ferrara", "citta_riferimento": "Ferrara"}).json()

        response = client.post(
            f"{LISTINI_URL}/{listino['id']}/categorie",
            json={"categoria_code": "A-EDILE", "base_eur_mq": "100.00", "coefficiente_impresa": "0.65"},
        )
        assert response.status_code in (200, 201)
        body = response.json()
        assert body["base_eur_mq"] == "100.00" or float(body["base_eur_mq"]) == 100.0
        assert body["coefficiente_impresa"] == "0.65" or float(body["coefficiente_impresa"]) == 0.65

    def test_post_categoria_upsert_idempotente_stessa_chiave(self, client):
        _registra_admin(client)
        listino = client.post(LISTINI_URL, json={"nome": "Piacenza", "citta_riferimento": "Piacenza"}).json()

        client.post(
            f"{LISTINI_URL}/{listino['id']}/categorie",
            json={"categoria_code": "B-FINITURE", "base_eur_mq": "50.00", "coefficiente_impresa": "0.6"},
        )
        second = client.post(
            f"{LISTINI_URL}/{listino['id']}/categorie",
            json={"categoria_code": "B-FINITURE", "base_eur_mq": "55.00", "coefficiente_impresa": "0.6"},
        )
        assert second.status_code in (200, 201)

        categorie = client.get(f"{LISTINI_URL}/{listino['id']}/categorie").json()
        finiture_rows = [c for c in categorie if c["categoria_code"] == "B-FINITURE"]
        assert len(finiture_rows) == 1
        assert float(finiture_rows[0]["base_eur_mq"]) == 55.00

    def test_patch_categoria_modifica_base_e_coefficiente(self, client):
        _registra_admin(client)
        listino_id = self._listino_re_id(client)
        categoria = client.get(f"{LISTINI_URL}/{listino_id}/categorie").json()[0]

        response = client.patch(
            f"{LISTINI_URL}/categorie/{categoria['id']}",
            json={"base_eur_mq": "999.99"},
        )
        assert response.status_code == 200
        assert float(response.json()["base_eur_mq"]) == 999.99

    def test_patch_categoria_inesistente_404(self, client):
        _registra_admin(client)
        response = client.patch(f"{LISTINI_URL}/categorie/999999", json={"base_eur_mq": "1.00"})
        assert response.status_code == 404

    def test_delete_categoria_elimina_solo_la_riga(self, client):
        _registra_admin(client)
        listino = client.post(LISTINI_URL, json={"nome": "Carpi", "citta_riferimento": "Carpi"}).json()
        client.post(
            f"{LISTINI_URL}/{listino['id']}/categorie",
            json={"categoria_code": "A-EDILE", "base_eur_mq": "10.00", "coefficiente_impresa": "0.65"},
        )
        cat_a = client.post(
            f"{LISTINI_URL}/{listino['id']}/categorie",
            json={"categoria_code": "B-FINITURE", "base_eur_mq": "20.00", "coefficiente_impresa": "0.6"},
        ).json()

        response = client.delete(f"{LISTINI_URL}/categorie/{cat_a['id']}")
        assert response.status_code in (200, 204)

        remaining = client.get(f"{LISTINI_URL}/{listino['id']}/categorie").json()
        codes = {c["categoria_code"] for c in remaining}
        assert "B-FINITURE" not in codes
        assert "A-EDILE" in codes


class TestCrudVoce:
    """Task 3: CRUD voce (prezzo/UM), descrizione/codice non editabili."""

    def test_get_voci_per_categoria_lista(self, client, admin_voce_esistente):
        response = client.get(f"{LISTINI_URL}/categorie/{admin_voce_esistente['sottocategoria_id']}/voci")
        assert response.status_code == 200
        rows = response.json()
        assert any(v["id"] == admin_voce_esistente["id"] for v in rows)

    def test_patch_voce_modifica_prezzo_e_um(self, client, admin_voce_esistente):
        response = client.patch(
            f"{LISTINI_URL}/voci/{admin_voce_esistente['id']}",
            json={"prezzo_cliente": "123.45", "um": "mq"},
        )
        assert response.status_code == 200
        body = response.json()
        assert float(body["prezzo_cliente"]) == 123.45
        assert body["um"] == "mq"
        assert body["descrizione"] == admin_voce_esistente["descrizione"]

    def test_patch_voce_ignora_descrizione_non_nello_schema(self, client, admin_voce_esistente):
        response = client.patch(
            f"{LISTINI_URL}/voci/{admin_voce_esistente['id']}",
            json={"prezzo_cliente": "10.00", "um": "pz", "descrizione": "Tentativo di rename"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["descrizione"] == admin_voce_esistente["descrizione"]

    def test_patch_voce_inesistente_404(self, client):
        response = client.patch(f"{LISTINI_URL}/voci/999999", json={"prezzo_cliente": "1.00", "um": "mq"})
        assert response.status_code == 404

    def test_delete_voce_elimina_singola_riga(self, client, admin_voce_esistente):
        response = client.delete(f"{LISTINI_URL}/voci/{admin_voce_esistente['id']}")
        assert response.status_code in (200, 204)

        listing = client.get(f"{LISTINI_URL}/categorie/{admin_voce_esistente['sottocategoria_id']}/voci").json()
        assert all(v["id"] != admin_voce_esistente["id"] for v in listing)


@pytest.fixture()
def admin_voce_esistente(client):
    """Registra l'admin e ritorna la prima Voce esistente del seed RE (via
    accesso diretto al DB di test, dato che il router non espone un
    endpoint per elencare le sottocategorie in questo piano)."""
    _registra_admin(client)

    from app.models.dettaglio_pro import Voce

    session_local = db_module.SessionLocal
    with session_local() as session:
        voce = session.query(Voce).order_by(Voce.id).first()
        assert voce is not None, "seed atteso: almeno una Voce presente"
        return {
            "id": voce.id,
            "sottocategoria_id": voce.sottocategoria_id,
            "descrizione": voce.descrizione,
        }
