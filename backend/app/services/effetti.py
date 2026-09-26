"""Risoluzione del catalogo domande: risposte dell'utente -> correzioni al calcolo.

Questo modulo e' l'unico posto in cui una risposta diventa aritmetica. Il motore
Free (`estimation.py`) e, dalla Fase 5, il motore Pro (`dettaglio_pro.py`) lo
importano e applicano cio' che torna: nessun `if` sul codice di una domanda vive
dentro i motori.

GLI OTTO TIPI DI EFFETTO — insieme chiuso, deliberatamente piccolo
--------------------------------------------------------------------
Niente espressioni, niente formule in tabella. Un motore a regole marcisce
quando in una cella si puo' scrivere qualunque cosa; qui ogni tipo ha
un'aritmetica nota, e aggiungerne uno e' una decisione di design, non una riga
di configurazione.

  Free  moltiplicatore_categoria  fattore sul base_eur_mq della categoria
        eur_mq_categoria          euro per m2 additivi sulla categoria
        eur_fisso_categoria       euro una tantum additivi sulla categoria
        eur_per_scostamento       euro per unita' di scostamento dall'atteso
  Pro   includi                   la voce entra nel computo
        escludi                   la voce/sottocategoria/categoria esce
        fattore_quantita          moltiplica la quantita' calcolata
        quantita_per_unita        quantita' = risposta numerica x valore

ORDINE DI RISOLUZIONE DEL MOTORE FREE (contratto, replicato in estimation.py)
-----------------------------------------------------------------------------
  1. base = base_eur_mq x moltiplicatore_tipo x mq
  2. base = base x PRODOTTO(moltiplicatore_categoria)
  3. se il prodotto al punto 2 e' 0 -> categoria a 0, si saltano 4 e 5
  4. base = base + SOMMA(eur_mq_categoria x mq)
  5. base = base + SOMMA(scostamento x eur_per_scostamento)
  6. imponibile = max(base, 0)

I moltiplicatori agiscono PRIMA dei termini additivi: un euro/m2 di
efficientamento non deve essere scalato da un moltiplicatore che riguarda
tutt'altro (l'eta' dell'immobile, il tipo di accesso al cantiere).

PERCHE' LO SCOSTAMENTO E NON IL VALORE ASSOLUTO
------------------------------------------------
Le correzioni numeriche si applicano alla DIFFERENZA fra la risposta e il valore
atteso per quella fascia di metri quadri (`attesa_immobile`). E' cio' che rende
il layer neutro a riposo: un 85 m2 con i valori standard ha scostamento zero su
ogni attributo e costa esattamente quanto costava prima che questo modulo
esistesse. L'oracolo primario (47.985-70.575) e' protetto per costruzione, non
per fortuna.

SOLO GLI EFFETTI PER-UNITA' SCALANO CON UN NUMERO
--------------------------------------------------
`eur_per_scostamento` (Free) e `quantita_per_unita` (Pro) moltiplicano il loro
valore per la risposta numerica. Tutti gli altri usano il valore cosi' com'e',
anche quando pendono da uno stepper. Se un effetto deve crescere col numero —
il piano dell'immobile, i metri di muro da recuperare — si modella come
`eur_per_scostamento`, non come moltiplicatore.

NESSUN COEFFICIENTE IMPRESA
---------------------------
Tutti i valori qui sono in euro-cliente, come `listino_categoria.base_eur_mq`
(regola non negoziabile #1). Il margine impresa non entra in questo layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.catalogo import Categoria
from app.models.dettaglio_pro import Sottocategoria, Voce
from app.models.domanda import (
    AttesaImmobile,
    DerivazioneRisposta,
    Domanda,
    EffettoOpzione,
    OpzioneDomanda,
)

# --- vocabolario chiuso -----------------------------------------------------

TIPO_MOLTIPLICATORE_CATEGORIA = "moltiplicatore_categoria"
TIPO_EUR_MQ_CATEGORIA = "eur_mq_categoria"
TIPO_EUR_FISSO_CATEGORIA = "eur_fisso_categoria"
TIPO_EUR_PER_SCOSTAMENTO = "eur_per_scostamento"
TIPO_INCLUDI = "includi"
TIPO_ESCLUDI = "escludi"
TIPO_FATTORE_QUANTITA = "fattore_quantita"
TIPO_QUANTITA_PER_UNITA = "quantita_per_unita"

TIPI_EFFETTO_FREE = frozenset(
    {
        TIPO_MOLTIPLICATORE_CATEGORIA,
        TIPO_EUR_MQ_CATEGORIA,
        TIPO_EUR_FISSO_CATEGORIA,
        TIPO_EUR_PER_SCOSTAMENTO,
    }
)
TIPI_EFFETTO_PRO = frozenset(
    {TIPO_INCLUDI, TIPO_ESCLUDI, TIPO_FATTORE_QUANTITA, TIPO_QUANTITA_PER_UNITA}
)
TIPI_EFFETTO = TIPI_EFFETTO_FREE | TIPI_EFFETTO_PRO

# Effetti che moltiplicano il proprio valore per la risposta numerica.
TIPI_EFFETTO_PER_UNITA = frozenset({TIPO_EUR_PER_SCOSTAMENTO, TIPO_QUANTITA_PER_UNITA})

# Effetti senza valore numerico: la presenza della riga E' l'effetto.
TIPI_EFFETTO_SENZA_VALORE = frozenset({TIPO_INCLUDI, TIPO_ESCLUDI})

CONTROLLI_NUMERICI = frozenset({"stepper", "numero"})
CONTROLLI_SCELTA_SINGOLA = frozenset({"scelta_singola", "toggle"})
CONTROLLO_SCELTA_MULTIPLA = "scelta_multipla"
CONTROLLI = CONTROLLI_NUMERICI | CONTROLLI_SCELTA_SINGOLA | {CONTROLLO_SCELTA_MULTIPLA}

TIER_FREE = "free"
TIER_PRO = "pro"

#: Per convenzione, uno stepper/numero ha una sola opzione con questo codice.
OPZIONE_VALORE = "valore"

#: Per convenzione (stesso precedente di OPZIONE_VALORE, non regole di
#: business): la domanda del catalogo che rappresenta i livelli di
#: `livello_finitura`. Il motore Pro (Fase 09-03) instrada la scelta per
#: categoria verso questa domanda.
DOMANDA_FINITURA = "finitura"

#: Per convenzione: il gruppo delle domande che si rispondono solo nel
#: pannello del dettaglio Pro (D-06). Il wizard (`_domande_attive`) le esclude.
GRUPPO_CONFIGURATORE_PRO = "configuratore_pro"

#: Bersagli ammessi per ciascun tipo di effetto.
TARGET_AMMESSI: dict[str, frozenset[str]] = {
    TIPO_MOLTIPLICATORE_CATEGORIA: frozenset({"categoria"}),
    TIPO_EUR_MQ_CATEGORIA: frozenset({"categoria"}),
    TIPO_EUR_FISSO_CATEGORIA: frozenset({"categoria"}),
    TIPO_EUR_PER_SCOSTAMENTO: frozenset({"categoria"}),
    TIPO_INCLUDI: frozenset({"sottocategoria", "voce"}),
    TIPO_ESCLUDI: frozenset({"categoria", "sottocategoria", "voce"}),
    TIPO_FATTORE_QUANTITA: frozenset({"sottocategoria", "voce"}),
    TIPO_QUANTITA_PER_UNITA: frozenset({"voce"}),
}


class EffettoNonValido(ValueError):
    """Un effetto malformato. Sollevata dalla validazione admin, mai dal motore:
    a runtime una riga incoerente viene saltata e segnalata nell'anteprima,
    perche' una stima non deve andare in 500 per un errore di curatela."""


# --- risultati --------------------------------------------------------------


@dataclass(frozen=True)
class EffettoApplicato:
    """Una riga della traccia: cosa ha sparato, con che numeri, e se e' stata
    applicata davvero. E' il materiale dell'anteprima admin — lo strumento con
    cui si tara. Senza, la curatela e' a occhio."""

    domanda_code: str
    opzione_code: str
    tipo_effetto: str
    categoria_code: str | None
    valore: Decimal | None
    unita: Decimal | None
    contributo: Decimal | None
    applicato: bool
    nota: str | None = None


@dataclass(frozen=True)
class CorrezioniCategoria:
    """Le quattro correzioni Free gia' aggregate per una categoria.

    `eur_fisso` e' l'importo una tantum: non scala con i m2 e non scala con lo
    scostamento. Esiste perche' un impianto fotovoltaico e una caldaia costano
    quello che costano — spinti dentro `eur_mq` darebbero una caldaia da 3.800
    euro su 85 m2 e da 9.000 su 200, che e' visibilmente falso.
    """

    moltiplicatore: Decimal = Decimal("1")
    eur_mq: Decimal = Decimal("0")
    eur_fisso: Decimal = Decimal("0")
    eur_scostamento: Decimal = Decimal("0")


@dataclass(frozen=True)
class RisoluzioneFree:
    correzioni: dict[str, CorrezioniCategoria]
    applicati: list[EffettoApplicato]

    @property
    def attiva(self) -> bool:
        return bool(self.correzioni)


@dataclass(frozen=True)
class ScelteRisolte:
    """Il catalogo dopo aver applicato risposte, default e visibilita'.

    `domande` sono quelle attive del tier, in ordine; `opzioni` sono quelle
    effettivamente scelte e VISIBILI. Chi consuma questo oggetto non deve
    rifare nessuna delle tre regole."""

    domande: list[Domanda]
    opzioni: list[OpzioneDomanda]


_VUOTA = RisoluzioneFree(correzioni={}, applicati=[])
_SCELTE_VUOTE = ScelteRisolte(domande=[], opzioni=[])


# --- validazione (usata dagli endpoint admin) -------------------------------


def target_di(
    categoria_code: str | None, sottocategoria_id: int | None, voce_id: int | None
) -> str | None:
    """Quale bersaglio e' valorizzato. `None` se zero o piu' di uno."""
    impostati = [
        nome
        for nome, valore in (
            ("categoria", categoria_code),
            ("sottocategoria", sottocategoria_id),
            ("voce", voce_id),
        )
        if valore is not None
    ]
    return impostati[0] if len(impostati) == 1 else None


def valida_effetto(
    db: Session,
    tipo_effetto: str,
    *,
    categoria_code: str | None = None,
    sottocategoria_id: int | None = None,
    voce_id: int | None = None,
    valore: Decimal | None = None,
) -> None:
    """Alza `EffettoNonValido` con un messaggio leggibile, o non fa nulla.

    Sta qui e non in un CHECK di tabella perche' il destinatario e' l'admin che
    sta curando i coefficienti, e un vincolo SQLite gli direbbe solo
    "constraint failed".

    Oltre alla FORMA del bersaglio (esattamente uno fra categoria /
    sottocategoria / voce, ammesso per quel `tipo_effetto`), verifica anche
    che il bersaglio ricevuto corrisponda a una riga esistente: SQLite non
    forza le FK di default (nessuna riga incoerente viene bloccata li'), e
    un motore che le forza (Postgres in produzione) darebbe solo un
    `IntegrityError` grezzo al `commit()` invece di questo 400 leggibile.
    """
    if tipo_effetto not in TIPI_EFFETTO:
        raise EffettoNonValido(
            f"Tipo di effetto sconosciuto: {tipo_effetto!r}. "
            f"Ammessi: {', '.join(sorted(TIPI_EFFETTO))}."
        )

    target = target_di(categoria_code, sottocategoria_id, voce_id)
    if target is None:
        raise EffettoNonValido(
            "Un effetto deve avere esattamente un bersaglio fra categoria, "
            "sottocategoria e voce."
        )
    if target not in TARGET_AMMESSI[tipo_effetto]:
        raise EffettoNonValido(
            f"L'effetto {tipo_effetto!r} non puo' puntare a una {target}. "
            f"Ammessi: {', '.join(sorted(TARGET_AMMESSI[tipo_effetto]))}."
        )

    if categoria_code is not None and db.get(Categoria, categoria_code) is None:
        raise EffettoNonValido(f"Categoria {categoria_code!r} inesistente.")
    if sottocategoria_id is not None and db.get(Sottocategoria, sottocategoria_id) is None:
        raise EffettoNonValido(f"Sottocategoria {sottocategoria_id} inesistente.")
    if voce_id is not None and db.get(Voce, voce_id) is None:
        raise EffettoNonValido(f"Voce {voce_id} inesistente.")

    if tipo_effetto in TIPI_EFFETTO_SENZA_VALORE:
        return

    if valore is None:
        raise EffettoNonValido(f"L'effetto {tipo_effetto!r} richiede un valore.")
    if tipo_effetto in (TIPO_MOLTIPLICATORE_CATEGORIA, TIPO_FATTORE_QUANTITA) and valore < 0:
        raise EffettoNonValido(
            f"Un {tipo_effetto!r} non puo' essere negativo (ricevuto {valore})."
        )


# --- baseline ---------------------------------------------------------------


def attese_per_mq(session: Session, mq: int) -> dict[str, Decimal]:
    """I valori attesi che coprono questi metri quadri, per attributo.

    Doppio uso, ed e' il motivo per cui la tabella e' una sola: il wizard ci
    prende i default dei contatori, il motore ci prende la baseline dello
    scostamento. Se le fasce si sovrappongono vince quella con `fascia_mq_min`
    piu' alta, cioe' la piu' specifica.
    """
    righe = (
        session.query(AttesaImmobile)
        .filter(
            AttesaImmobile.fascia_mq_min <= mq,
            AttesaImmobile.fascia_mq_max >= mq,
            AttesaImmobile.attiva.is_(True),
        )
        .order_by(AttesaImmobile.attributo_code, AttesaImmobile.fascia_mq_min)
        .all()
    )
    return {r.attributo_code: r.valore_atteso for r in righe}


# --- risoluzione ------------------------------------------------------------


def _as_decimal(valore: Any) -> Decimal | None:
    """Converte una risposta numerica in Decimal, o `None` se non lo e'.

    `bool` e' escluso esplicitamente: in Python `True` e' un `int`, e un toggle
    mandato come booleano invece che come codice opzione non deve diventare
    silenziosamente la quantita' 1.
    """
    if isinstance(valore, bool) or valore is None:
        return None
    if isinstance(valore, int):
        return Decimal(valore)
    if isinstance(valore, Decimal):
        return valore
    if isinstance(valore, str):
        try:
            return Decimal(valore)
        except Exception:
            return None
    return None


def _opzioni_scelte(
    domanda: Domanda, opzioni: list[OpzioneDomanda], risposta: Any
) -> list[OpzioneDomanda]:
    """Quali opzioni sono attive per questa domanda, risposta o default.

    Una domanda senza risposta cade sul suo `is_default`. Da cui una regola di
    curatela che vale la pena scrivere: **l'opzione di default non porta
    effetti**. E' cio' che tiene neutro il sistema quando l'utente non tocca
    niente, ed e' verificato da un test di neutralita', non lasciato alla
    buona volonta'.
    """
    if domanda.tipo_controllo in CONTROLLI_NUMERICI:
        # Un numero non sceglie fra opzioni: moltiplica l'unica che c'e'.
        per_code = {o.code: o for o in opzioni}
        implicita = per_code.get(OPZIONE_VALORE)
        if implicita is not None:
            return [implicita]
        return opzioni[:1]

    if domanda.tipo_controllo == CONTROLLO_SCELTA_MULTIPLA:
        if not isinstance(risposta, (list, tuple, set)):
            return []
        scelti = {str(v) for v in risposta}
        return [o for o in opzioni if o.code in scelti]

    # scelta_singola / toggle
    if isinstance(risposta, str):
        scelta = [o for o in opzioni if o.code == risposta]
        if scelta:
            return scelta
    return [o for o in opzioni if o.is_default]


def _visibili(domande: list[Domanda], scelte: dict[str, set[str]]) -> dict[str, bool]:
    """Risolve la visibilita' condizionale in ordine di `ordine`.

    Regola di curatela: la domanda che fa da gate deve venire PRIMA di quella
    che governa. Un riferimento in avanti (o a una domanda non visibile) rende
    la domanda governata non visibile — deterministico, e visibile
    nell'anteprima invece che sorprendente in produzione.
    """
    stato: dict[str, bool] = {}
    for d in domande:
        gate_code = d.visibile_se_domanda_code
        if gate_code is None:
            stato[d.code] = True
            continue
        if not stato.get(gate_code, False):
            stato[d.code] = False
            continue
        attese = d.visibile_se_opzione_code
        stato[d.code] = attese is None or attese in scelte.get(gate_code, set())
    return stato


def _applica_derivazioni(
    session: Session,
    risposte: dict[str, Any],
    opzioni_per_domanda: dict[str, list[OpzioneDomanda]],
    scelte_per_domanda: dict[str, list[OpzioneDomanda]],
) -> None:
    """Sostituisce un "non lo so" con la risposta dedotta da un'altra domanda.

    Muta `scelte_per_domanda` sul posto, DOPO i default e PRIMA della
    visibilita': da qui in poi nessun consumatore — il motore, l'arredo, i
    bonus, l'anteprima admin — distingue una risposta dedotta da una digitata.
    E' il punto: una sola risposta risolta, non due verita' che prima o poi
    divergono.

    Si deduce solo da una risposta DATA DAVVERO
    -------------------------------------------
    `da_domanda_code` deve comparire in `risposte`. Non basta che abbia una
    risposta risolta, perche' ogni domanda ne ha sempre una: il suo default.
    Dedurre la classe energetica da un anno di costruzione che l'utente non ha
    mai dichiarato significherebbe far pagare un moltiplicatore a chi non ha
    toccato niente — cioe' rompere la neutralita' a riposo, che e'
    l'invariante su cui poggia l'intero layer (vedi `_opzioni_scelte`: l'opzione
    di default non porta effetti). E' la stessa disciplina di
    `eur_per_scostamento`, che rinuncia alla correzione invece di applicarla su
    una baseline inventata.

    Una derivazione che punta a un'opzione inesistente non fa nulla: la
    risposta resta quella di prima. Silenziosa qui, visibile nell'anteprima
    admin, che e' il posto giusto per accorgersene.
    """
    if not risposte:
        return

    derivazioni = (
        session.query(DerivazioneRisposta)
        .filter(
            DerivazioneRisposta.attiva.is_(True),
            DerivazioneRisposta.domanda_code.in_(list(scelte_per_domanda)),
        )
        .order_by(DerivazioneRisposta.id)
        .all()
    )

    for d in derivazioni:
        scelte = scelte_per_domanda.get(d.domanda_code)
        if not scelte or scelte[0].code != d.quando_opzione_code:
            continue
        # Confronto con la risposta GREZZA, non con quella risolta: risolta
        # vuol dire "eventualmente il default", e dedurre da un default e'
        # precisamente cio' che rompe la neutralita'. Un codice inesistente
        # ("nel_futuro") non corrisponde a nessuna riga e quindi non deduce
        # nulla, invece di dedurre dal default su cui e' caduto.
        if risposte.get(d.da_domanda_code) != d.da_opzione_code:
            continue
        dedotta = next(
            (o for o in opzioni_per_domanda.get(d.domanda_code, []) if o.code == d.opzione_code),
            None,
        )
        if dedotta is not None:
            scelte_per_domanda[d.domanda_code] = [dedotta]


def risolvi_scelte(
    session: Session,
    *,
    risposte: dict[str, Any] | None,
    tier: str = TIER_FREE,
) -> ScelteRisolte:
    """Quali domande sono in gioco e quali opzioni risultano scelte.

    E' la meta' del lavoro che NON riguarda gli effetti: leggere il catalogo,
    applicare i default, risolvere la visibilita' condizionale. Vive qui da
    sola perche' ha un secondo consumatore — `services/arredo.py` — e due copie
    della regola di visibilita' vorrebbero dire che prima o poi una domanda
    nascosta smette di pesare sul prezzo ma continua a portare arredo.

    `risposte is None` torna vuoto: e' il layer spento.
    """
    if risposte is None:
        return _SCELTE_VUOTE

    domande = (
        session.query(Domanda)
        .filter(Domanda.attiva.is_(True), Domanda.tier_minimo == tier)
        .order_by(Domanda.ordine, Domanda.code)
        .all()
    )
    if not domande:
        return _SCELTE_VUOTE

    codici = [d.code for d in domande]
    opzioni_per_domanda: dict[str, list[OpzioneDomanda]] = {c: [] for c in codici}
    for o in (
        session.query(OpzioneDomanda)
        .filter(OpzioneDomanda.domanda_code.in_(codici), OpzioneDomanda.attiva.is_(True))
        .order_by(OpzioneDomanda.domanda_code, OpzioneDomanda.ordine, OpzioneDomanda.id)
        .all()
    ):
        opzioni_per_domanda[o.domanda_code].append(o)

    scelte_per_domanda: dict[str, list[OpzioneDomanda]] = {
        d.code: _opzioni_scelte(d, opzioni_per_domanda[d.code], risposte.get(d.code))
        for d in domande
    }
    _applica_derivazioni(session, risposte, opzioni_per_domanda, scelte_per_domanda)
    visibili = _visibili(
        domande, {code: {o.code for o in ops} for code, ops in scelte_per_domanda.items()}
    )

    return ScelteRisolte(
        domande=domande,
        opzioni=[o for d in domande if visibili[d.code] for o in scelte_per_domanda[d.code]],
    )


def risolvi_effetti_free(
    session: Session,
    *,
    mq: int,
    tipo: str,
    risposte: dict[str, Any] | None,
) -> RisoluzioneFree:
    """Traduce le risposte nelle tre correzioni Free, per categoria.

    `risposte is None` spegne il layer e torna una risoluzione vuota: e' la
    retrocompatibilita' esplicita per i client e i test che postano ancora
    `{citta, mq, tipo}`, e il motore in quel caso produce un risultato
    bit-identico a prima. Un dizionario vuoto invece ACCENDE il layer, e le
    domande non risposte cadono sui loro default.
    """
    scelte = risolvi_scelte(session, risposte=risposte, tier=TIER_FREE)
    opzioni_attive = scelte.opzioni
    if not opzioni_attive:
        return _VUOTA
    domande = scelte.domande

    effetti_per_opzione: dict[int, list[EffettoOpzione]] = {o.id: [] for o in opzioni_attive}
    for e in (
        session.query(EffettoOpzione)
        .filter(
            EffettoOpzione.opzione_id.in_(list(effetti_per_opzione)),
            EffettoOpzione.attivo.is_(True),
            EffettoOpzione.tipo_effetto.in_(sorted(TIPI_EFFETTO_FREE)),
        )
        .order_by(EffettoOpzione.id)
        .all()
    ):
        if e.tipo_code is None or e.tipo_code == tipo:
            effetti_per_opzione[e.opzione_id].append(e)

    attese = attese_per_mq(session, mq)
    domanda_per_code = {d.code: d for d in domande}

    moltiplicatori: dict[str, Decimal] = {}
    eur_mq: dict[str, Decimal] = {}
    eur_fisso: dict[str, Decimal] = {}
    eur_scost: dict[str, Decimal] = {}
    applicati: list[EffettoApplicato] = []

    for opzione in opzioni_attive:
        domanda = domanda_per_code[opzione.domanda_code]
        for effetto in effetti_per_opzione[opzione.id]:
            traccia = _applica_effetto_free(
                domanda=domanda,
                opzione=opzione,
                effetto=effetto,
                mq=mq,
                risposta=risposte.get(domanda.code),
                attese=attese,
                moltiplicatori=moltiplicatori,
                eur_mq=eur_mq,
                eur_fisso=eur_fisso,
                eur_scost=eur_scost,
            )
            applicati.append(traccia)

    codici_categoria = set(moltiplicatori) | set(eur_mq) | set(eur_fisso) | set(eur_scost)
    correzioni = {
        code: CorrezioniCategoria(
            moltiplicatore=moltiplicatori.get(code, Decimal("1")),
            eur_mq=eur_mq.get(code, Decimal("0")),
            eur_fisso=eur_fisso.get(code, Decimal("0")),
            eur_scostamento=eur_scost.get(code, Decimal("0")),
        )
        for code in sorted(codici_categoria)
    }
    return RisoluzioneFree(correzioni=correzioni, applicati=applicati)


def _applica_effetto_free(
    *,
    domanda: Domanda,
    opzione: OpzioneDomanda,
    effetto: EffettoOpzione,
    mq: int,
    risposta: Any,
    attese: dict[str, Decimal],
    moltiplicatori: dict[str, Decimal],
    eur_mq: dict[str, Decimal],
    eur_fisso: dict[str, Decimal],
    eur_scost: dict[str, Decimal],
) -> EffettoApplicato:
    """Applica un singolo effetto agli accumulatori e ne restituisce la traccia.

    Una riga incoerente (bersaglio mancante, valore assente) viene SALTATA e
    tracciata, mai sollevata: un errore di curatela non deve mandare in 500 una
    stima pubblica. Lo stesso vale per una baseline dichiarata e non trovata.
    """

    def _traccia(
        applicato: bool,
        *,
        unita: Decimal | None = None,
        contributo: Decimal | None = None,
        nota: str | None = None,
    ) -> EffettoApplicato:
        return EffettoApplicato(
            domanda_code=domanda.code,
            opzione_code=opzione.code,
            tipo_effetto=effetto.tipo_effetto,
            categoria_code=effetto.target_categoria_code,
            valore=effetto.valore,
            unita=unita,
            contributo=contributo,
            applicato=applicato,
            nota=nota,
        )

    categoria = effetto.target_categoria_code
    if categoria is None:
        return _traccia(False, nota="Effetto Free senza categoria bersaglio.")
    if effetto.valore is None:
        return _traccia(False, nota="Effetto senza valore.")

    if effetto.tipo_effetto == TIPO_MOLTIPLICATORE_CATEGORIA:
        moltiplicatori[categoria] = moltiplicatori.get(categoria, Decimal("1")) * effetto.valore
        return _traccia(True, contributo=effetto.valore)

    if effetto.tipo_effetto == TIPO_EUR_MQ_CATEGORIA:
        contributo = effetto.valore * Decimal(mq)
        eur_mq[categoria] = eur_mq.get(categoria, Decimal("0")) + effetto.valore
        return _traccia(True, contributo=contributo)

    if effetto.tipo_effetto == TIPO_EUR_FISSO_CATEGORIA:
        # Una tantum: non moltiplica per i m2 ne' per lo scostamento. Il
        # contributo tracciato coincide con il valore, che e' il punto.
        eur_fisso[categoria] = eur_fisso.get(categoria, Decimal("0")) + effetto.valore
        return _traccia(True, contributo=effetto.valore)

    # eur_per_scostamento: l'unico effetto Free che scala con la risposta.
    atteso = Decimal("0")
    if domanda.attributo_code is not None:
        if domanda.attributo_code not in attese:
            return _traccia(
                False,
                nota=(
                    f"Nessuna attesa per l'attributo {domanda.attributo_code!r} "
                    f"a {mq} m2: la correzione non si applica."
                ),
            )
        atteso = attese[domanda.attributo_code]

    valore_risposta = _as_decimal(risposta)
    if valore_risposta is None:
        # Nessuna risposta numerica: si assume il valore atteso, cioe'
        # scostamento zero. E' la neutralita' a riposo.
        return _traccia(True, unita=Decimal("0"), contributo=Decimal("0"))

    scostamento = valore_risposta - atteso
    contributo = scostamento * effetto.valore
    eur_scost[categoria] = eur_scost.get(categoria, Decimal("0")) + contributo
    return _traccia(True, unita=scostamento, contributo=contributo)
