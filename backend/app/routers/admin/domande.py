"""CRUD del catalogo domande + anteprima di stima (0014, ENG-02).

Il pezzo che conta di questo modulo non e' il CRUD: e' `POST /anteprima`.

Un motore a regole marcisce quando nessuno puo' vedere cosa fanno le regole
messe insieme. Le tre mitigazioni decise vanno costruite col motore, non dopo:
l'insieme chiuso di otto effetti (`services/effetti.py`), l'export Excel, e
questa anteprima — che date certe risposte dice quali effetti hanno sparato, con
quali numeri, e quanto si sposta il totale rispetto alla stima standard. Senza,
tarare ~50 coefficienti e' lavoro a occhio.

Ogni route ha `Depends(require_admin)`. NESSUNA CANCELLAZIONE FISICA (D-25,
D-39): non esiste un `DELETE` di domande, opzioni, effetti o attese in questo
modulo, ne' oggi ne' in futuro — l'unico modo di togliere una riga e'
disattivarla con `attiva=false` via `PATCH`. Una stima gia' salvata che cita
una domanda disattivata resta leggibile identica (D-29), perche' lo snapshot
vive in `stima_salvata.risultato_json` e non nelle righe del catalogo.

Le regole di integrita' (dipendenze di un'opzione, visibilita' condizionale,
opzione implicita degli stepper) vivono in `services/catalogo_domande.py`,
non qui: sono condivise con l'import Excel (piano 08.1-05), cosi' D-28 non e'
aggirabile ricaricando un file.

Nessuno schema di questo modulo espone il coefficiente impresa.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.auth import get_db, require_admin
from app.models.catalogo import Categoria
from app.models.domanda import AttesaImmobile, Domanda, EffettoOpzione, OpzioneDomanda
from app.schemas.admin_domande import (
    AnteprimaCategoriaOut,
    AnteprimaIn,
    AnteprimaOut,
    AttesaAdminCreateIn,
    AttesaAdminIn,
    AttesaAdminOut,
    DomandaAdminCreateIn,
    DomandaAdminIn,
    DomandaAdminOut,
    EffettoAdminCreateIn,
    EffettoAdminIn,
    EffettoAdminOut,
    EffettoTracciaOut,
    OpzioneAdminCreateIn,
    OpzioneAdminIn,
    OpzioneAdminOut,
)
from app.services.catalogo_domande import (
    assicura_opzione_valore,
    azzera_altri_default,
    valida_visibilita,
    verifica_dipendenze_opzione,
)
from app.services.city_resolver import resolve_listino
from app.services.effetti import (
    CONTROLLI,
    TIER_FREE,
    TIER_PRO,
    EffettoNonValido,
    attese_per_mq,
    risolvi_effetti_free,
    valida_effetto,
)
from app.services.estimation import EstimationService

router = APIRouter(prefix="/domande", tags=["admin-domande"])


def _to_domanda_out(row: Domanda) -> DomandaAdminOut:
    return DomandaAdminOut(
        code=row.code,
        testo=row.testo,
        help=row.help,
        tipo_controllo=row.tipo_controllo,
        gruppo=row.gruppo,
        ordine=row.ordine,
        tier_minimo=row.tier_minimo,
        attributo_code=row.attributo_code,
        obbligatoria=row.obbligatoria,
        visibile_se_domanda_code=row.visibile_se_domanda_code,
        visibile_se_opzione_code=row.visibile_se_opzione_code,
        attiva=row.attiva,
    )


def _to_opzione_out(row: OpzioneDomanda) -> OpzioneAdminOut:
    return OpzioneAdminOut(
        id=row.id,
        domanda_code=row.domanda_code,
        code=row.code,
        etichetta=row.etichetta,
        descrizione=row.descrizione,
        immagine_url=row.immagine_url,
        is_default=row.is_default,
        ordine=row.ordine,
        attiva=row.attiva,
    )


def _to_effetto_out(row: EffettoOpzione, opzione: OpzioneDomanda) -> EffettoAdminOut:
    return EffettoAdminOut(
        id=row.id,
        opzione_id=row.opzione_id,
        domanda_code=opzione.domanda_code,
        opzione_code=opzione.code,
        tipo_effetto=row.tipo_effetto,
        target_categoria_code=row.target_categoria_code,
        target_sottocategoria_id=row.target_sottocategoria_id,
        target_voce_id=row.target_voce_id,
        tipo_code=row.tipo_code,
        valore=row.valore,
        attivo=row.attivo,
    )


def _to_attesa_out(row: AttesaImmobile) -> AttesaAdminOut:
    return AttesaAdminOut(
        id=row.id,
        attributo_code=row.attributo_code,
        fascia_mq_min=row.fascia_mq_min,
        fascia_mq_max=row.fascia_mq_max,
        valore_atteso=row.valore_atteso,
        attiva=row.attiva,
    )


def _valida_domanda(tipo_controllo: str | None, tier_minimo: str | None) -> None:
    if tipo_controllo is not None and tipo_controllo not in CONTROLLI:
        raise HTTPException(
            400, f"Controllo sconosciuto. Ammessi: {', '.join(sorted(CONTROLLI))}."
        )
    if tier_minimo is not None and tier_minimo not in (TIER_FREE, TIER_PRO):
        raise HTTPException(400, f"Tier sconosciuto. Ammessi: {TIER_FREE}, {TIER_PRO}.")


# --- Domande ----------------------------------------------------------------


@router.get("", response_model=list[DomandaAdminOut])
def lista_domande(
    user=Depends(require_admin), db: Session = Depends(get_db)
) -> list[DomandaAdminOut]:
    rows = db.execute(select(Domanda).order_by(Domanda.ordine, Domanda.code)).scalars().all()
    return [_to_domanda_out(row) for row in rows]


@router.post("", response_model=DomandaAdminOut, status_code=201)
def crea_domanda(
    payload: DomandaAdminCreateIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> DomandaAdminOut:
    """Upsert per chiave naturale `code`, come `crea_extra`: una seconda POST
    con lo stesso code aggiorna invece di duplicare."""
    _valida_domanda(payload.tipo_controllo, payload.tier_minimo)
    motivo = valida_visibilita(
        db, payload.code, payload.visibile_se_domanda_code, payload.visibile_se_opzione_code
    )
    if motivo is not None:
        raise HTTPException(400, motivo)

    riga = db.get(Domanda, payload.code)
    if riga is None:
        riga = Domanda(code=payload.code)
        db.add(riga)
    for campo, valore in payload.model_dump(exclude={"code"}).items():
        setattr(riga, campo, valore)
    assicura_opzione_valore(db, riga)

    db.commit()
    db.refresh(riga)
    return _to_domanda_out(riga)


@router.patch("/{domanda_code}", response_model=DomandaAdminOut)
def modifica_domanda(
    domanda_code: str,
    payload: DomandaAdminIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> DomandaAdminOut:
    riga = db.get(Domanda, domanda_code)
    if riga is None:
        raise HTTPException(404, "Domanda non trovata")

    campi = payload.model_dump(exclude_unset=True)
    _valida_domanda(campi.get("tipo_controllo"), campi.get("tier_minimo"))
    vis_domanda = campi.get("visibile_se_domanda_code", riga.visibile_se_domanda_code)
    vis_opzione = campi.get("visibile_se_opzione_code", riga.visibile_se_opzione_code)
    motivo = valida_visibilita(db, domanda_code, vis_domanda, vis_opzione)
    if motivo is not None:
        raise HTTPException(400, motivo)

    for campo, valore in campi.items():
        setattr(riga, campo, valore)
    assicura_opzione_valore(db, riga)

    db.commit()
    db.refresh(riga)
    return _to_domanda_out(riga)


# --- Opzioni ----------------------------------------------------------------


@router.get("/opzioni", response_model=list[OpzioneAdminOut])
def lista_opzioni(
    domanda_code: str | None = None,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[OpzioneAdminOut]:
    stmt = select(OpzioneDomanda)
    if domanda_code is not None:
        stmt = stmt.filter_by(domanda_code=domanda_code)
    rows = (
        db.execute(
            stmt.order_by(
                OpzioneDomanda.domanda_code, OpzioneDomanda.ordine, OpzioneDomanda.id
            )
        )
        .scalars()
        .all()
    )
    return [_to_opzione_out(row) for row in rows]


@router.post("/opzioni", response_model=OpzioneAdminOut, status_code=201)
def crea_opzione(
    payload: OpzioneAdminCreateIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> OpzioneAdminOut:
    if db.get(Domanda, payload.domanda_code) is None:
        raise HTTPException(404, "Domanda non trovata")

    riga = (
        db.query(OpzioneDomanda)
        .filter_by(domanda_code=payload.domanda_code, code=payload.code)
        .one_or_none()
    )
    if riga is None:
        riga = OpzioneDomanda(domanda_code=payload.domanda_code, code=payload.code)
        db.add(riga)
    riga.etichetta = payload.etichetta
    riga.descrizione = payload.descrizione
    riga.immagine_url = payload.immagine_url
    riga.is_default = payload.is_default
    riga.ordine = payload.ordine
    riga.attiva = payload.attiva
    db.flush()

    if riga.is_default:
        azzera_altri_default(db, riga)

    db.commit()
    db.refresh(riga)
    return _to_opzione_out(riga)


@router.patch("/opzioni/{opzione_id}", response_model=OpzioneAdminOut)
def modifica_opzione(
    opzione_id: int,
    payload: OpzioneAdminIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> OpzioneAdminOut:
    """D-27/D-28: disattivare (`attiva: false`) un'opzione in uso e' rifiutato
    con un messaggio che nomina la dipendenza concreta, verificato PRIMA di
    scrivere nulla."""
    riga = db.get(OpzioneDomanda, opzione_id)
    if riga is None:
        raise HTTPException(404, "Opzione non trovata")

    campi = payload.model_dump(exclude_unset=True)
    attiva_finale = campi.get("attiva", riga.attiva)
    is_default_finale = campi.get("is_default", riga.is_default)

    if riga.attiva and not attiva_finale:
        motivo = verifica_dipendenze_opzione(db, riga, is_default=campi.get("is_default"))
        if motivo is not None:
            raise HTTPException(400, motivo)

    if is_default_finale and not attiva_finale:
        raise HTTPException(
            400, "Un'opzione non attiva non puo' essere la risposta predefinita."
        )

    for campo, valore in campi.items():
        setattr(riga, campo, valore)
    db.flush()

    if riga.is_default:
        azzera_altri_default(db, riga)

    db.commit()
    db.refresh(riga)
    return _to_opzione_out(riga)


# --- Effetti ----------------------------------------------------------------


@router.get("/effetti", response_model=list[EffettoAdminOut])
def lista_effetti(
    domanda_code: str | None = None,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[EffettoAdminOut]:
    stmt = select(EffettoOpzione, OpzioneDomanda).join(
        OpzioneDomanda, OpzioneDomanda.id == EffettoOpzione.opzione_id
    )
    if domanda_code is not None:
        stmt = stmt.filter(OpzioneDomanda.domanda_code == domanda_code)
    righe = db.execute(
        stmt.order_by(OpzioneDomanda.domanda_code, OpzioneDomanda.ordine, EffettoOpzione.id)
    ).all()
    return [_to_effetto_out(effetto, opzione) for effetto, opzione in righe]


@router.post("/effetti", response_model=EffettoAdminOut, status_code=201)
def crea_effetto(
    payload: EffettoAdminCreateIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> EffettoAdminOut:
    opzione = db.get(OpzioneDomanda, payload.opzione_id)
    if opzione is None:
        raise HTTPException(404, "Opzione non trovata")

    try:
        valida_effetto(
            payload.tipo_effetto,
            categoria_code=payload.target_categoria_code,
            sottocategoria_id=payload.target_sottocategoria_id,
            voce_id=payload.target_voce_id,
            valore=payload.valore,
        )
    except EffettoNonValido as exc:
        raise HTTPException(400, str(exc)) from exc

    riga = EffettoOpzione(**payload.model_dump())
    db.add(riga)
    db.commit()
    db.refresh(riga)
    return _to_effetto_out(riga, opzione)


@router.patch("/effetti/{effetto_id}", response_model=EffettoAdminOut)
def modifica_effetto(
    effetto_id: int,
    payload: EffettoAdminIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> EffettoAdminOut:
    """Si modificano solo valore, tipo_code e attivo.

    Tipo di effetto e bersaglio non si cambiano in corsa: sono l'identita' della
    riga, ed e' la chiave naturale con cui il seed la riconosce. Cambiarli
    equivale a scrivere un altro effetto, e allora tanto vale crearlo.
    """
    riga = db.get(EffettoOpzione, effetto_id)
    if riga is None:
        raise HTTPException(404, "Effetto non trovato")
    opzione = db.get(OpzioneDomanda, riga.opzione_id)

    campi = payload.model_dump(exclude_unset=True)
    for campo, valore in campi.items():
        setattr(riga, campo, valore)

    try:
        valida_effetto(
            riga.tipo_effetto,
            categoria_code=riga.target_categoria_code,
            sottocategoria_id=riga.target_sottocategoria_id,
            voce_id=riga.target_voce_id,
            valore=riga.valore,
        )
    except EffettoNonValido as exc:
        db.rollback()
        raise HTTPException(400, str(exc)) from exc

    db.commit()
    db.refresh(riga)
    return _to_effetto_out(riga, opzione)


# --- Attese -----------------------------------------------------------------


@router.get("/attese", response_model=list[AttesaAdminOut])
def lista_attese(
    user=Depends(require_admin), db: Session = Depends(get_db)
) -> list[AttesaAdminOut]:
    rows = (
        db.execute(
            select(AttesaImmobile).order_by(
                AttesaImmobile.attributo_code, AttesaImmobile.fascia_mq_min
            )
        )
        .scalars()
        .all()
    )
    return [_to_attesa_out(row) for row in rows]


@router.post("/attese", response_model=AttesaAdminOut, status_code=201)
def crea_attesa(
    payload: AttesaAdminCreateIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> AttesaAdminOut:
    if payload.fascia_mq_max < payload.fascia_mq_min:
        raise HTTPException(400, "La fascia finisce prima di cominciare.")

    riga = (
        db.query(AttesaImmobile)
        .filter_by(
            attributo_code=payload.attributo_code, fascia_mq_min=payload.fascia_mq_min
        )
        .one_or_none()
    )
    if riga is None:
        riga = AttesaImmobile(
            attributo_code=payload.attributo_code, fascia_mq_min=payload.fascia_mq_min
        )
        db.add(riga)
    riga.fascia_mq_max = payload.fascia_mq_max
    riga.valore_atteso = payload.valore_atteso
    riga.attiva = payload.attiva

    db.commit()
    db.refresh(riga)
    return _to_attesa_out(riga)


@router.patch("/attese/{attesa_id}", response_model=AttesaAdminOut)
def modifica_attesa(
    attesa_id: int,
    payload: AttesaAdminIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> AttesaAdminOut:
    riga = db.get(AttesaImmobile, attesa_id)
    if riga is None:
        raise HTTPException(404, "Attesa non trovata")

    for campo, valore in payload.model_dump(exclude_unset=True).items():
        setattr(riga, campo, valore)
    if riga.fascia_mq_max < riga.fascia_mq_min:
        db.rollback()
        raise HTTPException(400, "La fascia finisce prima di cominciare.")

    db.commit()
    db.refresh(riga)
    return _to_attesa_out(riga)


# --- Anteprima --------------------------------------------------------------


@router.post("/anteprima", response_model=AnteprimaOut)
def anteprima_stima(
    payload: AnteprimaIn,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> AnteprimaOut:
    """Date certe risposte: quali effetti sparano, con che numeri, e di quanto
    si sposta il totale rispetto alla stima senza catalogo.

    La base di confronto e' deliberatamente `risposte=None` (layer spento) e non
    `risposte={}` (layer acceso sui default). I due DEVONO coincidere, perche'
    l'opzione di default di ogni domanda non porta effetti; se qui compare un
    delta con un dizionario di risposte vuoto, vuol dire che quella regola di
    curatela e' stata violata — e questo endpoint e' il posto dove si vede,
    invece di scoprirlo dal fatto che tutte le stime sono cambiate.
    """
    listino, fallback = resolve_listino(db, payload.citta)

    base = EstimationService.compute(db, listino, mq=payload.mq, tipo=payload.tipo)
    corretta = EstimationService.compute(
        db, listino, mq=payload.mq, tipo=payload.tipo, risposte=payload.risposte
    )
    risoluzione = risolvi_effetti_free(
        db, mq=payload.mq, tipo=payload.tipo, risposte=payload.risposte
    )

    nomi = {
        c.code: c.nome
        for c in db.execute(select(Categoria).order_by(Categoria.ordine)).scalars()
    }
    base_per_code = {c.code: c for c in base.categorie}

    categorie = [
        AnteprimaCategoriaOut(
            code=c.code,
            nome=nomi.get(c.code, c.nome),
            base_min=base_per_code[c.code].totale_min,
            base_max=base_per_code[c.code].totale_max,
            totale_min=c.totale_min,
            totale_max=c.totale_max,
            delta_min=c.totale_min - base_per_code[c.code].totale_min,
            delta_max=c.totale_max - base_per_code[c.code].totale_max,
        )
        for c in corretta.categorie
    ]

    avvisi = [e.nota for e in risoluzione.applicati if not e.applicato and e.nota]
    if not payload.risposte and (
        corretta.totale_min != base.totale_min or corretta.totale_max != base.totale_max
    ):
        avvisi.insert(
            0,
            "Senza risposte il totale differisce dalla stima base: c'e' almeno "
            "un'opzione di default che porta effetti. Va tolto, altrimenti ogni "
            "stima cambia valore senza che nessuno l'abbia chiesto.",
        )

    return AnteprimaOut(
        citta=payload.citta,
        fallback=fallback,
        mq=payload.mq,
        tipo=payload.tipo,
        attese=attese_per_mq(db, payload.mq),
        categorie=categorie,
        base_totale_min=base.totale_min,
        base_totale_max=base.totale_max,
        totale_min=corretta.totale_min,
        totale_max=corretta.totale_max,
        delta_min=corretta.totale_min - base.totale_min,
        delta_max=corretta.totale_max - base.totale_max,
        effetti=[
            EffettoTracciaOut(
                domanda_code=e.domanda_code,
                opzione_code=e.opzione_code,
                tipo_effetto=e.tipo_effetto,
                categoria_code=e.categoria_code,
                valore=e.valore,
                unita=e.unita,
                contributo=e.contributo,
                applicato=e.applicato,
                nota=e.nota,
            )
            for e in risoluzione.applicati
        ],
        avvisi=avvisi,
    )
