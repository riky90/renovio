"""POST /api/v1/lead — cattura del lead di contatto (LEAD-01/02/03).

Solo utenti loggati (D-01, `Depends(get_current_user)`, non `require_admin`).
Persiste SEMPRE il record Lead PRIMA di qualsiasi tentativo SMTP (D-07): la
riga esiste committata nel DB prima che venga fatto qualunque `await
send_email(...)`. Risolve poi il referente della città (D-04/D-05) e invia
due email — al referente (notifica, D-06) e all'utente (conferma, D-08) —
entrambe SOLO con dati contatto + riepilogo a range, MAI dati impresa
(D-06/D-22/D-23).

Pattern async call-site copiato verbatim da `routers/auth.py`'s
`password_dimenticata` (04-RESEARCH.md Pitfall 4/Pattern 3): route `async
def`, scrittura DB sync dentro `with SessionLocal()`, poi `await
send_email(...)` come statement top-level. Difesa in profondità (D-07):
se `send_email` dovesse sollevare (il contratto dice che non dovrebbe mai
farlo), l'endpoint marca `email_inviata=False` e ritorna comunque 201 — mai
un 500 per un problema SMTP, il record in dashboard è la rete di sicurezza.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.dependencies.auth import get_current_user
from app.models.lead import Lead
from app.models.user import User
from app.schemas.lead import LeadCreate, LeadCreatedOut
from app.services.email_service import send_email
from app.services.lead_service import resolve_referente

router = APIRouter(prefix="/lead", tags=["lead"])

logger = logging.getLogger(__name__)


def _riepilogo_html(payload: LeadCreate) -> str:
    """Riepilogo SOLO a range (D-23) — mai coefficiente/prezzo impresa (D-22)."""
    return (
        f"<p><strong>Città:</strong> {payload.citta}</p>"
        f"<p><strong>Superficie:</strong> {payload.mq} m²</p>"
        f"<p><strong>Tipo intervento:</strong> {payload.tipo}</p>"
        f"<p><strong>Stima:</strong> € {payload.totale_min} – € {payload.totale_max}</p>"
    )


def _contatto_html(payload: LeadCreate) -> str:
    righe = [
        f"<p><strong>Nome:</strong> {payload.nome}</p>",
        f"<p><strong>Email:</strong> {payload.email}</p>",
    ]
    if payload.telefono:
        righe.append(f"<p><strong>Telefono:</strong> {payload.telefono}</p>")
    righe.append(f"<p><strong>Preferenza di contatto:</strong> {payload.preferenza_contatto.value}</p>")
    if payload.fascia_oraria:
        righe.append(f"<p><strong>Fascia oraria:</strong> {payload.fascia_oraria}</p>")
    if payload.messaggio:
        righe.append(f"<p><strong>Messaggio:</strong> {payload.messaggio}</p>")
    return "".join(righe)


def _email_referente_body(payload: LeadCreate) -> str:
    link = f"{settings.FRONTEND_URL}/admin/lead"
    return (
        "<h2>Nuova richiesta di contatto</h2>"
        + _contatto_html(payload)
        + _riepilogo_html(payload)
        + f'<p><a href="{link}">Apri la dashboard lead</a></p>'
    )


def _email_conferma_utente_body(payload: LeadCreate) -> str:
    return (
        "<h2>Abbiamo ricevuto la tua richiesta</h2>"
        "<p>Un professionista ti ricontatterà a breve per organizzare un sopralluogo.</p>"
        + _riepilogo_html(payload)
    )


async def _invia_email_lead(session: Session, lead: Lead, payload: LeadCreate) -> None:
    """Risolve il referente, invia le due email (D-06/D-08) e aggiorna
    `referente_id`/`email_inviata`. Chiamata SOLO dopo che `lead` è già
    stato committato (D-07)."""
    referente = resolve_referente(session, payload.citta)
    lead.referente_id = referente.id if referente is not None else None
    session.commit()

    inviata = False
    try:
        if referente is not None:
            await send_email(
                to=referente.email,
                subject="Nuova richiesta di contatto",
                html_body=_email_referente_body(payload),
            )
        await send_email(
            to=payload.email,
            subject="Abbiamo ricevuto la tua richiesta",
            html_body=_email_conferma_utente_body(payload),
        )
        inviata = True
    except Exception:  # difesa in profondità (D-07) — send_email è "never-raises" per contratto
        logger.exception("Invio email lead fallito — il record resta comunque salvato (lead_id=%s)", lead.id)
        inviata = False

    lead.email_inviata = inviata
    session.commit()


@router.post("", status_code=201, response_model=LeadCreatedOut)
async def crea_lead(
    payload: LeadCreate,
    current_user: User = Depends(get_current_user),
) -> LeadCreatedOut:
    with SessionLocal() as session:
        lead = Lead(
            user_id=current_user.id,
            nome=payload.nome,
            email=payload.email,
            telefono=payload.telefono,
            preferenza_contatto=payload.preferenza_contatto.value,
            fascia_oraria=payload.fascia_oraria,
            messaggio=payload.messaggio,
            citta=payload.citta,
            mq=payload.mq,
            tipo=payload.tipo,
            totale_min=payload.totale_min,
            totale_max=payload.totale_max,
        )
        session.add(lead)
        session.commit()
        session.refresh(lead)

        await _invia_email_lead(session, lead, payload)

        return LeadCreatedOut(id=lead.id)
