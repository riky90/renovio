"""/api/v1/me/stime — save/list/detail/pdf of the current user's estimates.

Every endpoint sits behind `Depends(get_current_user)` (T-07-04/T-08-04, 401
without a session). POST freezes the client-supplied `StimaResponse`-shaped
payload as-is into `risultato_json` (+ `schema_version`) — it NEVER calls
`EstimationService` (D-09/Pitfall 5, no recompute). GET list/detail/pdf are
filtered by `user_id == current_user.id`; detail/pdf return 404 (not 403)
when the row belongs to another user or doesn't exist, so ownership is
never leaked (T-07-01/T-08-02, anti-IDOR, ASVS V4). The pdf endpoint reads
ONLY the frozen snapshot via `PdfService` (T-08-03, D-11).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.dependencies.auth import get_current_user, subscription_is_active
from app.models.stima_salvata import StimaSalvata
from app.models.user import User
from app.schemas.stima import ArredoOut, BonusOut, CategoriaOut, ConfrontoFinitureOut, ExtraOut, StimaInputEcho, TotaleOut
from app.schemas.stima_salvata import (
    BudgetIn,
    BudgetOut,
    StimaSalvataCreate,
    StimaSalvataListItem,
    StimaSalvataOut,
)
from app.services.dettaglio_pro import (
    LivelliNonValidi,
    RisposteNonValide,
    domande_configuratore,
    valida_risposte_pro,
    validate_livelli,
)
from app.services.effetti import CONTROLLI_NUMERICI
from app.services.pdf_service import PdfService, build_filename

router = APIRouter(prefix="/me", tags=["stime"])

# v2: lo snapshot puo' contenere le chiavi opzionali `bonus`, `arredo` e
# `input.destinazione`.
# Gli snapshot v1 restano leggibili e non vengono mai riscritti — si leggono
# con `.get()` e i default degli schemi.
SCHEMA_VERSION = 2


class StimaSalvataCreatedOut(BaseModel):
    id: int
    created_at: datetime


@router.post("/stime", response_model=StimaSalvataCreatedOut, status_code=201)
def salva_stima(
    payload: StimaSalvataCreate,
    current_user: User = Depends(get_current_user),
) -> StimaSalvataCreatedOut:
    with SessionLocal() as session:
        # `exclude={"preferenze_pro"}`: senza questo, i parametri di ricalcolo
        # finirebbero DENTRO lo snapshot immutabile, che per contratto ha la
        # forma di `StimaResponse` — cioe' cio' che l'utente ha visto. La forma
        # dello snapshot resta identica a prima di questa feature.
        # Idem `budget_eur`: e' un parametro modificabile con PATCH, se restasse
        # nello snapshot ci sarebbero due verita' dopo la prima modifica.
        risultato_json = payload.model_dump(mode="json", exclude={"preferenze_pro", "budget_eur"})
        risultato_json["schema_version"] = SCHEMA_VERSION

        # Il tier si congela QUI, una volta sola: e' il piano attivo adesso, non
        # quello che l'utente avra' in futuro (vedi models/stima_salvata.py).
        tier = "pro" if subscription_is_active(session, current_user) else "free"

        preferenze = payload.preferenze_pro
        livelli = preferenze.livelli if preferenze else None
        if livelli:
            try:
                validate_livelli(session, livelli)
            except LivelliNonValidi as exc:
                raise HTTPException(400, str(exc)) from exc

        # Scelte del configuratore Pro raccolte nel wizard (09-11, es.
        # tipo_pavimento): validate contro il catalogo, poi unite alle
        # risposte mirate nella STESSA colonna che il pannello del dettaglio
        # gia' usa (`risposte_pro_json`), cosi' schermata e wizard restano
        # allineati.
        scelte_grezze = preferenze.scelte if preferenze else None
        scelte_valide: dict = {}
        if scelte_grezze:
            try:
                scelte_valide = valida_risposte_pro(session, dict(scelte_grezze))
            except RisposteNonValide as exc:
                raise HTTPException(400, str(exc)) from exc
            domande_catalogo = {
                d.code: d for d in domande_configuratore(session, mq=1, risposte={})
            }
            for codice in scelte_valide:
                domanda = domande_catalogo.get(codice)
                if domanda is None or domanda.tipo_controllo in CONTROLLI_NUMERICI:
                    raise HTTPException(400, f"'{codice}' non e' una scelta")

        risposte_pro: dict = {}
        if preferenze and preferenze.risposte is not None:
            risposte_pro.update(preferenze.risposte.model_dump())
        if scelte_valide:
            risposte_pro.update(scelte_valide)

        row = StimaSalvata(
            user_id=current_user.id,
            tier=tier,
            citta=payload.input.citta,
            mq=payload.input.mq,
            tipo=payload.input.tipo.value,
            totale_min=payload.totale.totale_min,
            totale_max=payload.totale.totale_max,
            fallback=payload.fallback,
            risultato_json=risultato_json,
            budget_eur=payload.budget_eur,
            livelli_pro_json=livelli or None,
            risposte_pro_json=risposte_pro or None,
        )
        session.add(row)
        session.commit()
        session.refresh(row)

        return StimaSalvataCreatedOut(id=row.id, created_at=row.created_at)


@router.get("/stime", response_model=list[StimaSalvataListItem])
def lista_stime(current_user: User = Depends(get_current_user)) -> list[StimaSalvataListItem]:
    with SessionLocal() as session:
        stmt = (
            select(StimaSalvata)
            .where(StimaSalvata.user_id == current_user.id)
            .order_by(StimaSalvata.created_at.desc())
        )
        rows = session.execute(stmt).scalars().all()

        return [
            StimaSalvataListItem(
                id=row.id,
                citta=row.citta,
                mq=row.mq,
                tipo=row.tipo,
                totale_min=row.totale_min,
                totale_max=row.totale_max,
                tier=row.tier or "free",
                created_at=row.created_at,
            )
            for row in rows
        ]


@router.get("/stime/{stima_id}", response_model=StimaSalvataOut)
def dettaglio_stima(
    stima_id: int,
    current_user: User = Depends(get_current_user),
) -> StimaSalvataOut:
    with SessionLocal() as session:
        stmt = select(StimaSalvata).where(
            StimaSalvata.id == stima_id,
            StimaSalvata.user_id == current_user.id,
        )
        row = session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, "Stima non trovata")

        snapshot = row.risultato_json

        return StimaSalvataOut(
            id=row.id,
            created_at=row.created_at,
            tier=row.tier or "free",
            input=StimaInputEcho(**snapshot["input"]),
            fallback=snapshot["fallback"],
            disclaimer=snapshot["disclaimer"],
            valuta=snapshot["valuta"],
            categorie=[CategoriaOut(**c) for c in snapshot["categorie"]],
            extra=[ExtraOut(**e) for e in snapshot["extra"]],
            totale=TotaleOut(**snapshot["totale"]),
            # `.get()` e non `snapshot["bonus"]`: un KeyError qui romperebbe
            # TUTTO lo storico di TUTTI gli utenti, perche' nessuna riga salvata
            # prima di questa feature ha la chiave.
            bonus=BonusOut(**snapshot["bonus"]) if snapshot.get("bonus") else None,
            # Snapshot precedenti a G9: niente chiave `arredo`, da qui il `.get()`.
            arredo=ArredoOut(**snapshot["arredo"]) if snapshot.get("arredo") else None,
            # Stesso motivo: assenti negli snapshot precedenti al 10-04.
            confronto_finiture=(
                ConfrontoFinitureOut(**snapshot["confronto_finiture"])
                if snapshot.get("confronto_finiture")
                else None
            ),
            finiture_al_minimo=bool(snapshot.get("finiture_al_minimo", False)),
            budget_eur=row.budget_eur,
        )


@router.patch("/stime/{stima_id}/budget", response_model=BudgetOut)
def aggiorna_budget(
    stima_id: int,
    payload: BudgetIn,
    current_user: User = Depends(get_current_user),
) -> BudgetOut:
    """Aggiorna SOLO la colonna `budget_eur` (Free e Pro). Lo snapshot non si
    tocca e nessun motore viene chiamato: il budget non muove il prezzo.
    404 (mai 403) su stima altrui o inesistente (anti-IDOR)."""
    with SessionLocal() as session:
        stmt = select(StimaSalvata).where(
            StimaSalvata.id == stima_id,
            StimaSalvata.user_id == current_user.id,
        )
        row = session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, "Stima non trovata")

        row.budget_eur = payload.budget_eur
        session.commit()
        return BudgetOut(budget_eur=row.budget_eur)


@router.get("/stime/{stima_id}/pdf")
def scarica_pdf_stima(
    stima_id: int,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Free branded PDF download (PDF-01, D-11/D-12). Reads ONLY the frozen
    `risultato_json` snapshot via `PdfService` — never recomputes
    (D-09/Pitfall 5, T-08-03)."""
    with SessionLocal() as session:
        stmt = select(StimaSalvata).where(
            StimaSalvata.id == stima_id,
            StimaSalvata.user_id == current_user.id,
        )
        row = session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, "Stima non trovata")

        pdf_bytes = PdfService.render(row, current_user)
        filename = build_filename(row)

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
