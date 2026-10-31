"""Pagamento del Pro con Stripe: piani, checkout, portale clienti, webhook.

La logica e' in `services/pagamenti.py`; qui solo HTTP, autenticazione e
codici di errore. Tutte le rotte rispondono 503 se Stripe non e'
configurato, tranne `GET /pro/piani`, che lo dice al frontend
(`pagamenti_attivi`), e `GET /me/abbonamento`, che legge solo la tessera.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from app.db import SessionLocal
from app.dependencies.auth import get_current_user, subscription_is_active
from app.limiter import limiter
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import (
    AbbonamentoOut,
    RecessoOut,
    CheckoutIn,
    ConfermaCheckoutIn,
    PianiOut,
    PianoOut,
    UrlOut,
)
from app.services import email_pro, pagamenti
from app.services.email_service import send_email

router = APIRouter(tags=["pagamenti"])
log = logging.getLogger(__name__)

NON_CONFIGURATI = "Pagamenti non ancora attivi."
STRIPE_KO = "Il servizio di pagamento non risponde. Riprova tra qualche minuto."


def _abbonamento_out(session, user: User) -> AbbonamentoOut:
    tessera = session.query(Subscription).filter_by(user_id=user.id).one_or_none()
    pro = subscription_is_active(session, user)
    if tessera is None:
        return AbbonamentoOut(
            pro=pro, stato="inattivo", piano_code=None, scade_il=None, rinnovo_automatico=False, gestibile=False
        )
    con_stripe = bool(tessera.stripe_subscription_id)
    scade_il = tessera.scaduta_il
    if con_stripe and tessera.stato == "attivo" and scade_il is not None:
        # La tessera tiene due giorni di margine per il webhook del rinnovo:
        # all'utente si mostra la fine vera del periodo pagato.
        scade_il = scade_il - pagamenti.TOLLERANZA_RINNOVO
    return AbbonamentoOut(
        pro=pro,
        stato=tessera.stato,
        piano_code=tessera.piano_code,
        scade_il=scade_il,
        rinnovo_automatico=pro and con_stripe and not tessera.cancella_a_fine_periodo,
        gestibile=bool(tessera.stripe_customer_id) and pagamenti.pagamenti_attivi(),
        recesso_fino_al=pagamenti.recesso_possibile_fino_al(tessera),
    )


async def _invia_conferma_acquisto(session, applicato: pagamenti.Applicato | None) -> None:
    """Email di conferma alla prima attivazione di un abbonamento. Un errore di
    invio non deve far fallire webhook o conferma: si registra e basta."""
    if applicato is None or not applicato.nuovo_acquisto:
        return
    tessera = applicato.tessera
    user = session.get(User, tessera.user_id)
    if user is None:
        return
    rinnovo = tessera.scaduta_il - pagamenti.TOLLERANZA_RINNOVO if tessera.scaduta_il else None
    oggetto, html = email_pro.conferma_acquisto(
        nome=user.nome,
        piano_code=tessera.piano_code,
        importo=applicato.importo,
        intervallo=applicato.intervallo,
        rinnovo_il=rinnovo,
        recesso_fino_al=pagamenti.recesso_possibile_fino_al(tessera),
    )
    try:
        await send_email(to=user.email, subject=oggetto, html_body=html)
    except Exception:
        log.exception("Email di conferma del Pro non inviata (user_id=%s)", user.id)


@router.get("/pro/piani", response_model=PianiOut)
def leggi_piani() -> PianiOut:
    if not pagamenti.pagamenti_attivi():
        return PianiOut(pagamenti_attivi=False, piani=[])
    try:
        piani = pagamenti.piani()
    except stripe.StripeError:
        log.exception("Stripe: lettura dei prezzi non riuscita")
        raise HTTPException(503, STRIPE_KO)
    return PianiOut(
        pagamenti_attivi=True,
        piani=[
            PianoOut(code=p.code, nome=p.nome, importo=p.importo, valuta=p.valuta, intervallo=p.intervallo)
            for p in piani
        ],
    )


@router.get("/me/abbonamento", response_model=AbbonamentoOut)
def leggi_abbonamento(current_user: User = Depends(get_current_user)) -> AbbonamentoOut:
    with SessionLocal() as session:
        return _abbonamento_out(session, current_user)


@router.post("/pro/checkout", response_model=UrlOut)
@limiter.limit("10/minute")
def crea_checkout(
    request: Request, payload: CheckoutIn, current_user: User = Depends(get_current_user)
) -> UrlOut:
    if not pagamenti.pagamenti_attivi():
        raise HTTPException(503, NON_CONFIGURATI)
    if payload.piano not in pagamenti.PIANI:
        raise HTTPException(422, "Piano non valido.")
    if not payload.accetta_condizioni:
        raise HTTPException(422, "Per procedere bisogna accettare le condizioni di vendita.")
    if not payload.accetta_esecuzione_immediata:
        raise HTTPException(422, "Per procedere serve la richiesta di attivazione immediata del servizio.")
    with SessionLocal() as session:
        tessera = session.query(Subscription).filter_by(user_id=current_user.id).one_or_none()
        if (
            tessera is not None
            and tessera.stripe_subscription_id
            and subscription_is_active(session, current_user)
        ):
            raise HTTPException(409, "Hai già un abbonamento Pro attivo: puoi gestirlo dalle impostazioni.")
        try:
            url = pagamenti.crea_checkout(
                session, current_user, payload.piano, consensi_il=datetime.now(timezone.utc)
            )
        except pagamenti.PianoNonDisponibile:
            raise HTTPException(422, "Piano non disponibile.")
        except stripe.StripeError:
            log.exception("Stripe: creazione del checkout non riuscita")
            raise HTTPException(503, STRIPE_KO)
    return UrlOut(url=url)


@router.post("/pro/checkout/conferma", response_model=AbbonamentoOut)
@limiter.limit("20/minute")
async def conferma_checkout(
    request: Request, payload: ConfermaCheckoutIn, current_user: User = Depends(get_current_user)
) -> AbbonamentoOut:
    if not pagamenti.pagamenti_attivi():
        raise HTTPException(503, NON_CONFIGURATI)
    with SessionLocal() as session:
        try:
            applicato = pagamenti.conferma_checkout(session, current_user, payload.session_id)
        except stripe.StripeError:
            log.exception("Stripe: conferma del checkout non riuscita")
            raise HTTPException(503, STRIPE_KO)
        await _invia_conferma_acquisto(session, applicato)
        return _abbonamento_out(session, current_user)


@router.post("/pro/recesso", response_model=RecessoOut)
@limiter.limit("5/minute")
async def recedi(request: Request, current_user: User = Depends(get_current_user)) -> RecessoOut:
    """"Recedi dal contratto qui" -> "Conferma recesso" (art. 54-bis Codice
    del Consumo): rimborso integrale, abbonamento chiuso subito, ricevuta via
    email. Possibile entro 14 giorni dal primo acquisto."""
    if not pagamenti.pagamenti_attivi():
        raise HTTPException(503, NON_CONFIGURATI)
    with SessionLocal() as session:
        tessera = session.query(Subscription).filter_by(user_id=current_user.id).one_or_none()
        try:
            rimborsato = pagamenti.recedi(session, tessera) if tessera is not None else None
        except pagamenti.RecessoNonPossibile:
            rimborsato = None
        except stripe.StripeError:
            log.exception("Stripe: recesso non riuscito (user_id=%s)", current_user.id)
            raise HTTPException(503, STRIPE_KO)
        if rimborsato is None:
            raise HTTPException(
                409,
                "Il recesso non è più disponibile: è possibile entro 14 giorni dal primo acquisto. "
                "Puoi sempre disdire il rinnovo da «Gestisci abbonamento».",
            )
        oggetto, html = email_pro.ricevuta_recesso(
            nome=current_user.nome, rimborsato=rimborsato, receduto_il=tessera.receduto_il
        )
        try:
            await send_email(to=current_user.email, subject=oggetto, html_body=html)
        except Exception:
            log.exception("Email di ricevuta del recesso non inviata (user_id=%s)", current_user.id)
        return RecessoOut(rimborsato=rimborsato, abbonamento=_abbonamento_out(session, current_user))


@router.post("/pro/portale", response_model=UrlOut)
@limiter.limit("10/minute")
def apri_portale(request: Request, current_user: User = Depends(get_current_user)) -> UrlOut:
    if not pagamenti.pagamenti_attivi():
        raise HTTPException(503, NON_CONFIGURATI)
    with SessionLocal() as session:
        tessera = session.query(Subscription).filter_by(user_id=current_user.id).one_or_none()
        if tessera is None or not tessera.stripe_customer_id:
            raise HTTPException(404, "Nessun abbonamento da gestire.")
        try:
            return UrlOut(url=pagamenti.crea_portale(tessera))
        except stripe.StripeError:
            log.exception("Stripe: apertura del portale non riuscita")
            raise HTTPException(503, STRIPE_KO)


@router.post("/stripe/webhook")
async def webhook_stripe(request: Request) -> dict:
    payload = await request.body()
    try:
        evento = pagamenti.verifica_evento(payload, request.headers.get("stripe-signature"))
    except pagamenti.PagamentiNonConfigurati:
        raise HTTPException(503, NON_CONFIGURATI)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(400, "Firma non valida.")
    with SessionLocal() as session:
        try:
            esito, applicato = pagamenti.gestisci_evento(session, evento)
        except stripe.StripeError:
            # 5xx: Stripe ritentera' la consegna dell'evento.
            log.exception("Stripe: gestione dell'evento %s non riuscita", evento.get("type"))
            raise HTTPException(503, STRIPE_KO)
        await _invia_conferma_acquisto(session, applicato)
    return {"ricevuto": True, "esito": esito}
