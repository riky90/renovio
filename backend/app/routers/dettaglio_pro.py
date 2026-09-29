"""/api/v1/me/stime/{id}/dettaglio-pro — dettaglio bottom-up per
sottocategorie (PRO-01) dietro paywall server-side (PRO-02, D-08).

/api/v1/me/stime/{id}/pdf-pro — PDF Pro dettagliato (PDF-02). Chiama lo
STESSO `_compute_dettaglio()` interno usato dal GET JSON, con argomenti
identici (incluse `risposte_pro_json`), cosi' schermata e PDF non possono
divergere by-construction (03-RESEARCH.md Pitfall 2).

Ogni rotta sta dietro `Depends(require_pro)`: 401 anonimo (via
`get_current_user`), 403 Free autenticato ("Funzione riservata agli utenti
Pro"). Ownership-filter `id + user_id` -> `HTTPException(404)` (mai 403),
stesso pattern anti-IDOR di `routers/stime_salvate.py`.

A quel gate se ne affianca un SECONDO, ortogonale: `stima.tier` (congelato
al salvataggio) deve valere 'pro'. `require_pro` guarda l'abbonamento
CORRENTE, il tier guarda il piano con cui la stima e' NATA. Senza il
secondo, abbonarsi trasformerebbe retroattivamente in Pro tutte le stime
Free gia' salvate — che e' esattamente il bug che questa coppia di gate
chiude. Una stima Free non diventa Pro: si rifa'.

Il calcolo e' SEMPRE on-demand dallo snapshot (`citta`/`mq`/`tipo` colonne
scalari di `StimaSalvata`, mai da `risultato_json`, D-09): questa e'
l'asimmetria voluta rispetto al PDF Free (che legge solo lo snapshot
congelato) — qui non serve un secondo snapshot perche' il dettaglio Pro
deve restare aggiornabile dagli admin (Fase 4). Resta valida: cio' che il
tier congela e' la DISPONIBILITA' del dettaglio, non il suo calcolo.

Le risposte del pannello "Qualche dettaglio in piu'" (09-05: payload
generico `{risposte: {codice: valore}}`, validato contro il catalogo da
`valida_risposte_pro`) sono persistite in `stima.risposte_pro_json`: GET,
POST risposte e pdf-pro leggono/scrivono la STESSA colonna, cosi' la
schermata e il PDF Pro non possono divergere (03-RESEARCH.md Pitfall 3).
Dal 0010 vale lo stesso per i livelli di finitura in
`stima.livelli_pro_json`: stessa colonna per tutti e tre gli endpoint,
stessa garanzia.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.dependencies.auth import require_pro
from app.models.stima_salvata import StimaSalvata
from app.models.user import User
from app.models.catalogo import Categoria, Extra, LivelloFinitura
from app.models.domanda import OpzioneDomanda
from app.schemas.dettaglio_pro import (
    CategoriaDettagliataOut,
    CategoriaLivelloOut,
    DettaglioProOut,
    DomandaProOut,
    LetturaCategoriaOut,
    LivelloFinituraOut,
    OpzioneProOut,
    OpzioniProOut,
    RigaIvaOut,
    RiepilogoIvaOut,
    RisposteDomandeRequest,
    SottocategoriaOut,
    VoceOut,
)
from app.schemas.stima import BonusOut, ConfrontoFinitureOut, ExtraOut
from app.services.bonus_stima import CategoriaPerBonus, ExtraPerBonus, bonus_out_per_stima
from app.services.city_resolver import resolve_listino
from app.services.dettaglio_pro import (
    DettaglioProResult,
    DettaglioProService,
    DomandaConfiguratore,
    LivelliNonValidi,
    RisposteNonValide,
    domande_configuratore,
    valida_risposte_pro,
    validate_livelli,
)
from app.services.effetti import CONTROLLI_NUMERICI, DOMANDA_FINITURA
from app.services.risultato import (
    LetturaCategoria,
    Riepilogo,
    lettura_categorie_pro,
    livello_inferiore,
    riepilogo_iva_pro,
)
from app.services.pdf_service import PdfService, build_filename_pro

router = APIRouter(prefix="/me", tags=["dettaglio-pro"])


def _domanda_out(d: DomandaConfiguratore) -> DomandaProOut:
    """Mappa una `DomandaConfiguratore` del servizio nel DTO chiuso — riusato
    da `_to_out` (dettaglio-pro) e da `opzioni_pro` (09-11: le stesse domande
    servono anche al wizard Pro, PRIMA che una stima esista)."""
    return DomandaProOut(
        code=d.code,
        testo=d.testo,
        help=d.help,
        tipo_controllo=d.tipo_controllo,
        opzioni=[
            OpzioneProOut(
                code=o.code,
                etichetta=o.etichetta,
                descrizione=o.descrizione,
                is_default=o.is_default,
            )
            for o in d.opzioni
        ],
        valore=d.valore,
        valore_etichetta=d.valore_etichetta,
    )


def _to_out(
    calcolo: CalcoloDettaglioPro,
    livelli_disponibili: list[LivelloFinitura],
    budget_eur: int | None = None,
) -> DettaglioProOut:
    """Mappa campo-per-campo il calcolo nel DTO chiuso — mai `model_validate`
    su entita' ORM o dataclass interne."""
    result = calcolo.result
    risposte = calcolo.risposte_eco
    riepilogo = calcolo.riepilogo
    return DettaglioProOut(
        domande=[_domanda_out(d) for d in result.domande],
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
                                livello=voce.livello,
                            )
                            for voce in sotto.voci
                        ],
                        totale_min=sotto.totale_min,
                        totale_max=sotto.totale_max,
                    )
                    for sotto in cat.sottocategorie
                ],
                totale_min=cat.totale_min,
                totale_max=cat.totale_max,
                livello_scelto=cat.livello_scelto,
                livello_scelto_nome=cat.livello_scelto_nome,
            )
            for cat in result.categorie
        ],
        totale_min=result.totale_min,
        totale_max=result.totale_max,
        totale_ivato_min=riepilogo.totale_min,
        totale_ivato_max=riepilogo.totale_max,
        riepilogo_iva=RiepilogoIvaOut(
            imponibile_lavori_min=riepilogo.imponibile_lavori_min,
            imponibile_lavori_max=riepilogo.imponibile_lavori_max,
            righe_iva=[
                RigaIvaOut(iva_pct=r.iva_pct, min=r.min, max=r.max) for r in riepilogo.righe_iva
            ],
            extra=[
                ExtraOut(
                    code=e["code"], nome=e["nome"], importo=e["importo"], iva_pct=e["iva_pct"]
                )
                for e in riepilogo.extra
            ],
            extra_totale=riepilogo.extra_totale,
            totale_min=riepilogo.totale_min,
            totale_max=riepilogo.totale_max,
        ),
        lettura_categorie=[
            LetturaCategoriaOut(
                code=lc.code,
                eur_mq_min=lc.eur_mq_min,
                eur_mq_max=lc.eur_mq_max,
                peso_etichetta=lc.peso_etichetta,
                peso_fill_pct=lc.peso_fill_pct,
            )
            for lc in calcolo.lettura
        ],
        confronto_finiture=calcolo.confronto,
        finiture_al_minimo=calcolo.finiture_al_minimo,
        bonus=calcolo.bonus,
        budget_eur=budget_eur,
        risposte=risposte,
        risposte_salvate=calcolo.risposte_salvate,
        # L'eco si ricostruisce dal RISULTATO, non dall'input: cosi' contiene i
        # livelli davvero applicati, default inclusi.
        livelli={
            cat.code: cat.livello_scelto for cat in result.categorie if cat.livello_scelto
        },
        livelli_disponibili=[
            LivelloFinituraOut(
                code=row.code,
                nome=row.nome,
                ordine=row.ordine,
                descrizione=row.descrizione,
                is_default=row.is_default,
            )
            for row in livelli_disponibili
        ],
    )


def _get_owned_stima(session: Session, stima_id: int, current_user: User) -> StimaSalvata:
    """Ownership + tier. Due gate ortogonali, in quest'ordine:

    1. la riga non esiste o e' di un altro utente -> 404 (mai 403), cosi'
       l'esistenza non trapela (anti-IDOR, stesso pattern di
       `routers/stime_salvate.py`);
    2. la riga esiste ed e' dell'utente ma e' stata creata col piano Free ->
       403. Qui il 403 e' corretto proprio perche' l'ownership e' gia' stata
       verificata sopra: non si sta rivelando nulla che il chiamante non
       possieda gia'.

    Il secondo gate e' cio' che impedisce a una stima Free storica di
    diventare Pro quando l'utente si abbona (`Depends(require_pro)` guarda
    l'abbonamento CORRENTE, questo guarda il tier CONGELATO della stima).
    """
    stmt = select(StimaSalvata).where(
        StimaSalvata.id == stima_id,
        StimaSalvata.user_id == current_user.id,
    )
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Stima non trovata")
    if (row.tier or "free") != "pro":
        raise HTTPException(
            403,
            "Questa stima e' stata creata con il piano Free. "
            "Rifalla in versione Pro per il dettaglio voce per voce.",
        )
    return row


@dataclass(frozen=True)
class CalcoloDettaglioPro:
    """Esito unico di `_compute_dettaglio`: risultato del motore Pro piu' i
    derivati di lettura (riepilogo IVA, EUR/m2 e peso, confronto finiture)."""

    result: DettaglioProResult
    risposte_eco: dict
    risposte_salvate: bool
    riepilogo: Riepilogo
    lettura: list[LetturaCategoria]
    confronto: ConfrontoFinitureOut | None
    finiture_al_minimo: bool
    bonus: BonusOut | None = None


def _categorie_nel_totale(session: Session, result: DettaglioProResult) -> dict[str, Categoria]:
    """Categorie del risultato che fanno parte del totale lavori (stesso filtro
    di `opzioni_pro`): l'arredo non entra mai in IVA, pesi e confronto (D-08)."""
    codici = [c.code for c in result.categorie]
    if not codici:
        return {}
    rows = (
        session.query(Categoria)
        .filter(Categoria.code.in_(codici), Categoria.nel_totale_lavori.is_(True))
        .all()
    )
    return {c.code: c for c in rows}


def _riepilogo_pro(
    session: Session, result: DettaglioProResult, nel_totale: dict[str, Categoria]
) -> Riepilogo:
    extra_rows = session.query(Extra).filter(Extra.attivo.is_(True)).order_by(Extra.code).all()
    return riepilogo_iva_pro(
        [
            (c.totale_min, c.totale_max, nel_totale[c.code].iva_pct)
            for c in result.categorie
            if c.code in nel_totale
        ],
        [
            {"code": e.code, "nome": e.nome, "importo": e.importo, "iva_pct": e.iva_pct}
            for e in extra_rows
        ],
    )


def _confronto_pro(
    session: Session,
    listino,
    row: StimaSalvata,
    risposte_motore: dict,
    result: DettaglioProResult,
    nel_totale: dict[str, Categoria],
    riepilogo_attuale: Riepilogo,
) -> tuple[ConfrontoFinitureOut | None, bool]:
    """Ricalcolo vero del motore Pro con ogni categoria un livello sotto (D-10).
    Ritorna (confronto, finiture_al_minimo)."""
    livelli_db = _livelli_disponibili(session)
    opzioni = [(lv.code, lv.ordine, lv.is_default) for lv in livelli_db]
    ordine = {lv.code: lv.ordine for lv in livelli_db}
    scelte = [
        c for c in result.categorie if c.code in nel_totale and c.livello_scelto is not None
    ]
    if not scelte:
        return None, False

    livelli_conf: dict[str, str] = {}
    scesi = 0
    for c in scelte:
        inf = livello_inferiore(opzioni, c.livello_scelto)
        if inf is None:
            livelli_conf[c.code] = c.livello_scelto
        else:
            livelli_conf[c.code] = inf
            scesi += 1
    if not scesi:
        return None, True

    conf = DettaglioProService.compute(
        session, listino, row.mq, row.tipo, risposte_motore, livelli_conf
    )
    riepilogo_conf = _riepilogo_pro(session, conf, _categorie_nel_totale(session, conf))
    if riepilogo_conf.totale_max >= riepilogo_attuale.totale_max:
        return None, False

    # A4: il livello mostrato e' l'inferiore della categoria col livello scelto piu' alto.
    piu_alta = max(scelte, key=lambda c: ordine.get(c.livello_scelto, 0))
    livello_code = livelli_conf[piu_alta.code]
    etichetta = (
        session.query(OpzioneDomanda.etichetta)
        .filter(
            OpzioneDomanda.domanda_code == DOMANDA_FINITURA,
            OpzioneDomanda.code == livello_code,
            OpzioneDomanda.attiva.is_(True),
        )
        .scalar()
    )
    nome = etichetta or next(lv.nome for lv in livelli_db if lv.code == livello_code)
    return (
        ConfrontoFinitureOut(
            livello_code=livello_code,
            livello_nome=nome,
            totale_min=riepilogo_conf.totale_min,
            totale_max=riepilogo_conf.totale_max,
        ),
        False,
    )


def _bonus_pro(
    session: Session,
    row: StimaSalvata,
    result: DettaglioProResult,
    nel_totale: dict[str, Categoria],
    riepilogo: Riepilogo,
) -> BonusOut | None:
    """Bonus del Pro, calcolati sugli stessi importi del riepilogo IVA Pro:
    stessa fonte dati, nessun secondo punto di calcolo. Basi lorde per
    categoria con l'IVA arrotondata all'euro come in `riepilogo_iva_pro`, cosi'
    la somma delle basi riconcilia col Totale IVA inclusa. Arredo e destinazione
    vengono dallo snapshot (lettura difensiva)."""
    uno = Decimal("1")

    def lordo(importo: Decimal, iva_pct: Decimal) -> Decimal:
        return importo + (importo * iva_pct).quantize(uno, rounding=ROUND_HALF_UP)

    categorie = [
        CategoriaPerBonus(
            c.code,
            lordo(c.totale_min, nel_totale[c.code].iva_pct),
            lordo(c.totale_max, nel_totale[c.code].iva_pct),
        )
        for c in result.categorie
        if c.code in nel_totale
    ]
    extra = [
        ExtraPerBonus(
            e["code"], (e["importo"] * (1 + e["iva_pct"])).quantize(uno, rounding=ROUND_HALF_UP)
        )
        for e in riepilogo.extra
    ]

    snap = row.risultato_json if isinstance(row.risultato_json, dict) else {}
    arredo = None
    blocco = snap.get("arredo")
    if isinstance(blocco, dict):
        try:
            arredo = (Decimal(str(blocco["totale_min"])), Decimal(str(blocco["totale_max"])))
        except (KeyError, ArithmeticError, ValueError):
            arredo = None
    input_snap = snap.get("input")
    destinazione = (input_snap.get("destinazione") if isinstance(input_snap, dict) else None) or "prima_casa"

    return bonus_out_per_stima(
        session,
        categorie_lorde=categorie,
        extra_lordi=extra,
        arredo=arredo,
        destinazione=destinazione,
        totale_min=riepilogo.totale_min,
        totale_max=riepilogo.totale_max,
    )


def _compute_dettaglio(session: Session, row: StimaSalvata) -> CalcoloDettaglioPro:
    """Unico punto di calcolo condiviso da GET dettaglio-pro, POST risposte e
    GET pdf-pro — garantisce parita' numerica by-construction tra schermata
    e PDF (03-RESEARCH.md Pitfall 2), ora anche per IVA, lettura per categoria
    e confronto finiture: stessi argomenti (listino risolto da
    `row.citta`, `row.mq`, `row.tipo`, `row.risposte_pro_json`,
    `row.livelli_pro_json`).

    Aggiungere qui un secondo punto di calcolo — anche solo per il PDF — e' il
    modo piu' rapido di far divergere schermata e stampa.

    Le risposte per il MOTORE combinano quelle del wizard (congelate
    nello snapshot, `row.risultato_json["input"]["risposte"]`, es.
    bagni/porte/condizionatori risposti in Fase Free) con quelle del
    pannello Pro (`row.risposte_pro_json`) — vince il Pro se le stesse
    chiavi compaiono in entrambe. L'ECO che il client vede resta invece
    SOLO `row.risposte_pro_json`: e' il contratto del pannello (D-06), il
    wizard ha il suo proprio."""
    listino, _fallback = resolve_listino(session, row.citta)
    # La colonna NULL e la risposta {0, 0, 0} sono due stati diversi e vanno
    # tenuti distinti fin da qui: `or {}` serve al calcolo, il flag alla UI.
    risposte_salvate = row.risposte_pro_json is not None
    risposte_wizard = (
        row.risultato_json.get("input", {}).get("risposte")
        if isinstance(row.risultato_json, dict)
        else None
    )
    risposte_motore = {
        **(risposte_wizard if isinstance(risposte_wizard, dict) else {}),
        **(row.risposte_pro_json or {}),
    }
    risposte_eco = row.risposte_pro_json or {}
    livelli = row.livelli_pro_json or {}
    result = DettaglioProService.compute(
        session, listino, row.mq, row.tipo, risposte_motore, livelli
    )
    nel_totale = _categorie_nel_totale(session, result)
    riepilogo = _riepilogo_pro(session, result, nel_totale)
    lettura = lettura_categorie_pro(
        [(c.code, c.totale_min, c.totale_max) for c in result.categorie if c.code in nel_totale],
        row.mq,
    )
    confronto, al_minimo = _confronto_pro(
        session, listino, row, risposte_motore, result, nel_totale, riepilogo
    )
    return CalcoloDettaglioPro(
        result=result,
        risposte_eco=risposte_eco,
        risposte_salvate=risposte_salvate,
        riepilogo=riepilogo,
        lettura=lettura,
        confronto=confronto,
        finiture_al_minimo=al_minimo,
        bonus=_bonus_pro(session, row, result, nel_totale, riepilogo),
    )


def _livelli_disponibili(session: Session) -> list[LivelloFinitura]:
    return session.query(LivelloFinitura).order_by(LivelloFinitura.ordine).all()


@router.get("/opzioni-pro", response_model=OpzioniProOut)
def opzioni_pro(_current_user: User = Depends(require_pro)) -> OpzioniProOut:
    """Catalogo dei livelli + categorie che li ammettono, per il form Pro.

    Esiste separato da `GET /admin/dettaglio-pro/livelli` perche' quello e'
    dietro `require_admin`: gli stessi dati servono a un utente Pro qualunque,
    e riusare l'endpoint admin avrebbe significato allargarne il gate.

    Le categorie arrivano da `livello_selezionabile`, mai da un elenco di
    codici cablato nel client (regola 3 del CLAUDE.md: e' un dato).

    Filtrate anche su `nel_totale_lavori`: il selettore del livello serve a
    scegliere le voci del DETTAGLIO, e `E-ARREDO` nel dettaglio non c'e'
    (il suo livello lo sceglie la domanda del wizard, che governa il forfait
    Free). Offrirne il selettore vorrebbe dire mostrare un comando che non
    cambia niente sullo schermo.

    `domande` (09-11): le domande a scelta del configuratore Pro, per il
    wizard che deve disegnarle allo step 4 PRIMA che una stima esista. Filtro
    su `tipo_controllo` (ENG-02, nessun `if` sul codice di una domanda): le
    numeriche (bagni/porte/condizionatori) il wizard le chiede gia' allo step
    2 dal catalogo Free. `mq=1` e' lecito: il default di una scelta non
    dipende dai m2."""
    with SessionLocal() as session:
        categorie = (
            session.query(Categoria)
            .filter(
                Categoria.livello_selezionabile.is_(True),
                Categoria.nel_totale_lavori.is_(True),
            )
            .order_by(Categoria.ordine)
            .all()
        )
        domande = [
            d
            for d in domande_configuratore(session, mq=1, risposte={})
            if d.tipo_controllo not in CONTROLLI_NUMERICI
        ]
        return OpzioniProOut(
            categorie=[CategoriaLivelloOut(code=c.code, nome=c.nome) for c in categorie],
            livelli=[
                LivelloFinituraOut(
                    code=r.code,
                    nome=r.nome,
                    ordine=r.ordine,
                    descrizione=r.descrizione,
                    is_default=r.is_default,
                )
                for r in _livelli_disponibili(session)
            ],
            domande=[_domanda_out(d) for d in domande],
        )


@router.get("/stime/{stima_id}/dettaglio-pro", response_model=DettaglioProOut)
def dettaglio_pro(
    stima_id: int,
    current_user: User = Depends(require_pro),
) -> DettaglioProOut:
    with SessionLocal() as session:
        row = _get_owned_stima(session, stima_id, current_user)

        calcolo = _compute_dettaglio(session, row)

        return _to_out(calcolo, _livelli_disponibili(session), row.budget_eur)


@router.post("/stime/{stima_id}/dettaglio-pro/risposte", response_model=DettaglioProOut)
def salva_risposte_dettaglio_pro(
    stima_id: int,
    payload: RisposteDomandeRequest,
    current_user: User = Depends(require_pro),
) -> DettaglioProOut:
    with SessionLocal() as session:
        row = _get_owned_stima(session, stima_id, current_user)

        # `livelli` viaggia nello stesso payload ma vive in un'altra colonna:
        # va escluso da `risposte_pro_json`, che deve continuare a contenere
        # esattamente e solo le risposte del pannello, validate contro il
        # catalogo (T-09-14) — non il dict grezzo del client.
        try:
            risposte = valida_risposte_pro(session, dict(payload.risposte))
        except RisposteNonValide as exc:
            raise HTTPException(400, str(exc)) from exc
        row.risposte_pro_json = risposte
        if payload.livelli is not None:
            try:
                validate_livelli(session, payload.livelli)
            except LivelliNonValidi as exc:
                raise HTTPException(400, str(exc)) from exc
            row.livelli_pro_json = payload.livelli
        session.commit()
        session.refresh(row)

        calcolo = _compute_dettaglio(session, row)

        return _to_out(calcolo, _livelli_disponibili(session), row.budget_eur)


@router.get("/stime/{stima_id}/pdf-pro")
def scarica_pdf_pro(
    stima_id: int,
    current_user: User = Depends(require_pro),
) -> StreamingResponse:
    """PDF Pro dettagliato (PDF-02). Ricalcola LIVE tramite lo STESSO
    `_compute_dettaglio()` del GET JSON (parita' by-construction, Pitfall 2),
    poi lo rende via `PdfService.render_pro()` — mai una seconda logica di
    calcolo dentro il template/servizio PDF."""
    with SessionLocal() as session:
        row = _get_owned_stima(session, stima_id, current_user)

        calcolo = _compute_dettaglio(session, row)

        pdf_bytes = PdfService.render_pro(calcolo, row, current_user)
        filename = build_filename_pro(row)

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
