"""Export del catalogo domande (D-05, D-06, D-07): un solo file a cinque
fogli — `domande`, `opzioni`, `effetti`, `attese`, `derivazioni` — uno per
tabella, senza denormalizzare. Nessun ramo `con_margine`: il catalogo domande
non contiene mai il coefficiente impresa (regola di dominio #1, `CLAUDE.md`),
quindi a differenza di `export_excel/parametri.py` questo modulo non ha
niente da nascondere dietro un flag opt-in.

`derivazioni` porta una colonna di contesto in piu' delle altre, `regola`: la
frase leggibile che spiega "quando X allora Y" senza dover leggere il codice
(D-06). E' l'unica volta che quella tabella e' visibile fuori dal seed.

La colonna `bersaglio` del foglio `effetti` (D-33, etichetta leggibile del
target di un effetto) e' aggiunta dal piano 08.1-03 Task 2, insieme alla
funzione che la calcola in `services/catalogo_domande.py`: non esiste ancora
in questo modulo al Task 1.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.domanda import (
    AttesaImmobile,
    DerivazioneRisposta,
    Domanda,
    EffettoOpzione,
    OpzioneDomanda,
)
from app.services.export_excel.workbook import nuovo_workbook, scrivi_foglio_dati, serializza

COLONNE_DOMANDE = [
    "id",
    "testo",
    "help",
    "tipo_controllo",
    "gruppo",
    "ordine",
    "tier_minimo",
    "attributo_code",
    "obbligatoria",
    "visibile_se_domanda_code",
    "visibile_se_opzione_code",
    "attiva",
]

COLONNE_OPZIONI = [
    "id",
    "domanda_code",
    "domanda_testo",
    "code",
    "etichetta",
    "descrizione",
    "immagine_url",
    "is_default",
    "ordine",
    "attiva",
]

COLONNE_EFFETTI = [
    "id",
    "opzione_id",
    "domanda_code",
    "opzione_code",
    "tipo_effetto",
    "target_categoria_code",
    "target_sottocategoria_id",
    "target_voce_id",
    "tipo_code",
    "valore",
    "attivo",
]

COLONNE_ATTESE = [
    "id",
    "attributo_code",
    "fascia_mq_min",
    "fascia_mq_max",
    "valore_atteso",
    "attiva",
]

COLONNE_DERIVAZIONI = [
    "id",
    "regola",
    "domanda_code",
    "quando_opzione_code",
    "da_domanda_code",
    "da_opzione_code",
    "opzione_code",
    "attiva",
]


def _righe_domande(db: Session) -> list[dict]:
    rows = db.query(Domanda).order_by(Domanda.ordine, Domanda.code).all()
    return [
        {
            "id": r.code,
            "testo": r.testo,
            "help": r.help,
            "tipo_controllo": r.tipo_controllo,
            "gruppo": r.gruppo,
            "ordine": r.ordine,
            "tier_minimo": r.tier_minimo,
            "attributo_code": r.attributo_code,
            "obbligatoria": r.obbligatoria,
            "visibile_se_domanda_code": r.visibile_se_domanda_code,
            "visibile_se_opzione_code": r.visibile_se_opzione_code,
            "attiva": r.attiva,
        }
        for r in rows
    ]


def _righe_opzioni(db: Session) -> list[dict]:
    rows = (
        db.query(OpzioneDomanda, Domanda)
        .join(Domanda, OpzioneDomanda.domanda_code == Domanda.code)
        .order_by(OpzioneDomanda.domanda_code, OpzioneDomanda.ordine, OpzioneDomanda.id)
        .all()
    )
    return [
        {
            "id": o.id,
            "domanda_code": o.domanda_code,
            "domanda_testo": domanda.testo,
            "code": o.code,
            "etichetta": o.etichetta,
            "descrizione": o.descrizione,
            "immagine_url": o.immagine_url,
            "is_default": o.is_default,
            "ordine": o.ordine,
            "attiva": o.attiva,
        }
        for o, domanda in rows
    ]


def _righe_effetti(db: Session) -> list[dict]:
    rows = (
        db.query(EffettoOpzione, OpzioneDomanda)
        .join(OpzioneDomanda, EffettoOpzione.opzione_id == OpzioneDomanda.id)
        .order_by(EffettoOpzione.id)
        .all()
    )
    return [
        {
            "id": e.id,
            "opzione_id": e.opzione_id,
            "domanda_code": opzione.domanda_code,
            "opzione_code": opzione.code,
            "tipo_effetto": e.tipo_effetto,
            "target_categoria_code": e.target_categoria_code,
            "target_sottocategoria_id": e.target_sottocategoria_id,
            "target_voce_id": e.target_voce_id,
            "tipo_code": e.tipo_code,
            "valore": e.valore,
            "attivo": e.attivo,
        }
        for e, opzione in rows
    ]


def _righe_attese(db: Session) -> list[dict]:
    rows = (
        db.query(AttesaImmobile)
        .order_by(AttesaImmobile.attributo_code, AttesaImmobile.fascia_mq_min)
        .all()
    )
    return [
        {
            "id": r.id,
            "attributo_code": r.attributo_code,
            "fascia_mq_min": r.fascia_mq_min,
            "fascia_mq_max": r.fascia_mq_max,
            "valore_atteso": r.valore_atteso,
            "attiva": r.attiva,
        }
        for r in rows
    ]


def _regola_derivazione(
    d: DerivazioneRisposta,
    testi_domanda: dict[str, str],
    etichette_opzione: dict[tuple[str, str], str],
) -> str:
    """Frase leggibile 'se X = A e Y = B -> C' (D-06). Fallback al codice
    grezzo quando testo/etichetta non si trovano: una derivazione rotta
    (punta a una domanda o un'opzione sparita) resta esportabile, non
    solleva."""
    da_domanda_testo = testi_domanda.get(d.da_domanda_code, d.da_domanda_code)
    da_opzione_etichetta = etichette_opzione.get(
        (d.da_domanda_code, d.da_opzione_code), d.da_opzione_code
    )
    domanda_testo = testi_domanda.get(d.domanda_code, d.domanda_code)
    quando_opzione_etichetta = etichette_opzione.get(
        (d.domanda_code, d.quando_opzione_code), d.quando_opzione_code
    )
    opzione_etichetta = etichette_opzione.get(
        (d.domanda_code, d.opzione_code), d.opzione_code
    )
    return (
        f"se «{da_domanda_testo}» = «{da_opzione_etichetta}» "
        f"e «{domanda_testo}» = «{quando_opzione_etichetta}» "
        f"→ «{opzione_etichetta}»"
    )


def _righe_derivazioni(db: Session) -> list[dict]:
    rows = db.query(DerivazioneRisposta).order_by(DerivazioneRisposta.id).all()
    if not rows:
        return []

    codici_domanda = {r.domanda_code for r in rows} | {r.da_domanda_code for r in rows}
    testi_domanda = {
        d.code: d.testo
        for d in db.query(Domanda).filter(Domanda.code.in_(codici_domanda)).all()
    }
    etichette_opzione = {
        (o.domanda_code, o.code): o.etichetta
        for o in db.query(OpzioneDomanda)
        .filter(OpzioneDomanda.domanda_code.in_(codici_domanda))
        .all()
    }

    return [
        {
            "id": r.id,
            "regola": _regola_derivazione(r, testi_domanda, etichette_opzione),
            "domanda_code": r.domanda_code,
            "quando_opzione_code": r.quando_opzione_code,
            "da_domanda_code": r.da_domanda_code,
            "da_opzione_code": r.da_opzione_code,
            "opzione_code": r.opzione_code,
            "attiva": r.attiva,
        }
        for r in rows
    ]


def build_workbook_domande(db: Session) -> tuple[bytes, int]:
    """Costruisce il workbook a cinque fogli del catalogo domande.

    Mai `con_margine`: il catalogo non contiene margine impresa in nessuna
    forma, quindi il workbook e' sempre nella sua unica versione (nessun
    foglio `AVVISO`).

    Ritorna (bytes del file, numero totale di righe dati scritte sui cinque
    fogli) — il totale alimenta la riga di audit `export_log`.
    """
    wb = nuovo_workbook()

    n_righe = 0
    n_righe += scrivi_foglio_dati(
        wb, nome="domande", colonne=COLONNE_DOMANDE, righe=_righe_domande(db)
    )
    n_righe += scrivi_foglio_dati(
        wb, nome="opzioni", colonne=COLONNE_OPZIONI, righe=_righe_opzioni(db)
    )
    n_righe += scrivi_foglio_dati(
        wb, nome="effetti", colonne=COLONNE_EFFETTI, righe=_righe_effetti(db)
    )
    n_righe += scrivi_foglio_dati(
        wb, nome="attese", colonne=COLONNE_ATTESE, righe=_righe_attese(db)
    )
    n_righe += scrivi_foglio_dati(
        wb, nome="derivazioni", colonne=COLONNE_DERIVAZIONI, righe=_righe_derivazioni(db)
    )

    return serializza(wb), n_righe
