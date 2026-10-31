"""Pagamenti del Pro con Stripe: piani, checkout, portale clienti, webhook.

Il Pro e' un abbonamento Stripe, mensile o annuale. Questo modulo e' l'unico
che parla con Stripe; i router lo chiamano, i test lo sostituiscono.

COME SI ATTIVA IL PRO
---------------------
1. `crea_checkout`: pagina di pagamento ospitata da Stripe (Checkout, modo
   `subscription`), legata all'utente con `client_reference_id` e con il
   cliente Stripe salvato sulla tessera.
2. Stripe chiama il webhook (`/stripe/webhook`): la firma si verifica con
   `STRIPE_WEBHOOK_SECRET` e, per ogni evento che riguarda un abbonamento,
   l'abbonamento si RILEGGE da Stripe. Cosi' l'ordine degli eventi non conta e
   un evento ripetuto non fa danni: vince sempre lo stato corrente.
3. `applica_abbonamento` traduce l'abbonamento Stripe nella tessera
   `Subscription`, che resta la sola fonte dello stato Pro
   (`subscription_is_active`).
4. Al ritorno dal pagamento il frontend chiama `conferma_checkout`: se il
   webhook e' in ritardo, il Pro si attiva lo stesso.

PREZZI
------
Importi e valuta stanno solo su Stripe: i due prezzi si cercano per
`lookup_key` (`STRIPE_LOOKUP_KEY_MENSILE`, `STRIPE_LOOKUP_KEY_ANNUALE`).
Cambiare prezzo = nuovo prezzo su Stripe con la stessa lookup key (opzione
"trasferisci la lookup key"), nessun deploy. Gli abbonamenti gia' attivi
restano al loro prezzo finche' non li si migra dal pannello Stripe.

SENZA CHIAVE
------------
Senza `STRIPE_SECRET_KEY` i pagamenti sono spenti (`pagamenti_attivi()` e'
False): la pagina "Passa a Pro" resta sull'attivazione dimostrativa.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import stripe
from sqlalchemy.orm import Session

from app.config import settings
from app.models.subscription import Subscription
from app.models.user import User

PIANO_MENSILE = "mensile"
PIANO_ANNUALE = "annuale"
PIANI = (PIANO_MENSILE, PIANO_ANNUALE)

#: Stati Stripe con cui il Pro e' attivo. `past_due`: il rinnovo non e'
#: andato a buon fine e Stripe sta riprovando; il Pro resta attivo fino alla
#: fine del periodo pagato (`scaduta_il`), poi decide il prossimo evento.
STATI_ATTIVI = frozenset({"active", "trialing", "past_due"})
#: Stati finali: l'abbonamento non tornera' attivo.
STATI_CHIUSI = frozenset({"canceled", "unpaid", "incomplete_expired"})

#: Margine dopo la fine del periodo: il webhook del rinnovo puo' arrivare
#: qualche ora dopo la scadenza, e l'utente non deve perdere il Pro intanto.
TOLLERANZA_RINNOVO = timedelta(days=2)

#: Eventi che riguardano un abbonamento. Gli altri si ignorano (risposta 200).
EVENTI_ABBONAMENTO = frozenset(
    {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.paid",
        "invoice.payment_failed",
    }
)

_CACHE_PIANI_SECONDI = 600


class PagamentiNonConfigurati(RuntimeError):
    """Manca la chiave Stripe o il segreto del webhook."""


class PianoNonDisponibile(ValueError):
    """Il piano chiesto non ha un prezzo attivo su Stripe."""


@dataclass(frozen=True)
class Piano:
    code: str
    nome: str
    importo: Decimal  # IVA inclusa, nella valuta del prezzo
    valuta: str
    intervallo: str  # "month" | "year"
    price_id: str


def pagamenti_attivi() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


def _client() -> stripe.StripeClient:
    if not pagamenti_attivi():
        raise PagamentiNonConfigurati("STRIPE_SECRET_KEY non impostata")
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def _lookup_keys() -> dict[str, str]:
    return {
        settings.STRIPE_LOOKUP_KEY_MENSILE: PIANO_MENSILE,
        settings.STRIPE_LOOKUP_KEY_ANNUALE: PIANO_ANNUALE,
    }


def _get(obj: Any, chiave: str, default: Any = None) -> Any:
    """Legge un campo da un oggetto Stripe o da un dict (test, payload)."""
    if obj is None:
        return default
    try:
        valore = obj[chiave]
    except (KeyError, TypeError, IndexError):
        valore = getattr(obj, chiave, default) if not isinstance(obj, dict) else default
    return default if valore is None else valore


# --- piani --------------------------------------------------------------------

_cache_piani: tuple[float, list[Piano]] | None = None


def piani() -> list[Piano]:
    """I piani in vendita, dai prezzi Stripe attivi con le nostre lookup key.
    In cache per qualche minuto: la pagina e' pubblica."""
    global _cache_piani
    if _cache_piani is not None and time.monotonic() - _cache_piani[0] < _CACHE_PIANI_SECONDI:
        return _cache_piani[1]
    chiavi = _lookup_keys()
    prezzi = _client().v1.prices.list(
        params={"lookup_keys": list(chiavi), "active": True, "expand": ["data.product"]}
    )
    risultato: list[Piano] = []
    for prezzo in _get(prezzi, "data", []):
        code = chiavi.get(_get(prezzo, "lookup_key"))
        ricorrenza = _get(prezzo, "recurring")
        if code is None or ricorrenza is None or _get(prezzo, "unit_amount") is None:
            continue
        prodotto = _get(prezzo, "product")
        nome = _get(prodotto, "name") if not isinstance(prodotto, str) else None
        risultato.append(
            Piano(
                code=code,
                nome=nome or "Renovio Pro",
                importo=Decimal(_get(prezzo, "unit_amount")) / 100,
                valuta=str(_get(prezzo, "currency", "eur")).upper(),
                intervallo=_get(ricorrenza, "interval"),
                price_id=_get(prezzo, "id"),
            )
        )
    risultato.sort(key=lambda p: PIANI.index(p.code))
    _cache_piani = (time.monotonic(), risultato)
    return risultato


def svuota_cache_piani() -> None:
    global _cache_piani
    _cache_piani = None


# --- tessera ------------------------------------------------------------------


def tessera_di(session: Session, user_id: int) -> Subscription:
    """La tessera dell'utente; la crea inattiva se non c'e'."""
    tessera = session.query(Subscription).filter_by(user_id=user_id).one_or_none()
    if tessera is None:
        tessera = Subscription(user_id=user_id, stato="inattivo")
        session.add(tessera)
        session.flush()
    return tessera


def _cliente_stripe(session: Session, user: User, tessera: Subscription) -> str:
    if tessera.stripe_customer_id:
        return tessera.stripe_customer_id
    nome = " ".join(p for p in (user.nome, getattr(user, "cognome", None)) if p)
    cliente = _client().v1.customers.create(
        params={"email": user.email, "name": nome or None, "metadata": {"user_id": str(user.id)}}
    )
    tessera.stripe_customer_id = _get(cliente, "id")
    session.flush()
    return tessera.stripe_customer_id


# --- checkout e portale ---------------------------------------------------------


def crea_checkout(session: Session, user: User, piano_code: str, *, consensi_il: datetime) -> str:
    """URL della pagina di pagamento Stripe per il piano scelto."""
    piano = next((p for p in piani() if p.code == piano_code), None)
    if piano is None:
        raise PianoNonDisponibile(piano_code)
    tessera = tessera_di(session, user.id)
    cliente = _cliente_stripe(session, user, tessera)
    metadata = {
        "user_id": str(user.id),
        "piano": piano.code,
        # Quando l'utente ha accettato le condizioni di vendita e chiesto
        # l'attivazione immediata (art. 50, c. 3 Codice del Consumo): resta
        # su Stripe come traccia del consenso.
        "condizioni_accettate_il": consensi_il.isoformat(),
        "attivazione_immediata_richiesta_il": consensi_il.isoformat(),
    }
    base = settings.FRONTEND_URL.rstrip("/")
    checkout = _client().v1.checkout.sessions.create(
        params={
            "mode": "subscription",
            "customer": cliente,
            "client_reference_id": str(user.id),
            "line_items": [{"price": piano.price_id, "quantity": 1}],
            "metadata": metadata,
            "subscription_data": {"metadata": metadata},
            "allow_promotion_codes": True,
            "locale": "it",
            "success_url": f"{base}/passa-a-pro?esito=ok&session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{base}/passa-a-pro?esito=annullato",
        }
    )
    session.commit()
    return _get(checkout, "url")


def crea_portale(tessera: Subscription) -> str:
    """URL del portale clienti Stripe: disdetta, cambio piano, carta, fatture."""
    if not tessera.stripe_customer_id:
        raise PianoNonDisponibile("nessun cliente Stripe")
    portale = _client().v1.billing_portal.sessions.create(
        params={
            "customer": tessera.stripe_customer_id,
            "return_url": f"{settings.FRONTEND_URL.rstrip('/')}/impostazioni/abbonamento",
        }
    )
    return _get(portale, "url")


# --- stato dell'abbonamento -------------------------------------------------------


def _fine_periodo(abbonamento: Any) -> datetime | None:
    """`current_period_end`: sull'abbonamento nelle API vecchie, sulle voci
    (`items`) da quelle del 2025. Si accettano entrambe."""
    fine = _get(abbonamento, "current_period_end")
    if fine is None:
        voci = _get(_get(abbonamento, "items"), "data", [])
        fini = [_get(v, "current_period_end") for v in voci if _get(v, "current_period_end")]
        fine = max(fini) if fini else None
    return datetime.fromtimestamp(int(fine), tz=timezone.utc) if fine is not None else None


def _piano_di(abbonamento: Any) -> str | None:
    chiavi = _lookup_keys()
    for voce in _get(_get(abbonamento, "items"), "data", []):
        code = chiavi.get(_get(_get(voce, "price"), "lookup_key"))
        if code:
            return code
    return _get(_get(abbonamento, "metadata"), "piano")


def _tessera_per_abbonamento(session: Session, abbonamento: Any) -> Subscription | None:
    sub_id = _get(abbonamento, "id")
    cliente = _get(abbonamento, "customer")
    if isinstance(cliente, dict) or (cliente is not None and not isinstance(cliente, str)):
        cliente = _get(cliente, "id")
    tessera = None
    if sub_id:
        tessera = session.query(Subscription).filter_by(stripe_subscription_id=sub_id).one_or_none()
    if tessera is None and cliente:
        tessera = session.query(Subscription).filter_by(stripe_customer_id=cliente).one_or_none()
    if tessera is None:
        user_id = _get(_get(abbonamento, "metadata"), "user_id")
        if user_id and str(user_id).isdigit() and session.get(User, int(user_id)) is not None:
            tessera = tessera_di(session, int(user_id))
    if tessera is not None and cliente and not tessera.stripe_customer_id:
        tessera.stripe_customer_id = cliente
    return tessera


def applica_abbonamento(session: Session, abbonamento: Any) -> Subscription | None:
    """Porta la tessera allo stato dell'abbonamento Stripe. Idempotente.
    `None` se l'abbonamento non e' di nessun nostro utente."""
    tessera = _tessera_per_abbonamento(session, abbonamento)
    if tessera is None:
        return None
    stato = _get(abbonamento, "status")
    sub_id = _get(abbonamento, "id")
    # Un abbonamento vecchio e chiuso non deve spegnere quello nuovo: se la
    # tessera segue gia' un altro abbonamento ancora vivo, si ignora.
    if (
        tessera.stripe_subscription_id
        and sub_id != tessera.stripe_subscription_id
        and stato in STATI_CHIUSI
        and tessera.stato == "attivo"
    ):
        return tessera
    fine = _fine_periodo(abbonamento)
    if stato in STATI_ATTIVI:
        tessera.stato = "attivo"
        tessera.scaduta_il = (fine + TOLLERANZA_RINNOVO) if fine else None
    elif stato in STATI_CHIUSI:
        tessera.stato = "cancellato"
        chiuso = _get(abbonamento, "ended_at") or _get(abbonamento, "canceled_at")
        tessera.scaduta_il = (
            datetime.fromtimestamp(int(chiuso), tz=timezone.utc) if chiuso else datetime.now(timezone.utc)
        )
    else:
        # `incomplete`: primo pagamento non ancora riuscito. Niente Pro.
        if tessera.stato != "attivo" or tessera.stripe_subscription_id == sub_id:
            tessera.stato = "inattivo"
    tessera.stripe_subscription_id = sub_id
    tessera.piano_code = _piano_di(abbonamento) or tessera.piano_code
    tessera.cancella_a_fine_periodo = bool(_get(abbonamento, "cancel_at_period_end", False))
    session.flush()
    return tessera


def recupera_abbonamento(sub_id: str) -> Any:
    return _client().v1.subscriptions.retrieve(sub_id, params={"expand": ["items.data.price"]})


def recupera_checkout(session_id: str) -> Any:
    return _client().v1.checkout.sessions.retrieve(session_id)


def conferma_checkout(session: Session, user: User, checkout_id: str) -> Subscription | None:
    """Al ritorno dal pagamento: se la sessione di checkout e' di questo
    utente ed e' completa, applica subito l'abbonamento (il webhook potrebbe
    arrivare dopo). `None` se la sessione non e' sua o non e' completa."""
    checkout = recupera_checkout(checkout_id)
    if str(_get(checkout, "client_reference_id")) != str(user.id):
        return None
    if _get(checkout, "status") != "complete" or not _get(checkout, "subscription"):
        return None
    sub_id = _get(checkout, "subscription")
    if not isinstance(sub_id, str):
        sub_id = _get(sub_id, "id")
    tessera = applica_abbonamento(session, recupera_abbonamento(sub_id))
    session.commit()
    return tessera


# --- webhook ------------------------------------------------------------------------


def verifica_evento(payload: bytes, firma: str | None) -> Any:
    """Evento Stripe con firma verificata. Solleva
    `stripe.SignatureVerificationError` o `ValueError` se non e' valido."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise PagamentiNonConfigurati("STRIPE_WEBHOOK_SECRET non impostato")
    return stripe.Webhook.construct_event(payload, firma, settings.STRIPE_WEBHOOK_SECRET)


def gestisci_evento(session: Session, evento: Any) -> str:
    """Applica un evento Stripe. Ritorna un'etichetta per il log/i test."""
    tipo = _get(evento, "type")
    if tipo not in EVENTI_ABBONAMENTO:
        return "ignorato"
    oggetto = _get(_get(evento, "data"), "object")
    if tipo == "checkout.session.completed":
        sub_id = _get(oggetto, "subscription")
    elif tipo.startswith("invoice."):
        sub_id = _get(oggetto, "subscription") or _get(
            _get(_get(oggetto, "parent"), "subscription_details"), "subscription"
        )
    else:
        sub_id = _get(oggetto, "id")
    if sub_id and not isinstance(sub_id, str):
        sub_id = _get(sub_id, "id")
    if not sub_id:
        return "senza abbonamento"
    tessera = applica_abbonamento(session, recupera_abbonamento(sub_id))
    session.commit()
    return "applicato" if tessera is not None else "utente sconosciuto"
