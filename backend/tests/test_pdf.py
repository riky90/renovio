"""E2E tests (RED, TDD) for GET /me/stime/{id}/pdf — the Free branded PDF
download (PDF-01, 02-08-PLAN.md).

Covers: content-type/filename (D-12), anti-leak of the impresa secret in the
rendered PDF bytes (D-13, re-verified per 02-UI-SPEC.md §H "domain guard"),
per-user ownership (T-08-02, 404 not 403 — anti-IDOR, same pattern as
02-07/test_stime_salvate.py), 401 without a session (T-08-04), and a static
guard that `pdf_service` never imports `EstimationService` (T-08-03,
D-09/Pitfall 5 — the PDF must render ONLY the frozen snapshot, never
recompute).

Until `app/services/pdf_service.py` and the `/me/stime/{id}/pdf` endpoint
exist, the byte-generating tests fail (404) as expected -> RED.

WeasyPrint requires native GTK/Pango/Cairo libraries not present on Windows
dev by default (02-RESEARCH.md Pitfall 3). Tests that need REAL PDF bytes
are skipped when the native lib is unavailable; ownership/401/anti-import
guards stay active regardless (they don't require a successful render).
"""

from __future__ import annotations

import importlib.util
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LOGOUT_URL = "/api/v1/auth/logout"
STIME_URL = "/api/v1/me/stime"

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
    """A StimaResponse-shaped payload, as returned by POST /api/v1/stima."""
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
            {
                "code": "finiture",
                "nome": "Finiture",
                "imponibile_min": "8000.00",
                "imponibile_max": "12000.00",
                "iva_pct": "0.22",
                "iva_min": "1760.00",
                "iva_max": "2640.00",
                "totale_min": "9760.00",
                "totale_max": "14640.00",
            },
            {
                "code": "serramenti",
                "nome": "Serramenti",
                "imponibile_min": "5000.00",
                "imponibile_max": "7000.00",
                "iva_pct": "0.10",
                "iva_min": "500.00",
                "iva_max": "700.00",
                "totale_min": "5500.00",
                "totale_max": "7700.00",
            },
            {
                "code": "prodotti",
                "nome": "Prodotti",
                "imponibile_min": "3000.00",
                "imponibile_max": "4500.00",
                "iva_pct": "0.10",
                "iva_min": "300.00",
                "iva_max": "450.00",
                "totale_min": "3300.00",
                "totale_max": "4950.00",
            },
        ],
        "extra": [
            {"code": "cse", "nome": "CSE/CSP", "importo": "1500.00", "iva_pct": "0.22"},
            {"code": "pratiche", "nome": "Pratiche", "importo": "800.00", "iva_pct": "0.22"},
        ],
        "totale": {
            "imponibile_min": "26000.00",
            "imponibile_max": "38500.00",
            "iva_min": "4120.00",
            "iva_max": "5850.00",
            "totale_min": "30120.00",
            "totale_max": "44350.00",
        },
    }


@pytest.fixture()
def client(monkeypatch, tmp_path):
    # slowapi Limiter is a process-wide singleton (see 02-03-SUMMARY.md) —
    # reset it so /registrati's 5/minute cap doesn't leak between tests.
    limiter.reset()

    db_path = tmp_path / "test_pdf.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    import app.routers.stime_salvate as stime_salvate_router_module

    monkeypatch.setattr(stime_salvate_router_module, "SessionLocal", testing_session_local)

    return TestClient(app)


def _registra(client, email="utente.a@example.com", password="Password123", nome="Utente A"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


def _salva_stima(client) -> int:
    created = client.post(STIME_URL, json=_stima_payload())
    assert created.status_code == 201
    return created.json()["id"]


class TestPdfDownload:
    @skip_without_weasyprint
    def test_pdf_download_ritorna_content_type_e_filename(self, client):
        _registra(client)
        stima_id = _salva_stima(client)

        response = client.get(f"{STIME_URL}/{stima_id}/pdf")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition
        assert "stima-ristrutturazione-" in content_disposition
        assert response.content.startswith(b"%PDF")

    @skip_without_weasyprint
    def test_pdf_non_contiene_dati_impresa(self, client):
        _registra(client)
        stima_id = _salva_stima(client)

        response = client.get(f"{STIME_URL}/{stima_id}/pdf")
        assert response.status_code == 200

        raw_text = response.content.decode("latin-1")
        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert forbidden not in raw_text, f"forbidden substring '{forbidden}' leaked in PDF bytes"


class TestPdfOwnershipEAuth:
    def test_utente_b_non_puo_scaricare_pdf_di_utente_a(self, client):
        _registra(client, email="utente.a2@example.com")
        stima_id = _salva_stima(client)
        client.post(LOGOUT_URL)

        _registra(client, email="utente.b@example.com")
        response = client.get(f"{STIME_URL}/{stima_id}/pdf")

        assert response.status_code == 404

    def test_pdf_senza_sessione_ritorna_401(self, client):
        response = client.get(f"{STIME_URL}/999/pdf")

        assert response.status_code == 401


class TestPdfServiceNonRicalcola:
    def test_pdf_service_non_importa_estimation_service(self):
        """Static guard (T-08-03, D-09/Pitfall 5): the PDF render path must
        read ONLY the frozen `risultato_json` snapshot, never recompute via
        `EstimationService`."""
        import app.services.pdf_service as pdf_service_module
        import inspect

        source = inspect.getsource(pdf_service_module)
        assert "EstimationService" not in source


class _FakeStima:
    def __init__(self, risultato_json, budget_eur=None):
        from datetime import datetime

        self.risultato_json = risultato_json
        self.budget_eur = budget_eur
        self.citta = "Reggio Emilia"
        self.created_at = datetime(2026, 9, 29)


class _FakeUser:
    nome = "Utente Test"


def _snapshot_render() -> dict:
    payload = _stima_payload()
    payload["totale"] = {
        "imponibile_min": "50000.00",
        "imponibile_max": "55000.00",
        "iva_min": "0.00",
        "iva_max": "0.00",
        "totale_min": "50000.00",
        "totale_max": "55000.00",
    }
    return payload


class TestPdfRenderHtml:
    """Rendering HTML dallo snapshot: non richiede WeasyPrint."""

    def test_barra_proporzionale_e_riepilogo(self):
        from app.services.pdf_service import PdfService

        html = PdfService.render_html(_FakeStima(_stima_payload()), _FakeUser())
        assert "Imponibile lavori" in html
        assert "Totale IVA inclusa" in html
        assert "IVA 10%" in html
        assert "IVA 22%" in html
        assert "€/m²" in html
        assert "(IVA esclusa)" in html
        assert "% del totale" in html
        assert "Costi extra" in html
        assert "text-transform" in html  # preesistente
        assert not re.search(r"(?<!text-)transform\s*:", html)
        assert "calc(" not in html

    def test_left_pct_coerente_con_scala_barra(self):
        from app.services.pdf_service import PdfService

        html = PdfService.render_html(_FakeStima(_snapshot_render()), _FakeUser())
        assert "left:75.76%" in html.replace(" ", "")

    def test_snapshot_pre_fase_si_rende(self):
        from app.services.pdf_service import PdfService

        snap = _stima_payload()
        snap.pop("extra")
        snap["input"].pop("mq")
        html = PdfService.render_html(_FakeStima(snap), _FakeUser())
        assert "Costi extra" not in html
        assert "Totale IVA inclusa" in html

    def test_extra_vuoti_nessuna_riga(self):
        from app.services.pdf_service import PdfService

        snap = _stima_payload()
        snap["extra"] = []
        html = PdfService.render_html(_FakeStima(snap), _FakeUser())
        assert "Costi extra" not in html


class TestPdfBudget:
    def test_budget_sotto_il_minimo_tacca_e_riquadro(self):
        from app.services.pdf_service import PdfService
        from app.services.risultato import scala_barra

        snap = _snapshot_render()
        html = PdfService.render_html(_FakeStima(snap, budget_eur=40000), _FakeUser())
        assert "Il tuo budget" in html
        assert "La stima supera il tuo budget" in html
        assert "Il budget non cambia il prezzo della stima." in html
        pct = scala_barra("50000", "55000", 40000).budget_pct
        assert f"left:{pct:.2f}%" in html.replace(" ", "")
        box = html[html.index('class="avviso-budget'):]
        box = box[: box.index("avviso-nota")]
        for vietato in ("<input", "<button", "href="):
            assert vietato not in box

    def test_righe_confronto_dallo_snapshot(self):
        from app.services.pdf_service import PdfService

        snap = _snapshot_render()
        snap["confronto_finiture"] = {
            "livello_code": "base",
            "livello_nome": "Medie",
            "totale_min": "45000.00",
            "totale_max": "50000.00",
        }
        html = PdfService.render_html(_FakeStima(snap, budget_eur=40000), _FakeUser())
        assert "Ora (IVA inclusa)" in html
        assert "Con finiture medie" in html

    def test_senza_budget_nessuna_sezione(self):
        from app.services.pdf_service import PdfService

        html = PdfService.render_html(_FakeStima(_snapshot_render()), _FakeUser())
        assert "Il tuo budget" not in html
        assert 'class="avviso-budget' not in html

    def test_snapshot_pre_fase_senza_budget(self):
        from app.services.pdf_service import PdfService

        snap = _stima_payload()
        snap.pop("extra")
        html = PdfService.render_html(_FakeStima(snap), _FakeUser())
        assert "Il tuo budget" not in html
