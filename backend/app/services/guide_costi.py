"""Fasce di prezzo per le guide pubbliche ai costi (SEO e ricerche AI).

Le guide del sito ("Quanto costa ristrutturare casa", "Costo rifacimento
bagno"...) mostrano cifre vere, calcolate dallo STESSO motore della stima
(`EstimationService` -> computo parametrico). Nessun numero e' scritto a mano
nel frontend: se l'admin cambia un prezzo o una regola, le guide seguono.

Uno scenario e' solo una scelta di risposte del catalogo domande: e'
contenuto editoriale ("rifare solo il bagno" = tutti gli altri interventi
spenti), non un prezzo, quindi vive qui e non in tabella. I prezzi restano in
database (regola #3).

Le cifre sono IVA inclusa, a range (regola #2), SENZA gli extra (CSE/CSP,
pratiche), che la guida riporta a parte. Nessun coefficiente impresa
(regola #1): `EstimationService` non lo espone.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.catalogo import Extra
from app.services.city_resolver import resolve_listino
from app.services.estimation import EstimationService

#: Tutti gli interventi spenti: la base degli scenari "solo X".
NESSUN_INTERVENTO: dict[str, Any] = {
    "interv_pavimenti": "mantieni",
    "interv_bagni": "nessuno",
    "interv_cucina": "no",
    "interv_elettrico": "nessuno",
    "idrico_collettore": "no",
    "interv_riscaldamento": "nessuno",
    "interv_clima": "nessuno",
    "interv_caldaia": "no",
    "interv_porte": "mantieni",
    "porta_blindata": "no",
    "interv_serramenti": "mantieni",
    "tinteggiatura": "no",
    "muri_lavori": "no",
    "controsoffitti_mq": 0,
}

MQ_RIFERIMENTO = 85
MQ_TABELLA = (50, 70, 85, 100, 120, 150)
TIPI = ("leggera", "moderata", "totale")
LIVELLI = ("base", "medio", "alto")
ETICHETTA_LIVELLO = {"base": "Finiture base", "medio": "Finiture medie", "alto": "Finiture di pregio"}


@dataclass(frozen=True)
class Scenario:
    code: str
    etichetta: str
    risposte: dict[str, Any]
    mq: int = MQ_RIFERIMENTO
    tipo: str = "moderata"


@dataclass(frozen=True)
class Guida:
    """Una guida e i suoi scenari, nell'ordine in cui la pagina li mostra."""

    code: str
    scenari: tuple[Scenario, ...] = field(default_factory=tuple)


def _solo(**risposte: Any) -> dict[str, Any]:
    return {**NESSUN_INTERVENTO, **risposte}


GUIDE: tuple[Guida, ...] = (
    Guida(
        "bagno",
        tuple(
            Scenario(f"bagno_{livello}", ETICHETTA_LIVELLO[livello], _solo(interv_bagni="uno", bagni=1, livello_finiture=livello))
            for livello in LIVELLI
        ),
    ),
    Guida(
        "cucina",
        (
            Scenario("cucina_induzione", "Impianti cucina, piano a induzione", _solo(interv_cucina="si", cucina_gas="no")),
            Scenario("cucina_gas", "Impianti cucina, piano a gas", _solo(interv_cucina="si", cucina_gas="si")),
        ),
    ),
    Guida(
        "impianto-elettrico",
        tuple(
            Scenario(f"elettrico_{modo}_{mq}", f"{'Rifacimento' if modo == 'rifacimento' else 'Modifica'}, {mq} m²", _solo(interv_elettrico=modo), mq=mq)
            for modo in ("modifica", "rifacimento")
            for mq in (50, 85, 120)
        ),
    ),
    Guida(
        "pavimenti",
        tuple(
            Scenario(
                f"pavimenti_{modo}_{pavimento}",
                f"{'Posa sopra l’esistente' if modo == 'sovrapponi' else 'Demolizione, massetto e posa'}, {nome}",
                _solo(interv_pavimenti=modo, tipo_pavimento=pavimento),
            )
            for modo in ("sovrapponi", "rifai")
            for pavimento, nome in (("gres", "gres"), ("parquet", "parquet"), ("laminato", "laminato"), ("vinilico_lvt", "vinilico LVT"))
        ),
    ),
    Guida(
        "serramenti",
        (
            Scenario("serramenti_senza_tapparelle", "Finestre e portefinestre in PVC", _solo(interv_serramenti="sostituisci", tapparelle="nessuna", finestre=5, portefinestre=1)),
            Scenario("serramenti_tapparelle_pvc", "Con tapparelle in PVC e cassonetti", _solo(interv_serramenti="sostituisci", tapparelle="pvc", finestre=5, portefinestre=1)),
            Scenario("serramenti_tapparelle_alluminio", "Con tapparelle in alluminio e cassonetti", _solo(interv_serramenti="sostituisci", tapparelle="alluminio", finestre=5, portefinestre=1)),
        ),
    ),
    Guida(
        "riscaldamento",
        (
            Scenario("riscaldamento_radiatori", "Radiatori nuovi e caldaia", _solo(interv_riscaldamento="radiatori", interv_caldaia="si")),
            Scenario("riscaldamento_pavimento", "Riscaldamento a pavimento", _solo(interv_riscaldamento="pavimento", interv_pavimenti="rifai")),
            Scenario("climatizzazione_split", "Climatizzazione con 2 split", _solo(interv_clima="split", condizionatori=2)),
        ),
    ),
)


def _eur(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _arrotonda_100(value: Decimal) -> int:
    """Le guide mostrano cifre arrotondate alle centinaia: e' una stima."""
    return int((value / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 100)


def _lavori(session: Session, listino, *, mq: int, tipo: str, risposte: dict[str, Any]) -> dict[str, Any]:
    """Totale lavori IVA inclusa a range, senza extra, e ripartizione per categoria."""
    risultato = EstimationService.compute(session, listino, mq=mq, tipo=tipo, risposte=risposte)
    minimo = sum((c.totale_min for c in risultato.categorie), Decimal("0"))
    massimo = sum((c.totale_max for c in risultato.categorie), Decimal("0"))
    return {
        "mq": mq,
        "tipo": tipo,
        "min": _arrotonda_100(minimo),
        "max": _arrotonda_100(massimo),
        "eur_mq_min": _eur(minimo / mq),
        "eur_mq_max": _eur(massimo / mq),
        "categorie": [
            {"code": c.code, "nome": c.nome, "min": _arrotonda_100(c.totale_min), "max": _arrotonda_100(c.totale_max)}
            for c in risultato.categorie
            if c.totale_max > 0
        ],
    }


def calcola_dati_guide(session: Session) -> dict[str, Any]:
    """Tutte le cifre delle guide, dal listino di default (Reggio Emilia)."""
    listino, _fallback = resolve_listino(session, "Reggio Emilia")

    per_tipo = {
        tipo: [_lavori(session, listino, mq=mq, tipo=tipo, risposte={}) for mq in MQ_TABELLA]
        for tipo in TIPI
    }
    per_livello = {
        livello: _lavori(session, listino, mq=MQ_RIFERIMENTO, tipo="totale", risposte={"livello_finiture": livello})
        for livello in LIVELLI
    }
    guide = {
        guida.code: [
            {"code": s.code, "etichetta": s.etichetta, **_lavori(session, listino, mq=s.mq, tipo=s.tipo, risposte=s.risposte)}
            for s in guida.scenari
        ]
        for guida in GUIDE
    }
    extra = [
        {"code": e.code, "nome": e.nome, "importo_ivato": _eur(e.importo * (1 + e.iva_pct))}
        for e in session.query(Extra).filter_by(attivo=True).order_by(Extra.code).all()
    ]
    return {
        "aggiornato_il": date.today().isoformat(),
        "citta_listino": listino.citta_riferimento or listino.nome,
        "mq_riferimento": MQ_RIFERIMENTO,
        "per_tipo": per_tipo,
        "per_livello": per_livello,
        "guide": guide,
        "extra": extra,
    }


_CACHE: dict[str, Any] = {}
_TTL_SECONDI = 600


def dati_guide_in_cache(session: Session) -> dict[str, Any]:
    """Le cifre cambiano solo quando l'admin tocca listino o regole: dieci
    minuti di cache evitano di ricalcolare ~60 stime a ogni visita di una
    guida."""
    adesso = time.monotonic()
    if _CACHE.get("scade", 0) > adesso:
        return _CACHE["dati"]
    dati = calcola_dati_guide(session)
    _CACHE.update(dati=dati, scade=adesso + _TTL_SECONDI)
    return dati
