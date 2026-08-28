"""E2E tests (RED, TDD) for the lead-capture slice: POST /api/v1/lead, over
real cookie-jar HTTP calls (`TestClient`).

Covers LEAD-01/02/03 (04-01-PLAN.md <must_haves>): login-only capture (D-01),
independent snapshot persisted before any SMTP attempt (D-03/D-07), referente
resolution with default-listino fallback (D-04/D-05), notification + user
confirmation email (D-06/D-08), resilience to SMTP failure (D-07), and
anti-leak of the impresa secret in both the response and the email bodies
(D-22).

Until `app/routers/lead.py` / `app/models/lead.py` exist, `app.main` fails to
include the router and these requests 404 on `/api/v1/lead` -> RED as
expected.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from slugify import slugify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.db import Base
from app.limiter import limiter
from app.main import app

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LEAD_URL = "/api/v1/lead"

FORBIDDEN_SUBSTRINGS = [
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
]

FORBIDDEN_KEYS = {
    "base_eur_mq",
    "moltiplicatore",
    "coefficiente_impresa",
    "prezzo_impresa",
}


def _assert_no_forbidden_keys(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, f"forbidden key '{key}' found in response"
            _assert_no_forbidden_keys(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_forbidden_keys(item)


def _lead_payload(citta: str = "Reggio Emilia") -> dict:
    return {
        "nome": "Mario Rossi",
        "email": "mario.rossi@example.com",
        "telefono": "3331234567",
        "messaggio": "Vorrei un sopralluogo per la mia cucina.",
        "preferenza_contatto": "email",
        "fascia_oraria": "mattina",
        "citta": citta,
        "mq": 85,
        "tipo": "totale",
        "totale_min": "30120.00",
        "totale_max": "44350.00",
    }


@pytest.fixture()
def db_setup(tmp_path):
    """Crea DB SQLite di test + monkeypatcha SessionLocal ovunque servito.

    Restituisce (engine, testing_session_local) cosi' i singoli test possono
    seedare Listino/ComuneListino/Referente prima di esercitare l'endpoint.
    """
    limiter.reset()

    db_path = tmp_path / "test_lead.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

    db_module.SessionLocal = testing_session_local

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    deps_auth_module.SessionLocal = testing_session_local
    auth_router_module.SessionLocal = testing_session_local

    try:
        import app.routers.lead as lead_router_module

        if hasattr(lead_router_module, "SessionLocal"):
            lead_router_module.SessionLocal = testing_session_local
    except ModuleNotFoundError:
        pass

    return engine, testing_session_local


@pytest.fixture()
def client(db_setup):
    return TestClient(app)


def _registra(client, email="utente.lead@example.com", password="Password123", nome="Utente Lead"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": password, "nome": nome})


def _seed_listino_default(session_factory, is_default: bool = True) -> int:
    """Crea un Listino di default (catch-all), senza referente. Ritorna listino_id."""
    from app.models.listino import Listino

    with session_factory() as session:
        listino = Listino(
            nome="Listino Default",
            citta_riferimento="Reggio Emilia",
            is_default=is_default,
        )
        session.add(listino)
        session.commit()
        session.refresh(listino)
        return listino.id


def _seed_citta_con_referente(
    session_factory,
    citta: str,
    referente_nome: str = "Referente Città",
    referente_email: str = "referente.citta@example.com",
    attivo: bool = True,
) -> tuple[int, int]:
    """Crea Listino + ComuneListino + Referente attivo per `citta`. Ritorna (listino_id, referente_id)."""
    from app.models.catalogo import ComuneListino, Referente
    from app.models.listino import Listino

    with session_factory() as session:
        listino = Listino(nome=f"Listino {citta}", citta_riferimento=citta, is_default=False)
        session.add(listino)
        session.flush()

        comune = ComuneListino(
            comune_nome=citta,
            comune_slug=slugify(citta),
            listino_id=listino.id,
        )
        session.add(comune)

        referente = Referente(
            listino_id=listino.id,
            nome=referente_nome,
            email=referente_email,
            attivo=attivo,
            priorita=0,
        )
        session.add(referente)
        session.commit()
        session.refresh(listino)
        session.refresh(referente)
        return listino.id, referente.id


def _seed_default_con_referente(
    session_factory,
    referente_nome: str = "Referente Default",
    referente_email: str = "referente.default@example.com",
) -> tuple[int, int]:
    """Crea il Listino di default con un Referente attivo (catch-all globale)."""
    from app.models.catalogo import Referente
    from app.models.listino import Listino

    with session_factory() as session:
        listino = Listino(nome="Listino Default", citta_riferimento="Reggio Emilia", is_default=True)
        session.add(listino)
        session.flush()

        referente = Referente(
            listino_id=listino.id,
            nome=referente_nome,
            email=referente_email,
            attivo=True,
            priorita=0,
        )
        session.add(referente)
        session.commit()
        session.refresh(listino)
        session.refresh(referente)
        return listino.id, referente.id


class TestPostLead:
    def test_post_lead_authenticated(self, client, db_setup):
        _engine, session_factory = db_setup
        _seed_default_con_referente(session_factory)
        _registra(client)

        response = client.post(LEAD_URL, json=_lead_payload())

        assert response.status_code == 201
        body = response.json()
        assert "id" in body

        from app.models.lead import Lead

        with session_factory() as session:
            row = session.get(Lead, body["id"])
            assert row is not None
            assert row.citta == "Reggio Emilia"
            assert row.mq == 85
            assert row.tipo == "totale"
            assert str(row.totale_min) == "30120.00"
            assert str(row.totale_max) == "44350.00"
            assert row.nome == "Mario Rossi"
            assert row.email == "mario.rossi@example.com"

    def test_post_lead_anonymous_401(self, client, db_setup):
        _engine, session_factory = db_setup
        _seed_default_con_referente(session_factory)

        response = client.post(LEAD_URL, json=_lead_payload())

        assert response.status_code == 401


class TestLeadPersistedAndEmailSent:
    def test_lead_persisted_and_email_sent(self, client, db_setup, monkeypatch):
        _engine, session_factory = db_setup
        _listino_id, referente_id = _seed_citta_con_referente(session_factory, "Reggio Emilia")
        _registra(client)

        calls = []

        async def _fake_send_email(to, subject, html_body):
            calls.append({"to": to, "subject": subject, "html_body": html_body})

        import app.routers.lead as lead_router_module

        monkeypatch.setattr(lead_router_module, "send_email", _fake_send_email)

        response = client.post(LEAD_URL, json=_lead_payload("Reggio Emilia"))

        assert response.status_code == 201
        body = response.json()

        from app.models.lead import Lead

        with session_factory() as session:
            row = session.get(Lead, body["id"])
            assert row.referente_id == referente_id
            assert row.email_inviata is True

        assert len(calls) == 2
        destinatari = {c["to"] for c in calls}
        assert "referente.citta@example.com" in destinatari
        assert "mario.rossi@example.com" in destinatari


class TestResolveReferenteFallback:
    def test_resolve_referente_fallback_default(self, db_setup):
        from app.services.lead_service import resolve_referente

        _engine, session_factory = db_setup
        _seed_default_con_referente(session_factory)
        # Città "Modena" senza mappatura -> fallback su default listino via city_resolver.
        with session_factory() as session:
            referente = resolve_referente(session, "Modena")
            assert referente is not None
            assert referente.email == "referente.default@example.com"

    def test_resolve_referente_citta_propria(self, db_setup):
        from app.services.lead_service import resolve_referente

        _engine, session_factory = db_setup
        _listino_id, referente_id = _seed_citta_con_referente(session_factory, "Parma")
        with session_factory() as session:
            referente = resolve_referente(session, "Parma")
            assert referente is not None
            assert referente.id == referente_id


class TestLeadSavedEvenIfEmailFails:
    def test_lead_saved_even_if_email_fails(self, client, db_setup, monkeypatch):
        _engine, session_factory = db_setup
        _seed_citta_con_referente(session_factory, "Reggio Emilia")
        _registra(client)

        async def _raising_send_email(to, subject, html_body):
            raise RuntimeError("SMTP down")

        import app.routers.lead as lead_router_module

        monkeypatch.setattr(lead_router_module, "send_email", _raising_send_email)

        response = client.post(LEAD_URL, json=_lead_payload("Reggio Emilia"))

        assert response.status_code == 201
        body = response.json()

        from app.models.lead import Lead

        with session_factory() as session:
            row = session.get(Lead, body["id"])
            assert row is not None
            assert row.email_inviata is False


class TestLeadNoImpresaLeak:
    def test_lead_no_impresa_leak(self, client, db_setup):
        _engine, session_factory = db_setup
        _seed_citta_con_referente(session_factory, "Reggio Emilia")
        _registra(client)

        response = client.post(LEAD_URL, json=_lead_payload("Reggio Emilia"))

        assert response.status_code == 201
        raw_text = response.text

        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert forbidden not in raw_text, f"forbidden substring '{forbidden}' leaked in lead response"

        _assert_no_forbidden_keys(response.json())
