"""E2E tests (RED->GREEN, TDD) per /api/v1/admin/coefficienti (ADM-02,
04-10-PLAN.md): CRUD delle 4 famiglie di coefficienti D-12 (moltiplicatori
tipo×categoria, IVA per categoria, extra, coefficienti quantità-per-m² Pro)
+ GET base_eur_mq in sola lettura.

Copre: 403 su ogni route per non-admin (T-04-38); bound Pydantic sui valori
fuori dominio (T-04-39, ASVS V5); PATCH non azzera righe non toccate
(T-04-40, D-24); effetto immediato — dopo un PATCH del moltiplicatore, una
nuova POST /api/v1/stima riflette subito il nuovo valore, senza cache
(D-11); nessun campo impresa (`coefficiente_impresa`) esposto da questo
modulo (T-04-41).

Fino a quando `routers/admin/coefficienti.py` non ha le route implementate,
queste richieste ritornano 404 -> RED come atteso.
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
from tests.computo_spento import catalogo_v2
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
STIMA_URL = "/api/v1/stima"
COEFF_URL = "/api/v1/admin/coefficienti"

ADMIN_EMAIL = "admin.coefficienti@example.com"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    db_path = tmp_path / "test_admin_coefficienti.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())
        # Numeri del percorso EUR/m2 + effetti (catalogo v2): tests/computo_spento.py
        catalogo_v2(s)

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module
    import app.routers.stima as stima_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(stima_router_module, "SessionLocal", testing_session_local)

    return TestClient(app)


def _registra_admin(client, email=ADMIN_EMAIL, nome="Admin Coefficienti"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def _registra_user(client, email="utente.normale.coeff@example.com", nome="Utente Normale"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


class TestAdminGuard403:
    """T-04-38: non-admin riceve 403 su OGNI route /admin/coefficienti."""

    def test_get_moltiplicatori_403_per_non_admin(self, client):
        _registra_user(client)
        assert client.get(f"{COEFF_URL}/moltiplicatori").status_code == 403

    def test_patch_moltiplicatore_403_per_non_admin(self, client):
        _registra_user(client)
        assert client.patch(f"{COEFF_URL}/moltiplicatori/1", json={"valore": "1.0"}).status_code == 403

    def test_iva_403_per_non_admin(self, client):
        _registra_user(client)
        assert client.get(f"{COEFF_URL}/iva").status_code == 403
        assert client.patch(f"{COEFF_URL}/iva/A-EDILE", json={"iva_pct": "0.1"}).status_code == 403

    def test_extra_403_per_non_admin(self, client):
        _registra_user(client)
        assert client.get(f"{COEFF_URL}/extra").status_code == 403
        assert client.post(f"{COEFF_URL}/extra", json={}).status_code == 403
        assert client.patch(f"{COEFF_URL}/extra/CSE_CSP", json={}).status_code == 403
        assert client.delete(f"{COEFF_URL}/extra/CSE_CSP").status_code == 403

    def test_coeff_pro_403_per_non_admin(self, client):
        _registra_user(client)
        assert client.get(f"{COEFF_URL}/coeff-pro").status_code == 403
        assert client.patch(f"{COEFF_URL}/coeff-pro/1", json={"valore": "1.0"}).status_code == 403

    def test_base_403_per_non_admin(self, client):
        _registra_user(client)
        assert client.get(f"{COEFF_URL}/base").status_code == 403

    def test_get_moltiplicatori_401_senza_sessione(self, client):
        assert client.get(f"{COEFF_URL}/moltiplicatori").status_code == 401


class TestCrudMoltiplicatori:
    def test_get_moltiplicatori_lista_12_righe(self, client):
        _registra_admin(client)
        response = client.get(f"{COEFF_URL}/moltiplicatori")
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 12
        for row in rows:
            assert "tipo_code" in row
            assert "categoria_code" in row
            assert "valore" in row

    def test_patch_moltiplicatore_modifica_valore(self, client):
        _registra_admin(client)
        rows = client.get(f"{COEFF_URL}/moltiplicatori").json()
        target = next(r for r in rows if r["tipo_code"] == "totale" and r["categoria_code"] == "A-EDILE")

        response = client.patch(f"{COEFF_URL}/moltiplicatori/{target['id']}", json={"valore": "1.5"})
        assert response.status_code == 200
        assert float(response.json()["valore"]) == 1.5

    def test_patch_moltiplicatore_valore_non_positivo_422(self, client):
        _registra_admin(client)
        rows = client.get(f"{COEFF_URL}/moltiplicatori").json()
        response = client.patch(f"{COEFF_URL}/moltiplicatori/{rows[0]['id']}", json={"valore": "0"})
        assert response.status_code == 422

    def test_patch_moltiplicatore_inesistente_404(self, client):
        _registra_admin(client)
        response = client.patch(f"{COEFF_URL}/moltiplicatori/999999", json={"valore": "1.0"})
        assert response.status_code == 404

    def test_patch_moltiplicatore_non_tocca_le_altre_righe(self, client):
        """D-24: PATCH su una riga non azzera/modifica le altre 11."""
        _registra_admin(client)
        before = client.get(f"{COEFF_URL}/moltiplicatori").json()
        target = before[0]
        altri_prima = {r["id"]: r["valore"] for r in before if r["id"] != target["id"]}

        client.patch(f"{COEFF_URL}/moltiplicatori/{target['id']}", json={"valore": "2.0"})

        after = client.get(f"{COEFF_URL}/moltiplicatori").json()
        altri_dopo = {r["id"]: r["valore"] for r in after if r["id"] != target["id"]}
        assert altri_prima == altri_dopo


class TestEffettoImmediato:
    """D-11: una nuova stima calcolata dopo un edit admin usa subito i
    nuovi valori — nessuna cache lato EstimationService."""

    def test_patch_moltiplicatore_riflesso_su_nuova_stima(self, client):
        _registra_admin(client)

        stima_prima = client.post(STIMA_URL, json={"citta": "Reggio Emilia", "mq": 100, "tipo": "totale"})
        assert stima_prima.status_code == 200
        totale_min_prima = stima_prima.json()["totale"]["totale_min"]

        rows = client.get(f"{COEFF_URL}/moltiplicatori").json()
        target = next(r for r in rows if r["tipo_code"] == "totale" and r["categoria_code"] == "A-EDILE")
        nuovo_valore = float(target["valore"]) * 3
        patch_response = client.patch(f"{COEFF_URL}/moltiplicatori/{target['id']}", json={"valore": str(nuovo_valore)})
        assert patch_response.status_code == 200

        stima_dopo = client.post(STIMA_URL, json={"citta": "Reggio Emilia", "mq": 100, "tipo": "totale"})
        assert stima_dopo.status_code == 200
        totale_min_dopo = stima_dopo.json()["totale"]["totale_min"]

        assert totale_min_dopo != totale_min_prima


class TestCrudIva:
    def test_get_iva_lista_tutte_le_categorie(self, client):
        """Cinque dalla fase 07: l'admin governa l'IVA di OGNI categoria in
        tabella, compresa `E-ARREDO`, che e' fuori dal totale lavori ma avra'
        voci Pro con la loro aliquota (fase 08). Nasconderla qui vorrebbe dire
        un'aliquota non modificabile da pannello, contro ENG-02."""
        _registra_admin(client)
        response = client.get(f"{COEFF_URL}/iva")
        assert response.status_code == 200
        rows = response.json()
        codes = {r["code"] for r in rows}
        assert codes == {"A-EDILE", "B-FINITURE", "C-SERRAMENTI", "D-PRODOTTI", "E-ARREDO"}
        assert len(rows) == 5

    def test_patch_iva_modifica_categoria(self, client):
        _registra_admin(client)
        response = client.patch(f"{COEFF_URL}/iva/B-FINITURE", json={"iva_pct": "0.22"})
        assert response.status_code == 200
        assert float(response.json()["iva_pct"]) == 0.22

    def test_patch_iva_fuori_dominio_422(self, client):
        _registra_admin(client)
        response = client.patch(f"{COEFF_URL}/iva/B-FINITURE", json={"iva_pct": "1.0"})
        assert response.status_code == 422

    def test_patch_iva_categoria_inesistente_404(self, client):
        _registra_admin(client)
        response = client.patch(f"{COEFF_URL}/iva/NON-ESISTE", json={"iva_pct": "0.1"})
        assert response.status_code == 404


class TestCrudExtra:
    def test_get_extra_lista(self, client):
        _registra_admin(client)
        response = client.get(f"{COEFF_URL}/extra")
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) >= 2
        for row in rows:
            assert "importo" in row
            assert "iva_pct" in row
            assert "attivo" in row

    def test_post_extra_crea_nuovo(self, client):
        _registra_admin(client)
        response = client.post(
            f"{COEFF_URL}/extra",
            json={"code": "NUOVO_EXTRA", "nome": "Nuovo extra", "importo": "150.00", "iva_pct": "0.22"},
        )
        assert response.status_code in (200, 201)
        body = response.json()
        assert body["code"] == "NUOVO_EXTRA"
        assert body["attivo"] is True

    def test_patch_extra_modifica_campi(self, client):
        _registra_admin(client)
        client.post(
            f"{COEFF_URL}/extra",
            json={"code": "EXTRA_PATCH", "nome": "Extra patch", "importo": "50.00", "iva_pct": "0.10"},
        )
        response = client.patch(f"{COEFF_URL}/extra/EXTRA_PATCH", json={"importo": "75.00", "attivo": False})
        assert response.status_code == 200
        body = response.json()
        assert float(body["importo"]) == 75.00
        assert body["attivo"] is False
        assert body["nome"] == "Extra patch"

    def test_patch_extra_inesistente_404(self, client):
        _registra_admin(client)
        response = client.patch(f"{COEFF_URL}/extra/NON-ESISTE", json={"importo": "1.00"})
        assert response.status_code == 404

    def test_delete_extra_elimina_solo_la_riga(self, client):
        _registra_admin(client)
        client.post(
            f"{COEFF_URL}/extra",
            json={"code": "EXTRA_DELETE", "nome": "Extra delete", "importo": "10.00", "iva_pct": "0.10"},
        )
        before = {r["code"] for r in client.get(f"{COEFF_URL}/extra").json()}

        response = client.delete(f"{COEFF_URL}/extra/EXTRA_DELETE")
        assert response.status_code in (200, 204)

        after = {r["code"] for r in client.get(f"{COEFF_URL}/extra").json()}
        assert "EXTRA_DELETE" not in after
        assert after == before - {"EXTRA_DELETE"}


class TestCrudCoeffPro:
    def test_get_coeff_pro_lista(self, client):
        _registra_admin(client)
        response = client.get(f"{COEFF_URL}/coeff-pro")
        assert response.status_code == 200
        rows = response.json()
        assert isinstance(rows, list)

    def test_patch_coeff_pro_modifica_valore(self, client):
        _registra_admin(client)
        rows = client.get(f"{COEFF_URL}/coeff-pro").json()
        if not rows:
            pytest.skip("nessun coefficiente_qta_voce nel seed di test")
        target = rows[0]

        response = client.patch(f"{COEFF_URL}/coeff-pro/{target['id']}", json={"valore": "3.5"})
        assert response.status_code == 200
        assert float(response.json()["valore"]) == 3.5

    def test_patch_coeff_pro_negativo_422(self, client):
        _registra_admin(client)
        rows = client.get(f"{COEFF_URL}/coeff-pro").json()
        if not rows:
            pytest.skip("nessun coefficiente_qta_voce nel seed di test")
        response = client.patch(f"{COEFF_URL}/coeff-pro/{rows[0]['id']}", json={"valore": "-1"})
        assert response.status_code == 422

    def test_patch_coeff_pro_inesistente_404(self, client):
        _registra_admin(client)
        response = client.patch(f"{COEFF_URL}/coeff-pro/999999", json={"valore": "1.0"})
        assert response.status_code == 404


class TestBaseEurMq:
    """GET in sola lettura di ListinoCategoria.base_eur_mq (T-04-41: mai
    `coefficiente_impresa` in questo schema)."""

    def test_get_base_espone_solo_base_eur_mq(self, client):
        _registra_admin(client)
        response = client.get(f"{COEFF_URL}/base")
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) >= 4
        for row in rows:
            assert "base_eur_mq" in row
            assert "coefficiente_impresa" not in row
