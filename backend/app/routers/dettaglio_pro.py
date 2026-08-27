"""/api/v1/me/stime/{id}/dettaglio-pro — dettaglio bottom-up per
sottocategorie (PRO-01) dietro paywall server-side (PRO-02, D-08).

Ogni rotta sta dietro `Depends(require_pro)`: 401 anonimo (via
`get_current_user`), 403 Free autenticato ("Funzione riservata agli utenti
Pro"). Ownership-filter `id + user_id` -> `HTTPException(404)` (mai 403),
stesso pattern anti-IDOR di `routers/stime_salvate.py`.

Il calcolo e' SEMPRE on-demand dallo snapshot (`citta`/`mq`/`tipo` colonne
scalari di `StimaSalvata`, mai da `risultato_json`, D-09): questa e'
l'asimmetria voluta rispetto al PDF Free (che legge solo lo snapshot
congelato) — qui non serve un secondo snapshot perche' il dettaglio Pro
deve restare aggiornabile dagli admin (Fase 4).

Le risposte alle domande mirate (bagni/porte/condizionatori) sono
persistite in `stima.risposte_pro_json`: sia il GET che il POST leggono/
scrivono la STESSA colonna, cosi' la schermata e il futuro PDF Pro non
possono divergere (03-RESEARCH.md Pitfall 3).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.dependencies.auth import require_pro
from app.models.stima_salvata import StimaSalvata
from app.models.user import User
from app.schemas.dettaglio_pro import (
    CategoriaDettagliataOut,
    DettaglioProOut,
    RisposteDomandeOut,
    RisposteDomandeRequest,
    SottocategoriaOut,
    VoceOut,
)
from app.services.city_resolver import resolve_listino
from app.services.dettaglio_pro import DettaglioProResult, DettaglioProService

router = APIRouter(prefix="/me", tags=["dettaglio-pro"])


def _to_out(result: DettaglioProResult, risposte: dict) -> DettaglioProOut:
    """Mappa campo-per-campo il risultato del servizio nel DTO chiuso — mai
    `model_validate` su entita' ORM o dataclass interne."""
    return DettaglioProOut(
        categorie=[
            CategoriaDettagliataOut(
                code=cat.code,
                nome=cat.nome,
                sottocategorie=[
                    SottocategoriaOut(
                        codice=sotto.codice,
                        nome=sotto.nome,
                        famiglia=sotto.famiglia,
                        voci=[
                            VoceOut(
                                codice=voce.codice,
                                descrizione=voce.descrizione,
                                um=voce.um,
                                quantita_stimata=voce.quantita_stimata,
                                prezzo_min=voce.prezzo_min,
                                prezzo_max=voce.prezzo_max,
                            )
                            for voce in sotto.voci
                        ],
                    )
                    for sotto in cat.sottocategorie
                ],
            )
            for cat in result.categorie
        ],
        risposte=RisposteDomandeOut(**risposte),
    )


def _get_owned_stima(session: Session, stima_id: int, current_user: User) -> StimaSalvata:
    stmt = select(StimaSalvata).where(
        StimaSalvata.id == stima_id,
        StimaSalvata.user_id == current_user.id,
    )
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Stima non trovata")
    return row


@router.get("/stime/{stima_id}/dettaglio-pro", response_model=DettaglioProOut)
def dettaglio_pro(
    stima_id: int,
    current_user: User = Depends(require_pro),
) -> DettaglioProOut:
    with SessionLocal() as session:
        row = _get_owned_stima(session, stima_id, current_user)

        listino, _fallback = resolve_listino(session, row.citta)
        risposte = row.risposte_pro_json or {}

        result = DettaglioProService.compute(session, listino, row.mq, row.tipo, risposte)

        return _to_out(result, risposte)


@router.post("/stime/{stima_id}/dettaglio-pro/risposte", response_model=DettaglioProOut)
def salva_risposte_dettaglio_pro(
    stima_id: int,
    payload: RisposteDomandeRequest,
    current_user: User = Depends(require_pro),
) -> DettaglioProOut:
    with SessionLocal() as session:
        row = _get_owned_stima(session, stima_id, current_user)

        risposte = payload.model_dump()
        row.risposte_pro_json = risposte
        session.commit()
        session.refresh(row)

        listino, _fallback = resolve_listino(session, row.citta)
        result = DettaglioProService.compute(session, listino, row.mq, row.tipo, risposte)

        return _to_out(result, risposte)
