"""Regole di integrita' del catalogo domande, condivise dal router admin e
(piano 08.1-05) dall'import Excel.

Il punto di stare qui e non dentro `routers/admin/domande.py`: D-28 non deve
essere aggirabile ricaricando un file. Un'unica funzione decide se
un'opzione si puo' disattivare, chiamata da entrambi i percorsi di
scrittura.

Nessuna di queste funzioni fa commit: chi le chiama decide quando la
transazione si chiude, cosi' un rifiuto (return non-None / eccezione)
lascia la sessione pulita per il chiamante.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.domanda import DerivazioneRisposta, Domanda, OpzioneDomanda
from app.services.effetti import CONTROLLI_NUMERICI, OPZIONE_VALORE


def verifica_dipendenze_opzione(
    db: Session, opzione: OpzioneDomanda, *, is_default: bool | None = None
) -> str | None:
    """Il motivo per cui `opzione` non si puo' disattivare, o `None`.

    Raccoglie TUTTE le dipendenze, non la prima trovata, e le unisce con
    "; ": un'opzione puo' essere insieme il default della sua domanda e il
    trigger di una derivazione, e l'admin deve vederle entrambe in un colpo
    solo invece di sistemarle una alla volta scoprendole per tentativi.

    `is_default` sovrascrive `opzione.is_default`: serve quando la stessa
    scrittura che disattiva l'opzione cambia anche il suo stato di default
    (PATCH con `{attiva: false, is_default: false}` non deve lamentarsi del
    default che sta gia' togliendo).
    """
    motivi: list[str] = []

    e_default = opzione.is_default if is_default is None else is_default
    if e_default:
        domanda = db.get(Domanda, opzione.domanda_code)
        motivi.append(f"e' la risposta predefinita di «{domanda.testo}»")

    derivazioni = (
        db.query(DerivazioneRisposta)
        .filter(DerivazioneRisposta.attiva.is_(True))
        .filter(
            (
                (DerivazioneRisposta.domanda_code == opzione.domanda_code)
                & (
                    (DerivazioneRisposta.quando_opzione_code == opzione.code)
                    | (DerivazioneRisposta.opzione_code == opzione.code)
                )
            )
            | (
                (DerivazioneRisposta.da_domanda_code == opzione.domanda_code)
                & (DerivazioneRisposta.da_opzione_code == opzione.code)
            )
        )
        .all()
    )
    for d in derivazioni:
        dedotta = db.get(Domanda, d.domanda_code)
        sorgente = db.get(Domanda, d.da_domanda_code)
        motivi.append(f"la usa la derivazione «{dedotta.testo}» <- «{sorgente.testo}»")

    domande_gate = (
        db.query(Domanda)
        .filter(
            Domanda.attiva.is_(True),
            Domanda.visibile_se_domanda_code == opzione.domanda_code,
            Domanda.visibile_se_opzione_code == opzione.code,
        )
        .all()
    )
    for d in domande_gate:
        motivi.append(f"e' la condizione di visibilita' di «{d.testo}»")

    if not motivi:
        return None
    return f"Non si puo' disattivare «{opzione.etichetta}»: " + "; ".join(motivi)


def valida_visibilita(
    db: Session,
    domanda_code: str,
    vis_domanda: str | None,
    vis_opzione: str | None,
) -> str | None:
    """Il motivo per cui la visibilita' condizionale non e' valida, o `None`.

    D-37: niente codici inesistenti nemmeno via API — la stessa disciplina
    che il form applica con due select collegati vale anche qui, perche' il
    form non e' l'unico chiamante.
    """
    if (vis_domanda is None) != (vis_opzione is None):
        return (
            "La visibilita' condizionale richiede sia la domanda sia "
            "l'opzione, oppure nessuna delle due."
        )
    if vis_domanda is None:
        return None
    if vis_domanda == domanda_code:
        return "Una domanda non puo' dipendere da se stessa."

    domanda_gate = db.get(Domanda, vis_domanda)
    if domanda_gate is None:
        return f"La domanda {vis_domanda!r} non esiste."

    opzione_gate = (
        db.query(OpzioneDomanda)
        .filter_by(domanda_code=vis_domanda, code=vis_opzione)
        .one_or_none()
    )
    if opzione_gate is None or not opzione_gate.attiva:
        return (
            f"L'opzione {vis_opzione!r} non e' un'opzione attiva di "
            f"«{domanda_gate.testo}»."
        )
    return None


def assicura_opzione_valore(db: Session, domanda: Domanda) -> None:
    """Crea l'opzione implicita `code='valore'` per uno stepper/numero (D-35).

    Convenzione del seed (`seed_data/seed-domande.json`): `etichetta='Valore'`,
    `is_default=False`, `ordine=0`. Idempotente — non fa nulla se l'opzione
    esiste gia', cosi' si puo' chiamare anche quando un PATCH porta una
    domanda gia' esistente verso un controllo numerico.
    """
    if domanda.tipo_controllo not in CONTROLLI_NUMERICI:
        return
    esiste = (
        db.query(OpzioneDomanda)
        .filter_by(domanda_code=domanda.code, code=OPZIONE_VALORE)
        .one_or_none()
    )
    if esiste is not None:
        return
    db.add(
        OpzioneDomanda(
            domanda_code=domanda.code,
            code=OPZIONE_VALORE,
            etichetta="Valore",
            is_default=False,
            ordine=0,
            attiva=True,
        )
    )
    db.flush()


def azzera_altri_default(db: Session, opzione: OpzioneDomanda) -> None:
    """Il default e' un radio button, non una casella.

    Due default sulla stessa domanda renderebbero il risultato dipendente
    dall'ordine delle righe; zero default farebbero sparire gli effetti di
    una domanda non risposta. Si impone qui, dove la scrittura avviene,
    invece di inseguirlo con un vincolo che l'admin non saprebbe leggere.
    """
    db.query(OpzioneDomanda).filter(
        OpzioneDomanda.domanda_code == opzione.domanda_code,
        OpzioneDomanda.id != opzione.id,
    ).update({OpzioneDomanda.is_default: False}, synchronize_session=False)
