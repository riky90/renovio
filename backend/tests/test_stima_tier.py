"""`stima.tier` — il piano si congela al salvataggio (migrazione 0009).

Prima di questa colonna l'accesso al dettaglio Pro dipendeva solo
dall'abbonamento CORRENTE: appena un utente si abbonava, tutte le sue stime
Free storiche si comportavano da Pro. Qui si verifica che non succeda piu'.

Fixture: engine-swap + client, stesso pattern di
`test_dettaglio_pro_paywall.py` (seed reale caricato — il dettaglio Pro
calcola on-demand dal listino, non da uno snapshot).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from scripts.seed import load_seed_data, seed
from tests.test_pdf import skip_without_weasyprint

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LOGOUT_URL = "/api/v1/auth/logout"
STIME_URL = "/api/v1/me/stime"
ATTIVA_PRO_URL = "/api/v1/me/pro/attiva"

MSG_STIMA_FREE = (
    "Questa stima e' stata creata con il piano Free. "
    "Rifalla in versione Pro per il dettaglio voce per voce."
)


def _stima_payload() -> dict:
    return {
        "input": {"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"},
        "fallback": False,
        "disclaimer": None,
        "valuta": "EUR",
        "categorie": [
            {
                "code": "edile",
                "nome": "Edile",
                "imponibile_min": "10000.00",
                "imponibile_max": "15000.00",
                "iva_pct": "0.10",
                "iva_min": "1000.00",
                "iva_max": "1500.00",
                "totale_min": "11000.00",
                "totale_max": "16500.00",
            },
        ],
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
def client(monkeypatch, tmp_path):
    limiter.reset()

    db_path = tmp_path / "test_stima_tier.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

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


def _registra(client, email="utente.tier@example.com", password="Password123", nome="Utente Tier"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


class TestTierAlSalvataggio:
    def test_utente_free_salva_stima_free(self, client):
        _registra(client)
        stima_id = client.post(STIME_URL, json=_stima_payload()).json()["id"]

        assert client.get(f"{STIME_URL}/{stima_id}").json()["tier"] == "free"

    def test_utente_pro_salva_stima_pro(self, client):
        _registra(client)
        client.post(ATTIVA_PRO_URL)
        stima_id = client.post(STIME_URL, json=_stima_payload()).json()["id"]

        assert client.get(f"{STIME_URL}/{stima_id}").json()["tier"] == "pro"

    def test_tier_esposto_nella_lista(self, client):
        _registra(client)
        client.post(STIME_URL, json=_stima_payload())  # free
        client.post(ATTIVA_PRO_URL)
        client.post(STIME_URL, json=_stima_payload())  # pro

        tiers = [item["tier"] for item in client.get(STIME_URL).json()]

        assert sorted(tiers) == ["free", "pro"]


class TestStimaFreeNonDiventaPro:
    """Il cuore della regressione: l'utente si abbona DOPO aver salvato."""

    def _stima_free_poi_abbonato(self, client) -> int:
        _registra(client)
        stima_id = client.post(STIME_URL, json=_stima_payload()).json()["id"]
        client.post(ATTIVA_PRO_URL)  # diventa Pro solo adesso
        return stima_id

    def test_dettaglio_pro_403(self, client):
        stima_id = self._stima_free_poi_abbonato(client)

        response = client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")

        assert response.status_code == 403
        assert response.json()["detail"] == MSG_STIMA_FREE

    def test_pdf_pro_403(self, client):
        stima_id = self._stima_free_poi_abbonato(client)

        assert client.get(f"{STIME_URL}/{stima_id}/pdf-pro").status_code == 403

    def test_post_risposte_403(self, client):
        stima_id = self._stima_free_poi_abbonato(client)

        response = client.post(
            f"{STIME_URL}/{stima_id}/dettaglio-pro/risposte",
            json={"bagni": 1, "porte": 1, "condizionatori": 1},
        )

        assert response.status_code == 403

    def test_la_stima_free_resta_leggibile(self, client):
        """Il 403 riguarda SOLO il dettaglio Pro: la stima Free resta
        consultabile come sempre."""
        stima_id = self._stima_free_poi_abbonato(client)

        assert client.get(f"{STIME_URL}/{stima_id}").status_code == 200

    @skip_without_weasyprint
    def test_il_pdf_free_resta_scaricabile(self, client):
        """Il PDF Free non passa dal gate sul tier (vive in
        `routers/stime_salvate.py`) e continua a funzionare."""
        stima_id = self._stima_free_poi_abbonato(client)

        assert client.get(f"{STIME_URL}/{stima_id}/pdf").status_code == 200

    def test_stima_nuova_dopo_upgrade_e_pro(self, client):
        """L'upgrade vale da qui in avanti: la stima successiva e' Pro."""
        self._stima_free_poi_abbonato(client)
        nuova_id = client.post(STIME_URL, json=_stima_payload()).json()["id"]

        assert client.get(f"{STIME_URL}/{nuova_id}/dettaglio-pro").status_code == 200


class TestGateOrtogonali:
    def test_stima_pro_ma_abbonamento_scaduto_403(self, client):
        """`require_pro` (abbonamento corrente) e il tier (piano d'origine)
        sono due gate distinti: qui casca il primo."""
        _registra(client)
        client.post(ATTIVA_PRO_URL)
        stima_id = client.post(STIME_URL, json=_stima_payload()).json()["id"]

        from datetime import datetime, timedelta, timezone

        from app.models.subscription import Subscription

        with db_module.SessionLocal() as s:
            sub = s.query(Subscription).one()
            sub.scaduta_il = datetime.now(timezone.utc) - timedelta(days=1)
            s.commit()

        response = client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")

        assert response.status_code == 403
        assert response.json()["detail"] == "Funzione riservata agli utenti Pro"

    def test_stima_altrui_resta_404_non_403(self, client):
        """L'anti-IDOR non deve regredire: il gate sul tier gira DOPO quello
        di ownership, quindi l'esistenza di una riga altrui non trapela."""
        _registra(client)
        stima_id = client.post(STIME_URL, json=_stima_payload()).json()["id"]  # free, utente A
        client.post(LOGOUT_URL)

        _registra(client, email="utente.tier.b@example.com")
        client.post(ATTIVA_PRO_URL)

        assert client.get(f"{STIME_URL}/{stima_id}/dettaglio-pro").status_code == 404
