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

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.dependencies.auth import require_pro
from app.models.stima_salvata import StimaSalvata
from app.models.user import User
from app.models.catalogo import Categoria, LivelloFinitura
from app.schemas.dettaglio_pro import (
    CategoriaDettagliataOut,
    CategoriaLivelloOut,
    DettaglioProOut,
    DomandaProOut,
    LivelloFinituraOut,
    OpzioneProOut,
    OpzioniProOut,
    RisposteDomandeRequest,
    SottocategoriaOut,
    VoceOut,
)
from app.services.city_resolver import resolve_listino
from app.services.dettaglio_pro import (
    DettaglioProResult,
    DettaglioProService,
    LivelliNonValidi,
    RisposteNonValide,
    valida_risposte_pro,
    validate_livelli,
)
from app.services.pdf_service import PdfService, build_filename_pro

router = APIRouter(prefix="/me", tags=["dettaglio-pro"])


def _to_out(
    result: DettaglioProResult,
    risposte: dict,
    livelli_disponibili: list[LivelloFinitura],
    risposte_salvate: bool = False,
) -> DettaglioProOut:
    """Mappa campo-per-campo il risultato del servizio nel DTO chiuso — mai
    `model_validate` su entita' ORM o dataclass interne."""
    return DettaglioProOut(
        domande=[
            DomandaProOut(
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
            for d in result.domande
        ],
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
        risposte=risposte,
        risposte_salvate=risposte_salvate,
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


def _compute_dettaglio(
    session: Session, row: StimaSalvata
) -> tuple[DettaglioProResult, dict, bool]:
    """Unico punto di calcolo condiviso da GET dettaglio-pro, POST risposte e
    GET pdf-pro — garantisce parita' numerica by-construction tra schermata
    e PDF (03-RESEARCH.md Pitfall 2): stessi argomenti (listino risolto da
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
    return result, risposte_eco, risposte_salvate


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
    cambia niente sullo schermo."""
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
        )


@router.get("/stime/{stima_id}/dettaglio-pro", response_model=DettaglioProOut)
def dettaglio_pro(
    stima_id: int,
    current_user: User = Depends(require_pro),
) -> DettaglioProOut:
    with SessionLocal() as session:
        row = _get_owned_stima(session, stima_id, current_user)

        result, risposte, risposte_salvate = _compute_dettaglio(session, row)

        return _to_out(result, risposte, _livelli_disponibili(session), risposte_salvate)


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

        result, risposte, risposte_salvate = _compute_dettaglio(session, row)

        return _to_out(result, risposte, _livelli_disponibili(session), risposte_salvate)


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

        result, _risposte, _salvate = _compute_dettaglio(session, row)

        pdf_bytes = PdfService.render_pro(result, row, current_user)
        filename = build_filename_pro(row)

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
