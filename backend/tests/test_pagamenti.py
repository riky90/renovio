"""Pagamento del Pro con Stripe (abbonamento mensile e annuale).

Stripe non si chiama mai: `services.pagamenti._client` e' sostituito da un
finto client che registra le richieste e risponde con oggetti in forma
Stripe. I webhook invece sono firmati davvero (HMAC SHA-256 come fa Stripe) e
passano dalla verifica vera di `stripe.Webhook.construct_event`.

Cosa va dimostrato:

  1. SENZA CHIAVE i pagamenti sono spenti e resta l'attivazione dimostrativa;
     CON LA CHIAVE l'attivazione dimostrativa e' chiusa (mai un Pro gratis
     con i pagamenti attivi).
  2. I PIANI vengono dai prezzi Stripe (lookup key), non dal codice.
  3. IL CHECKOUT chiede l'accettazione delle condizioni e la richiesta di
     attivazione immediata, lega la sessione
     all'utente e riusa il cliente Stripe.
  4. IL WEBHOOK verifica la firma, attiva il Pro, segue disdetta e fine
     dell'abbonamento, ed e' idempotente.
  5. LA CONFERMA al ritorno dal pagamento attiva il Pro solo per la sessione
     dell'utente stesso.
  6. NESSUN identificativo Stripe esce verso il client.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.subscription import Subscription
from app.services import pagamenti
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
ME_URL = "/api/v1/auth/me"
PIANI_URL = "/api/v1/pro/piani"
CHECKOUT_URL = "/api/v1/pro/checkout"
CONFERMA_URL = "/api/v1/pro/checkout/conferma"
PORTALE_URL = "/api/v1/pro/portale"
ABBONAMENTO_URL = "/api/v1/me/abbonamento"
WEBHOOK_URL = "/api/v1/stripe/webhook"
ATTIVA_DEMO_URL = "/api/v1/me/pro/attiva"

SEGRETO_WEBHOOK = "whsec_test_segreto"
FINE_PERIODO = int((datetime.now(timezone.utc) + timedelta(days=365)).timestamp())


class FintoStripe:
    """Il minimo di `StripeClient.v1` che usa `services.pagamenti`."""

    def __init__(self):
        self.richieste: list[tuple[str, dict]] = []
        self.abbonamenti: dict[str, dict] = {}
        self.checkout: dict[str, dict] = {}
        self._n = 0
        v1 = SimpleNamespace(
            prices=SimpleNamespace(list=self._prezzi),
            customers=SimpleNamespace(create=self._cliente),
            checkout=SimpleNamespace(
                sessions=SimpleNamespace(create=self._crea_checkout, retrieve=self._leggi_checkout)
            ),
            billing_portal=SimpleNamespace(sessions=SimpleNamespace(create=self._portale)),
            subscriptions=SimpleNamespace(retrieve=self._leggi_abbonamento),
        )
        self.v1 = v1

    def _id(self, prefisso: str) -> str:
        self._n += 1
        return f"{prefisso}_{self._n}"

    def _prezzi(self, params=None, options=None):
        self.richieste.append(("prices.list", params))
        return {
            "data": [
                {
                    "id": "price_annuale",
                    "lookup_key": settings.STRIPE_LOOKUP_KEY_ANNUALE,
                    "unit_amount": 2900,
                    "currency": "eur",
                    "recurring": {"interval": "year"},
                    "product": {"name": "Renovio Pro"},
                },
                {
                    "id": "price_mensile",
                    "lookup_key": settings.STRIPE_LOOKUP_KEY_MENSILE,
                    "unit_amount": 300,
                    "currency": "eur",
                    "recurring": {"interval": "month"},
                    "product": {"name": "Renovio Pro"},
                },
            ]
        }

    def _cliente(self, params=None, options=None):
        self.richieste.append(("customers.create", params))
        return {"id": self._id("cus")}

    def _crea_checkout(self, params=None, options=None):
        self.richieste.append(("checkout.sessions.create", params))
        cs_id = self._id("cs")
        self.checkout[cs_id] = {
            "id": cs_id,
            "client_reference_id": params["client_reference_id"],
            "customer": params["customer"],
            "status": "open",
            "subscription": None,
            "params": params,
        }
        return {"id": cs_id, "url": f"https://checkout.stripe.test/{cs_id}"}

    def _leggi_checkout(self, cs_id, params=None, options=None):
        return self.checkout[cs_id]

    def _portale(self, params=None, options=None):
        self.richieste.append(("billing_portal.sessions.create", params))
        return {"url": "https://billing.stripe.test/portale"}

    def _leggi_abbonamento(self, sub_id, params=None, options=None):
        return self.abbonamenti[sub_id]

    # --- aiuti per i test: Stripe che "completa" un pagamento -----------

    def completa(self, cs_id: str, *, piano: str = "annuale", status: str = "active") -> str:
        cs = self.checkout[cs_id]
        sub_id = self._id("sub")
        lookup = settings.STRIPE_LOOKUP_KEY_ANNUALE if piano == "annuale" else settings.STRIPE_LOOKUP_KEY_MENSILE
        self.abbonamenti[sub_id] = {
            "id": sub_id,
            "customer": cs["customer"],
            "status": status,
            "cancel_at_period_end": False,
            "metadata": cs["params"]["subscription_data"]["metadata"],
            # API 2025+: la fine del periodo sta sulle voci.
            "items": {"data": [{"current_period_end": FINE_PERIODO, "price": {"lookup_key": lookup}}]},
        }
        cs["status"] = "complete"
        cs["subscription"] = sub_id
        return sub_id


@pytest.fixture()
def finto_stripe(monkeypatch):
    finto = FintoStripe()
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_finta")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SEGRETO_WEBHOOK)
    monkeypatch.setattr(pagamenti, "_client", lambda: finto)
    pagamenti.svuota_cache_piani()
    yield finto
    pagamenti.svuota_cache_piani()


@pytest.fixture()
def db_session_local(monkeypatch, tmp_path):
    limiter.reset()
    engine = create_engine(f"sqlite:///{tmp_path / 'pagamenti.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_local = sessione_di_test(engine)
    import app.dependencies.auth as deps_auth
    import app.routers.auth as auth_router
    import app.routers.pagamenti as pagamenti_router
    import app.routers.subscription as subscription_router

    for modulo in (db_module, deps_auth, auth_router, pagamenti_router, subscription_router):
        monkeypatch.setattr(modulo, "SessionLocal", session_local)
    return session_local


@pytest.fixture()
def client(db_session_local):
    return TestClient(app)


def _registra(client, email="pro@example.com") -> int:
    r = client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": "Pro"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _evento(tipo: str, oggetto: dict) -> tuple[bytes, dict]:
    payload = json.dumps(
        {"id": f"evt_{tipo}", "object": "event", "type": tipo, "data": {"object": oggetto}}
    ).encode()
    t = int(time.time())
    firma = hmac.new(SEGRETO_WEBHOOK.encode(), f"{t}.".encode() + payload, hashlib.sha256).hexdigest()
    return payload, {"stripe-signature": f"t={t},v1={firma}", "content-type": "application/json"}


def _paga(client, finto, *, piano="annuale") -> str:
    r = client.post(CHECKOUT_URL, json={"piano": piano, "accetta_condizioni": True, "accetta_esecuzione_immediata": True})
    assert r.status_code == 200, r.text
    cs_id = r.json()["url"].rsplit("/", 1)[1]
    sub_id = finto.completa(cs_id, piano=piano)
    payload, headers = _evento("checkout.session.completed", {"id": cs_id, "subscription": sub_id})
    assert client.post(WEBHOOK_URL, content=payload, headers=headers).status_code == 200
    return sub_id


# --- 1. interruttore -----------------------------------------------------------


def test_senza_chiave_pagamenti_spenti_e_demo_attiva(client, monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")
    assert client.get(PIANI_URL).json() == {"pagamenti_attivi": False, "piani": []}
    _registra(client)
    assert client.post(CHECKOUT_URL, json={"piano": "annuale", "accetta_condizioni": True, "accetta_esecuzione_immediata": True}).status_code == 503
    assert client.post(ATTIVA_DEMO_URL).status_code == 200
    assert client.get(ME_URL).json()["pro"] is True


def test_con_la_chiave_la_demo_e_chiusa(client, finto_stripe):
    _registra(client)
    assert client.post(ATTIVA_DEMO_URL).status_code == 403
    assert client.get(ME_URL).json()["pro"] is False


# --- 2. piani --------------------------------------------------------------------


def test_piani_dai_prezzi_stripe(client, finto_stripe):
    corpo = client.get(PIANI_URL).json()
    assert corpo["pagamenti_attivi"] is True
    assert [(p["code"], p["importo"], p["intervallo"]) for p in corpo["piani"]] == [
        ("mensile", "3", "month"),
        ("annuale", "29", "year"),
    ]
    _, params = finto_stripe.richieste[0]
    assert set(params["lookup_keys"]) == {"renovio_pro_mensile", "renovio_pro_annuale"}
    assert "price_" not in json.dumps(corpo)


# --- 3. checkout -----------------------------------------------------------------


def test_checkout_richiede_login_e_consenso(client, finto_stripe):
    assert client.post(CHECKOUT_URL, json={"piano": "annuale", "accetta_condizioni": True, "accetta_esecuzione_immediata": True}).status_code == 401
    _registra(client)
    assert client.post(CHECKOUT_URL, json={"piano": "annuale", "accetta_condizioni": True, "accetta_esecuzione_immediata": False}).status_code == 422
    assert client.post(CHECKOUT_URL, json={"piano": "annuale", "accetta_condizioni": False, "accetta_esecuzione_immediata": True}).status_code == 422
    assert client.post(CHECKOUT_URL, json={"piano": "settimanale", "accetta_condizioni": True, "accetta_esecuzione_immediata": True}).status_code == 422


def test_checkout_lega_la_sessione_all_utente_e_riusa_il_cliente(client, finto_stripe):
    user_id = _registra(client)
    for _ in range(2):
        r = client.post(CHECKOUT_URL, json={"piano": "mensile", "accetta_condizioni": True, "accetta_esecuzione_immediata": True})
        assert r.status_code == 200
        assert r.json()["url"].startswith("https://checkout.stripe.test/")
    creati = [p for nome, p in finto_stripe.richieste if nome == "customers.create"]
    assert len(creati) == 1 and creati[0]["email"] == "pro@example.com"
    sessioni = [p for nome, p in finto_stripe.richieste if nome == "checkout.sessions.create"]
    params = sessioni[0]
    assert params["mode"] == "subscription"
    assert params["client_reference_id"] == str(user_id)
    assert params["line_items"] == [{"price": "price_mensile", "quantity": 1}]
    assert params["subscription_data"]["metadata"]["user_id"] == str(user_id)
    assert "condizioni_accettate_il" in params["metadata"]
    assert "attivazione_immediata_richiesta_il" in params["metadata"]
    assert "{CHECKOUT_SESSION_ID}" in params["success_url"]


# --- 4. webhook -------------------------------------------------------------------


def test_webhook_con_firma_sbagliata(client, finto_stripe):
    payload, headers = _evento("customer.subscription.updated", {"id": "sub_x"})
    headers["stripe-signature"] = headers["stripe-signature"].replace("v1=", "v1=00")
    assert client.post(WEBHOOK_URL, content=payload, headers=headers).status_code == 400


def test_webhook_attiva_il_pro_annuale(client, finto_stripe):
    _registra(client)
    _paga(client, finto_stripe, piano="annuale")
    assert client.get(ME_URL).json()["pro"] is True
    abb = client.get(ABBONAMENTO_URL).json()
    assert abb["pro"] is True and abb["piano_code"] == "annuale"
    assert abb["rinnovo_automatico"] is True and abb["gestibile"] is True
    scade = datetime.fromisoformat(abb["scade_il"]).replace(tzinfo=timezone.utc)
    atteso = datetime.fromtimestamp(FINE_PERIODO, tz=timezone.utc)
    assert abs((scade - atteso).total_seconds()) < 2


def test_disdetta_resta_pro_fino_a_fine_periodo_poi_no(client, finto_stripe):
    _registra(client)
    sub_id = _paga(client, finto_stripe)

    finto_stripe.abbonamenti[sub_id]["cancel_at_period_end"] = True
    payload, headers = _evento("customer.subscription.updated", {"id": sub_id})
    client.post(WEBHOOK_URL, content=payload, headers=headers)
    abb = client.get(ABBONAMENTO_URL).json()
    assert abb["pro"] is True and abb["rinnovo_automatico"] is False

    finto_stripe.abbonamenti[sub_id].update(status="canceled", ended_at=int(time.time()) - 5)
    payload, headers = _evento("customer.subscription.deleted", {"id": sub_id})
    client.post(WEBHOOK_URL, content=payload, headers=headers)
    assert client.get(ME_URL).json()["pro"] is False
    assert client.get(ABBONAMENTO_URL).json()["stato"] == "cancellato"


def test_webhook_idempotente_e_eventi_ignorati(client, finto_stripe, db_session_local):
    _registra(client)
    sub_id = _paga(client, finto_stripe)
    payload, headers = _evento("customer.subscription.updated", {"id": sub_id})
    for _ in range(3):
        assert client.post(WEBHOOK_URL, content=payload, headers=headers).json()["esito"] == "applicato"
    payload, headers = _evento("payment_intent.created", {"id": "pi_1"})
    assert client.post(WEBHOOK_URL, content=payload, headers=headers).json()["esito"] == "ignorato"
    with db_session_local() as s:
        assert s.query(Subscription).count() == 1


def test_rinnovo_fallito_e_poi_pagato(client, finto_stripe):
    _registra(client)
    sub_id = _paga(client, finto_stripe, piano="mensile")
    finto_stripe.abbonamenti[sub_id]["status"] = "past_due"
    payload, headers = _evento("invoice.payment_failed", {"id": "in_1", "subscription": sub_id})
    client.post(WEBHOOK_URL, content=payload, headers=headers)
    assert client.get(ME_URL).json()["pro"] is True  # fino a fine periodo
    finto_stripe.abbonamenti[sub_id]["status"] = "unpaid"
    payload, headers = _evento(
        "invoice.payment_failed",
        {"id": "in_2", "parent": {"subscription_details": {"subscription": sub_id}}},
    )
    client.post(WEBHOOK_URL, content=payload, headers=headers)
    assert client.get(ME_URL).json()["pro"] is False


def test_checkout_rifiutato_se_gia_abbonato(client, finto_stripe):
    _registra(client)
    _paga(client, finto_stripe)
    r = client.post(CHECKOUT_URL, json={"piano": "mensile", "accetta_condizioni": True, "accetta_esecuzione_immediata": True})
    assert r.status_code == 409


# --- 5. conferma al ritorno ------------------------------------------------------


def test_conferma_attiva_senza_aspettare_il_webhook(client, finto_stripe):
    _registra(client)
    r = client.post(CHECKOUT_URL, json={"piano": "annuale", "accetta_condizioni": True, "accetta_esecuzione_immediata": True})
    cs_id = r.json()["url"].rsplit("/", 1)[1]
    assert client.post(CONFERMA_URL, json={"session_id": cs_id}).json()["pro"] is False  # non ancora pagato
    finto_stripe.completa(cs_id)
    assert client.post(CONFERMA_URL, json={"session_id": cs_id}).json()["pro"] is True


def test_conferma_non_vale_per_la_sessione_di_un_altro(client, finto_stripe):
    _registra(client, "a@example.com")
    cs_id = client.post(CHECKOUT_URL, json={"piano": "annuale", "accetta_condizioni": True, "accetta_esecuzione_immediata": True}).json()["url"].rsplit("/", 1)[1]
    finto_stripe.completa(cs_id)
    client.post("/api/v1/auth/logout")
    client.cookies.clear()
    _registra(client, "b@example.com")
    assert client.post(CONFERMA_URL, json={"session_id": cs_id}).json()["pro"] is False


# --- portale e nessuna fuga ---------------------------------------------------------


def test_portale(client, finto_stripe):
    _registra(client)
    assert client.post(PORTALE_URL).status_code == 404
    _paga(client, finto_stripe)
    r = client.post(PORTALE_URL)
    assert r.status_code == 200 and r.json()["url"] == "https://billing.stripe.test/portale"
    params = [p for nome, p in finto_stripe.richieste if nome == "billing_portal.sessions.create"][0]
    assert params["return_url"].endswith("/impostazioni/abbonamento")


def test_nessun_identificativo_stripe_verso_il_client(client, finto_stripe):
    _registra(client)
    _paga(client, finto_stripe)
    for url in (ME_URL, ABBONAMENTO_URL, PIANI_URL):
        testo = client.get(url).text
        for vietato in ("cus_", "sub_", "price_", "stripe"):
            assert vietato not in testo, (url, vietato)
