"""CRUD dei bonus fiscali: bonus, aliquote per periodo, mapping categoria.

Tutte le route dietro `require_admin`. E' il pannello che rende vera la
promessa di `models/bonus.py`: quando l'aliquota cambia per legge, si aggiunge
una riga con la nuova finestra di validita', non si fa un deploy.

DUE VINCOLI DI DOMINIO, applicati qui e non solo nei test:

1. **Anti-doppio-conteggio (409).** Per ogni categoria, la somma delle quote
   sui bonus ATTIVI non puo' superare 1. Sforarlo significa detrarre due volte
   la stessa spesa e dire all'utente che recupera piu' di quanto recuperi.
   Il controllo scatta anche riattivando un bonus, non solo aggiungendo un
   mapping: e' li' che l'errore e' piu' facile da fare.
2. **Cancellare un bonus con aliquote o mapping: 409, mai a cascata** (D-24,
   stesso principio della sottocategoria con voci).

Le stime GIA' SALVATE non sono toccate da nessun edit qui: il bonus e'
congelato dentro `risultato_json` insieme al resto dello snapshot.

Non toccare `routers/admin/__init__.py` per la logica: questo file resta il
solo punto di estensione delle route di questa sezione.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.dependencies.auth import require_admin
from app.models.bonus import AliquotaBonus, BonusCategoria, BonusExtra, BonusFiscale
from app.models.catalogo import Categoria, Extra
from app.schemas.admin_bonus import (
    AliquotaIn,
    AliquotaOut,
    AliquotaUpdate,
    BonusCategoriaIn,
    BonusCategoriaOut,
    BonusCategoriaUpdate,
    BonusExtraIn,
    BonusExtraOut,
    BonusExtraUpdate,
    BonusIn,
    BonusOut,
    BonusUpdate,
)
from app.services.bonus_service import BonusService

router = APIRouter(prefix="/bonus", tags=["admin-bonus"])

MSG_QUOTA = (
    "La somma delle quote sui bonus attivi supererebbe il 100% per la categoria "
    "'{categoria}': la stessa spesa verrebbe detratta due volte."
)

MSG_QUOTA_EXTRA = (
    "La somma delle quote sui bonus attivi supererebbe il 100% per l'extra "
    "'{extra}': la stessa spesa verrebbe detratta due volte."
)


def _verifica_quote(
    session: Session,
    *,
    categoria_code: str | None = None,
    quota_aggiunta: Decimal = Decimal("0"),
    escludi_id: int | None = None,
) -> None:
    """Alza 409 se una categoria supererebbe il 100% di quota detraibile."""
    quote = BonusService.quote_per_categoria(session, escludi_id=escludi_id)
    if categoria_code is not None:
        quote[categoria_code] = quote.get(categoria_code, Decimal("0")) + quota_aggiunta
    for code, totale in quote.items():
        if totale > Decimal("1"):
            raise HTTPException(409, MSG_QUOTA.format(categoria=code))


def _verifica_quote_extra(
    session: Session,
    *,
    extra_code: str | None = None,
    quota_aggiunta: Decimal = Decimal("0"),
    escludi_id: int | None = None,
) -> None:
    """Alza 409 se un extra supererebbe il 100% di quota detraibile."""
    quote = BonusService.quote_per_extra(session, escludi_id=escludi_id)
    if extra_code is not None:
        quote[extra_code] = quote.get(extra_code, Decimal("0")) + quota_aggiunta
    for code, totale in quote.items():
        if totale > Decimal("1"):
            raise HTTPException(409, MSG_QUOTA_EXTRA.format(extra=code))


# --- Bonus -----------------------------------------------------------------


@router.get("", response_model=list[BonusOut])
def lista_bonus(_admin=Depends(require_admin)) -> list[BonusOut]:
    with SessionLocal() as session:
        rows = (
            session.execute(select(BonusFiscale).order_by(BonusFiscale.ordine, BonusFiscale.code))
            .scalars()
            .all()
        )
        return [BonusOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("", response_model=BonusOut, status_code=201)
def crea_bonus(payload: BonusIn, _admin=Depends(require_admin)) -> BonusOut:
    with SessionLocal() as session:
        if session.get(BonusFiscale, payload.code) is not None:
            raise HTTPException(409, "Esiste gia' un bonus con questo codice")
        row = BonusFiscale(
            code=payload.code,
            nome=payload.nome,
            descrizione=payload.descrizione,
            ordine=payload.ordine,
            attivo=payload.attivo,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return BonusOut.model_validate(row, from_attributes=True)


@router.patch("/{code}", response_model=BonusOut)
def aggiorna_bonus(code: str, payload: BonusUpdate, _admin=Depends(require_admin)) -> BonusOut:
    with SessionLocal() as session:
        row = session.get(BonusFiscale, code)
        if row is None:
            raise HTTPException(404, "Bonus non trovato")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        session.flush()
        # Riaccendere un bonus puo' far sforare una categoria o un extra: si
        # controlla dopo il flush, prima del commit.
        _verifica_quote(session)
        _verifica_quote_extra(session)
        session.commit()
        session.refresh(row)
        return BonusOut.model_validate(row, from_attributes=True)


@router.delete("/{code}", status_code=204)
def elimina_bonus(code: str, _admin=Depends(require_admin)) -> None:
    with SessionLocal() as session:
        row = session.get(BonusFiscale, code)
        if row is None:
            raise HTTPException(404, "Bonus non trovato")
        dipendenti = (
            session.execute(
                select(AliquotaBonus.id).where(AliquotaBonus.bonus_code == code).limit(1)
            ).first()
            or session.execute(
                select(BonusCategoria.id).where(BonusCategoria.bonus_code == code).limit(1)
            ).first()
            or session.execute(
                select(BonusExtra.id).where(BonusExtra.bonus_code == code).limit(1)
            ).first()
        )
        if dipendenti is not None:
            raise HTTPException(
                409, "Elimina prima le aliquote, le categorie e gli extra di questo bonus"
            )
        session.delete(row)
        session.commit()


# --- Aliquote --------------------------------------------------------------


@router.get("/aliquote", response_model=list[AliquotaOut])
def lista_aliquote(
    bonus_code: str | None = None, _admin=Depends(require_admin)
) -> list[AliquotaOut]:
    with SessionLocal() as session:
        stmt = select(AliquotaBonus)
        if bonus_code is not None:
            stmt = stmt.where(AliquotaBonus.bonus_code == bonus_code)
        stmt = stmt.order_by(
            AliquotaBonus.bonus_code, AliquotaBonus.destinazione, AliquotaBonus.valido_dal
        )
        rows = session.execute(stmt).scalars().all()
        return [AliquotaOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/aliquote", response_model=AliquotaOut, status_code=201)
def crea_aliquota(payload: AliquotaIn, _admin=Depends(require_admin)) -> AliquotaOut:
    with SessionLocal() as session:
        if session.get(BonusFiscale, payload.bonus_code) is None:
            raise HTTPException(404, "Bonus non trovato")
        if payload.valido_al is not None and payload.valido_al < payload.valido_dal:
            raise HTTPException(400, "La data di fine validita' precede quella di inizio")
        esistente = (
            session.query(AliquotaBonus)
            .filter_by(
                bonus_code=payload.bonus_code,
                destinazione=payload.destinazione,
                valido_dal=payload.valido_dal,
            )
            .one_or_none()
        )
        if esistente is not None:
            raise HTTPException(409, "Esiste gia' un'aliquota per questo periodo e destinazione")
        row = AliquotaBonus(**payload.model_dump())
        session.add(row)
        session.commit()
        session.refresh(row)
        return AliquotaOut.model_validate(row, from_attributes=True)


@router.patch("/aliquote/{aliquota_id}", response_model=AliquotaOut)
def aggiorna_aliquota(
    aliquota_id: int, payload: AliquotaUpdate, _admin=Depends(require_admin)
) -> AliquotaOut:
    with SessionLocal() as session:
        row = session.get(AliquotaBonus, aliquota_id)
        if row is None:
            raise HTTPException(404, "Aliquota non trovata")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        if row.valido_al is not None and row.valido_al < row.valido_dal:
            raise HTTPException(400, "La data di fine validita' precede quella di inizio")
        session.commit()
        session.refresh(row)
        return AliquotaOut.model_validate(row, from_attributes=True)


@router.delete("/aliquote/{aliquota_id}", status_code=204)
def elimina_aliquota(aliquota_id: int, _admin=Depends(require_admin)) -> None:
    with SessionLocal() as session:
        row = session.get(AliquotaBonus, aliquota_id)
        if row is None:
            raise HTTPException(404, "Aliquota non trovata")
        session.delete(row)
        session.commit()


# --- Mapping categoria -> bonus --------------------------------------------


@router.get("/categorie", response_model=list[BonusCategoriaOut])
def lista_bonus_categorie(_admin=Depends(require_admin)) -> list[BonusCategoriaOut]:
    with SessionLocal() as session:
        rows = (
            session.execute(
                select(BonusCategoria).order_by(
                    BonusCategoria.bonus_code, BonusCategoria.categoria_code
                )
            )
            .scalars()
            .all()
        )
        return [BonusCategoriaOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/categorie", response_model=BonusCategoriaOut, status_code=201)
def crea_bonus_categoria(
    payload: BonusCategoriaIn, _admin=Depends(require_admin)
) -> BonusCategoriaOut:
    with SessionLocal() as session:
        if session.get(BonusFiscale, payload.bonus_code) is None:
            raise HTTPException(404, "Bonus non trovato")
        if session.get(Categoria, payload.categoria_code) is None:
            raise HTTPException(404, "Categoria non trovata")
        esistente = (
            session.query(BonusCategoria)
            .filter_by(bonus_code=payload.bonus_code, categoria_code=payload.categoria_code)
            .one_or_none()
        )
        if esistente is not None:
            raise HTTPException(409, "Questa categoria e' gia' mappata su questo bonus")

        _verifica_quote(
            session,
            categoria_code=payload.categoria_code,
            quota_aggiunta=payload.quota_ammissibile_pct,
        )

        row = BonusCategoria(**payload.model_dump())
        session.add(row)
        session.commit()
        session.refresh(row)
        return BonusCategoriaOut.model_validate(row, from_attributes=True)


@router.patch("/categorie/{mapping_id}", response_model=BonusCategoriaOut)
def aggiorna_bonus_categoria(
    mapping_id: int, payload: BonusCategoriaUpdate, _admin=Depends(require_admin)
) -> BonusCategoriaOut:
    with SessionLocal() as session:
        row = session.get(BonusCategoria, mapping_id)
        if row is None:
            raise HTTPException(404, "Mappatura non trovata")
        if payload.quota_ammissibile_pct is not None:
            # `escludi_id`: la riga che si sta riscrivendo non deve contarsi due
            # volte nel totale.
            _verifica_quote(
                session,
                categoria_code=row.categoria_code,
                quota_aggiunta=payload.quota_ammissibile_pct,
                escludi_id=row.id,
            )
            row.quota_ammissibile_pct = payload.quota_ammissibile_pct
        session.commit()
        session.refresh(row)
        return BonusCategoriaOut.model_validate(row, from_attributes=True)


@router.delete("/categorie/{mapping_id}", status_code=204)
def elimina_bonus_categoria(mapping_id: int, _admin=Depends(require_admin)) -> None:
    with SessionLocal() as session:
        row = session.get(BonusCategoria, mapping_id)
        if row is None:
            raise HTTPException(404, "Mappatura non trovata")
        session.delete(row)
        session.commit()


# --- Mapping extra -> bonus ------------------------------------------------
#
# Gemello del blocco categorie. Esiste perche' CSE/CSP e pratiche
# amministrative sono spesa detraibile ma non sono categorie: senza queste
# righe la detrazione esce sottostimata di tutto l'importo degli extra, in
# silenzio.


@router.get("/extra", response_model=list[BonusExtraOut])
def lista_bonus_extra(_admin=Depends(require_admin)) -> list[BonusExtraOut]:
    with SessionLocal() as session:
        rows = (
            session.execute(
                select(BonusExtra).order_by(BonusExtra.bonus_code, BonusExtra.extra_code)
            )
            .scalars()
            .all()
        )
        return [BonusExtraOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/extra", response_model=BonusExtraOut, status_code=201)
def crea_bonus_extra(payload: BonusExtraIn, _admin=Depends(require_admin)) -> BonusExtraOut:
    with SessionLocal() as session:
        if session.get(BonusFiscale, payload.bonus_code) is None:
            raise HTTPException(404, "Bonus non trovato")
        if session.get(Extra, payload.extra_code) is None:
            raise HTTPException(404, "Extra non trovato")
        esistente = (
            session.query(BonusExtra)
            .filter_by(bonus_code=payload.bonus_code, extra_code=payload.extra_code)
            .one_or_none()
        )
        if esistente is not None:
            raise HTTPException(409, "Questo extra e' gia' mappato su questo bonus")

        _verifica_quote_extra(
            session,
            extra_code=payload.extra_code,
            quota_aggiunta=payload.quota_ammissibile_pct,
        )

        row = BonusExtra(**payload.model_dump())
        session.add(row)
        session.commit()
        session.refresh(row)
        return BonusExtraOut.model_validate(row, from_attributes=True)


@router.patch("/extra/{mapping_id}", response_model=BonusExtraOut)
def aggiorna_bonus_extra(
    mapping_id: int, payload: BonusExtraUpdate, _admin=Depends(require_admin)
) -> BonusExtraOut:
    with SessionLocal() as session:
        row = session.get(BonusExtra, mapping_id)
        if row is None:
            raise HTTPException(404, "Mappatura non trovata")
        if payload.quota_ammissibile_pct is not None:
            _verifica_quote_extra(
                session,
                extra_code=row.extra_code,
                quota_aggiunta=payload.quota_ammissibile_pct,
                escludi_id=row.id,
            )
            row.quota_ammissibile_pct = payload.quota_ammissibile_pct
        session.commit()
        session.refresh(row)
        return BonusExtraOut.model_validate(row, from_attributes=True)


@router.delete("/extra/{mapping_id}", status_code=204)
def elimina_bonus_extra(mapping_id: int, _admin=Depends(require_admin)) -> None:
    with SessionLocal() as session:
        row = session.get(BonusExtra, mapping_id)
        if row is None:
            raise HTTPException(404, "Mappatura non trovata")
        session.delete(row)
        session.commit()
