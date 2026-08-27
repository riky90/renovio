"""Tests for GET /me/stime/{id}/pdf-pro — il PDF Pro dettagliato (PDF-02,
03-04-PLAN.md Task 2).

Fixture: engine-swap + seed reale (come `test_dettaglio_pro_paywall.py`),
serve perche' il pdf-pro calcola on-demand dal listino via
`DettaglioProService.compute()`, non da uno snapshot congelato.

Copre:
- matrice paywall SEMPRE attiva (non byte-generating, non richiede GTK3):
  anonimo->401, Free->403, stima altrui->404 (anti-IDOR)
- test di PARITA' non-byte: `_compute_dettaglio()` (usato dal pdf-pro) e
  `DettaglioProService.compute()` (usato dal GET JSON) con gli stessi input
  producono lo stesso risultato numerico — schermata e PDF non possono
  divergere (03-RESEARCH.md Pitfall 2)
- test byte-generating (skip-graceful senza GTK3, stesso probe di
  `test_pdf.py`): content-type/filename + anti-leak sui bytes/HTML del PDF
  Pro, estendendo la lista FORBIDDEN gia' usata da `test_pdf.py`/
  `test_no_leak.py`
"""

from __future__ import annotations

import importlib.util

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from scripts.seed import load_seed_data, seed

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LOGOUT_URL = "/api/v1/auth/logout"
STIME_URL = "/api/v1/me/stime"
ATTIVA_PRO_URL = "/api/v1/me/pro/attiva"

FORBIDDEN_SUBSTRINGS = [
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
]


def _weasyprint_native_lib_available() -> bool:
    """True if WeasyPrint can actually load its native GTK/Pango/Cairo libs
    (not just if the `weasyprint` Python package is importable)."""
    if importlib.util.find_spec("weasyprint") is None:
        return False
    try:
        import weasyprint  # noqa: F401
    except OSError:
        return False
    return True


WEASYPRINT_NATIVE_AVAILABLE = _weasyprint_native_lib_available()

skip_without_weasyprint = pytest.mark.skipif(
    not WEASYPRINT_NATIVE_AVAILABLE,
    reason=(
        "WeasyPrint native GTK/Pango/Cairo runtime not available on this "
        "machine (02-RESEARCH.md Pitfall 3) — install GTK3 runtime for "
        "Windows or run inside Docker/WSL2 to exercise real PDF rendering."
    ),
)


def _stima_payload() -> dict:
    """A StimaResponse-shaped payload con citta/mq/tipo reali che risolvono
    sul listino RE seedato (stesso shape di test_dettaglio_pro_paywall.py)."""
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

    db_path = tmp_path / "test_pdf_pro.db"
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

    return TestClient(app), testing_session_local


def _registra(client, email="utente.a@example.com", password="Password123", nome="Utente A"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


def _crea_stima_pro(client) -> int:
    """Registra un utente Pro e crea una stima salvata; ritorna lo stima_id."""
    _registra(client)
    client.post(ATTIVA_PRO_URL)
    created = client.post(STIME_URL, json=_stima_payload())
    return created.json()["id"]


class TestPaywallMatrix:
    def test_anonimo_401(self, client):
        c, _ = client
        response = c.get(f"{STIME_URL}/1/pdf-pro")
        assert response.status_code == 401

    def test_free_autenticato_403(self, client):
        c, _ = client
        _registra(c)
        created = c.post(STIME_URL, json=_stima_payload())
        stima_id = created.json()["id"]

        response = c.get(f"{STIME_URL}/{stima_id}/pdf-pro")

        assert response.status_code == 403
        assert response.json()["detail"] == "Funzione riservata agli utenti Pro"

    def test_stima_altrui_404(self, client):
        c, _ = client
        stima_id = _crea_stima_pro(c)
        c.post(LOGOUT_URL)

        _registra(c, email="utente.b@example.com")
        c.post(ATTIVA_PRO_URL)

        response = c.get(f"{STIME_URL}/{stima_id}/pdf-pro")

        assert response.status_code == 404


class TestParitaSchermataPdf:
    def test_compute_dettaglio_usato_dal_pdf_pro_e_identico_al_get_json(self, client):
        """Parita' by-construction (Pitfall 2): stesso input -> stesso
        risultato numerico, sia passando dal GET JSON sia dalla funzione
        interna condivisa usata dal pdf-pro."""
        c, session_factory = client
        stima_id = _crea_stima_pro(c)

        response = c.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")
        assert response.status_code == 200
        json_body = response.json()

        import app.routers.dettaglio_pro as dettaglio_pro_router_module
        from app.models.stima_salvata import StimaSalvata

        with session_factory() as session:
            row = session.query(StimaSalvata).filter_by(id=stima_id).one()
            result, risposte = dettaglio_pro_router_module._compute_dettaglio(session, row)
            pdf_out = dettaglio_pro_router_module._to_out(result, risposte)

        assert pdf_out.model_dump(mode="json") == json_body


class TestPdfProDownload:
    @skip_without_weasyprint
    def test_pdf_pro_ritorna_content_type_e_filename(self, client):
        c, _ = client
        stima_id = _crea_stima_pro(c)

        response = c.get(f"{STIME_URL}/{stima_id}/pdf-pro")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition
        assert "dettaglio" in content_disposition
        assert response.content.startswith(b"%PDF")

    @skip_without_weasyprint
    def test_pdf_pro_non_contiene_dati_impresa(self, client):
        c, _ = client
        stima_id = _crea_stima_pro(c)

        response = c.get(f"{STIME_URL}/{stima_id}/pdf-pro")
        assert response.status_code == 200

        raw_text = response.content.decode("latin-1")
        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert forbidden not in raw_text, f"forbidden substring '{forbidden}' leaked in PDF Pro bytes"


class TestPdfServiceRenderProRicalcolaLive:
    def test_render_pro_non_richiama_direttamente_estimation_service(self):
        """Static guard analogo a test_pdf.py: render_pro() non deve mai
        importare/richiamare il motore Free (D-01), coerente con l'intero
        modulo pdf_service.py."""
        import app.services.pdf_service as pdf_service_module
        import inspect

        source = inspect.getsource(pdf_service_module)
        assert "EstimationService" not in source
