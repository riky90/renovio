"""GET /api/v1/domande — il catalogo che alimenta il wizard.

Endpoint pubblico e di sola lettura: il wizard Free e' aperto agli anonimi,
esattamente come `POST /stima`. Il tier filtra *cosa* si vede, non *chi* puo'
chiedere — le domande Pro non sono un segreto, il dettaglio che producono si'
ed e' gia' dietro `require_pro`.

Questo endpoint e' la fine dell'hardcoding delle domande nel client: prima
vivevano in tre posti scollegati (`EstimateFormPro.tsx:DOMANDE`,
`DettaglioProView.tsx:FIELD_LABELS` e i campi dedicati di `StimaRequest`), e
aggiungerne una era un deploy di backend e frontend. Ora e' una riga in tabella.

I default arrivano gia' risolti per i metri quadri richiesti, e non come una
regola che il client ri-implementa: la stessa `attese_per_mq()` che qui produce
i default e' quella che nel motore fa da baseline allo scostamento. Se il client
ne avesse una copia, una fascia modificata dall'admin sposterebbe il calcolo
senza spostare cio' che l'utente vede — e lo scostamento apparirebbe da un
default che nessuno ha toccato.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.limiter import limiter
from app.models.domanda import Domanda, OpzioneDomanda
from app.schemas.domande import CatalogoDomandeOut, DomandaOut, OpzioneOut
from app.services.effetti import (
    CONTROLLI_NUMERICI,
    CONTROLLO_SCELTA_MULTIPLA,
    TIER_FREE,
    TIER_PRO,
    attese_per_mq,
)

router = APIRouter(prefix="/domande", tags=["domande"])

#: Cosa vede ciascun tier. `free` e' un sottoinsieme di `pro`, non un insieme
#: disgiunto: un utente Pro compila anche le domande Free, altrimenti il wizard
#: avrebbe due cataloghi da tenere allineati a mano.
TIER_VISIBILI = {TIER_FREE: (TIER_FREE,), TIER_PRO: (TIER_FREE, TIER_PRO)}


@router.get("", response_model=CatalogoDomandeOut)
@limiter.limit("60/minute")
def leggi_catalogo(
    request: Request,
    tier: str = Query(default=TIER_FREE, pattern="^(free|pro)$"),
    mq: int | None = Query(default=None, ge=1, le=10_000),
) -> CatalogoDomandeOut:
    """Catalogo + opzioni + default gia' risolti per `mq`.

    `mq` e' opzionale perche' il wizard carica il catalogo allo step 1, quando
    la superficie non e' ancora stata digitata. Senza `mq` gli stepper tornano
    con `valore_default=None`: il client mostra il campo vuoto e lo riempie alla
    seconda chiamata, invece di piantarci uno zero che l'utente prenderebbe per
    una risposta gia' data.
    """
    with SessionLocal() as session:
        attese = attese_per_mq(session, mq) if mq is not None else {}
        domande = _domande_attive(session, TIER_VISIBILI[tier])
        opzioni = _opzioni_per_domanda(session, [d.code for d in domande])

        return CatalogoDomandeOut(
            tier=tier,
            mq=mq,
            attese=attese,
            domande=[
                DomandaOut(
                    code=d.code,
                    testo=d.testo,
                    help=d.help,
                    tipo_controllo=d.tipo_controllo,
                    gruppo=d.gruppo,
                    ordine=d.ordine,
                    tier_minimo=d.tier_minimo,
                    attributo_code=d.attributo_code,
                    obbligatoria=d.obbligatoria,
                    visibile_se_domanda_code=d.visibile_se_domanda_code,
                    visibile_se_opzione_code=d.visibile_se_opzione_code,
                    valore_default=_default_di(d, opzioni.get(d.code, []), attese),
                    opzioni=[
                        OpzioneOut(
                            code=o.code,
                            etichetta=o.etichetta,
                            descrizione=o.descrizione,
                            immagine_url=o.immagine_url,
                            is_default=o.is_default,
                            ordine=o.ordine,
                        )
                        for o in opzioni.get(d.code, [])
                    ],
                )
                for d in domande
            ],
        )


def _domande_attive(session: Session, tiers: tuple[str, ...]) -> list[Domanda]:
    """Solo le attive, nell'ordine di curatela.

    L'ordinamento e' `(gruppo, ordine, code)` e non solo `ordine`: il wizard
    raggruppa per step, e due domande di gruppi diversi con lo stesso `ordine`
    devono comunque uscire in un ordine stabile. `code` chiude il pareggio, cosi'
    la lista non cambia fra due chiamate identiche.
    """
    return (
        session.query(Domanda)
        .filter(Domanda.attiva.is_(True), Domanda.tier_minimo.in_(tiers))
        .order_by(Domanda.gruppo, Domanda.ordine, Domanda.code)
        .all()
    )


def _opzioni_per_domanda(
    session: Session, codes: list[str]
) -> dict[str, list[OpzioneDomanda]]:
    """Tutte le opzioni ATTIVE in una query sola, raggruppate per domanda.

    D-27: un'opzione disattivata sparisce dal wizard pubblico. Query separata
    da quella di `services/effetti.py::risolvi_scelte` — stesso filtro, due
    consumatori diversi (wizard vs motore), non condivisa.
    """
    if not codes:
        return {}
    righe = (
        session.query(OpzioneDomanda)
        .filter(OpzioneDomanda.domanda_code.in_(codes), OpzioneDomanda.attiva.is_(True))
        .order_by(OpzioneDomanda.domanda_code, OpzioneDomanda.ordine, OpzioneDomanda.code)
        .all()
    )
    per_domanda: dict[str, list[OpzioneDomanda]] = {}
    for riga in righe:
        per_domanda.setdefault(riga.domanda_code, []).append(riga)
    return per_domanda


def _default_di(domanda: Domanda, opzioni: list[OpzioneDomanda], attese: dict):
    """Il default gia' risolto, nella forma che quel controllo si aspetta.

    Tre forme distinte e non una sola stringa: uno stepper vuole un numero, una
    scelta vuole un codice, una scelta multipla vuole una lista. Risolverle qui
    significa che il client non deve sapere che `attesa_immobile` esiste.

    Per gli stepper il default e' l'atteso della fascia — mai zero. Zero non e'
    "non lo so", e' una risposta: significa "nessun bagno", e sullo scostamento
    varrebbe come una correzione al ribasso di tutti i bagni previsti. Quando la
    fascia non c'e' si torna `None` e il campo resta vuoto, che e' l'unica cosa
    onesta da mostrare — lo stesso criterio per cui il motore, senza attesa, non
    applica alcuna correzione invece di inventarsi una baseline.
    """
    if domanda.tipo_controllo in CONTROLLI_NUMERICI:
        if domanda.attributo_code is None:
            return None
        return attese.get(domanda.attributo_code)

    if domanda.tipo_controllo == CONTROLLO_SCELTA_MULTIPLA:
        return [o.code for o in opzioni if o.is_default]

    scelto = next((o for o in opzioni if o.is_default), None)
    return scelto.code if scelto is not None else None
