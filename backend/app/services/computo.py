"""Computo parametrico (Fase 11): da risposte e m2 a quantita' e importi voce
per voce. Un solo motore per Free e Pro (MOT-01): il Free somma per
categoria, il Pro mostra le voci.

TRE LIVELLI
-----------
  1. GRANDEZZE della casa e flag d'intervento (`Grandezza`): m2 di pareti,
     bagni rifatti, cucina si'/no... Il valore viene dalla risposta numerica
     della domanda che la porta, oppure dalle opzioni scelte di una domanda a
     scelta (`ValoreGrandezzaOpzione`), oppure dal default in forma chiusa
     (costante + termini). Il tipo di ristrutturazione entra come PRESET delle
     risposte (`PresetRisposta`, applicato da `risolvi_scelte`) e come
     sorgenti `tipo_<code>` nei termini: non scala piu' le quantita'.
  2. ASSI Pro esistenti (`finitura`, `tipo_pavimento`) ed effetti `escludi` /
     `fattore_quantita`: decidono quali voci alternative entrano e con che
     fattore, come nella v2 (`RisoluzionePro`).
  3. REGOLE per voce (`RegolaVoce`), legate al codice voce, dal vocabolario
     chiuso qui sotto. Le voci senza regola usano la catena v2
     (`quantita_per_unita`, poi `CoefficienteQuantitaVoce`).

TIPI DI REGOLA — insieme chiuso
-------------------------------
  fisso                      q = fattore
  grandezza                  q = fattore x G
  da_voci                    q = fattore x somma q(sorgenti incluse)
  percentuale                importo = fattore x somma importi(sorgenti)
  percentuale_per_grandezza  importo = fattore x somma importi(sorgenti) x G
  scaglioni                  q = valore del primo scaglione con G <= fino_a

Poi, per tutte: `q x fattore_quantita` dell'asse Pro, condizione (la voce
entra solo se la grandezza di condizione e' > 0), importo minimo "a corpo".

ORDINE DI VALUTAZIONE
---------------------
Grandezze e voci si valutano per dipendenza (ricorsione con memo). Un ciclo
non solleva: la voce o grandezza coinvolta vale 0 e la traccia lo dice — una
stima non deve andare in 500 per un errore di curatela (stessa postura di
`effetti.py`); la validazione admin lo segnala prima (`valida_computo`).

NESSUN COEFFICIENTE IMPRESA: prezzi cliente di `Voce` e quantita'. Il margine
non entra in questo modulo (regola non negoziabile #1).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, TipoRistrutturazione
from app.models.computo import (
    Grandezza,
    RegolaVoce,
    ScaglioneRegola,
    SorgenteRegola,
    TermineGrandezza,
    ValoreGrandezzaOpzione,
)
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Sottocategoria, Voce
from app.models.domanda import Domanda, OpzioneDomanda
from app.models.listino import Listino
from app.services.effetti import (
    CONTROLLI_NUMERICI,
    DOMANDA_FINITURA,
    DOMANDA_LIVELLO_FINITURE,
    TIER_FREE,
    TIER_PRO,
    RisoluzionePro,
    _as_decimal,
    attese_per_mq,
    risolvi_effetti_pro,
    risolvi_scelte,
)

# --- vocabolario chiuso -----------------------------------------------------

REGOLA_FISSO = "fisso"
REGOLA_GRANDEZZA = "grandezza"
REGOLA_DA_VOCI = "da_voci"
REGOLA_PERCENTUALE = "percentuale"
REGOLA_PERCENTUALE_PER_GRANDEZZA = "percentuale_per_grandezza"
REGOLA_SCAGLIONI = "scaglioni"

TIPI_REGOLA = frozenset(
    {
        REGOLA_FISSO,
        REGOLA_GRANDEZZA,
        REGOLA_DA_VOCI,
        REGOLA_PERCENTUALE,
        REGOLA_PERCENTUALE_PER_GRANDEZZA,
        REGOLA_SCAGLIONI,
    }
)
#: Regole che leggono una grandezza (`grandezza_code` obbligatorio).
REGOLE_CON_GRANDEZZA = frozenset(
    {REGOLA_GRANDEZZA, REGOLA_PERCENTUALE_PER_GRANDEZZA, REGOLA_SCAGLIONI}
)
#: Regole che leggono altre voci (almeno una `SorgenteRegola`).
REGOLE_CON_SORGENTI = frozenset(
    {REGOLA_DA_VOCI, REGOLA_PERCENTUALE, REGOLA_PERCENTUALE_PER_GRANDEZZA}
)
#: Regole che producono un importo e non una quantita' x prezzo.
REGOLE_A_IMPORTO = frozenset({REGOLA_PERCENTUALE, REGOLA_PERCENTUALE_PER_GRANDEZZA})

ARROTONDAMENTI = frozenset({"nessuno", "su", "giu", "vicino"})

#: Sorgenti riservate dei termini: i metri quadri della stima e i flag di tipo.
SORGENTE_MQ = "mq"
PREFISSO_TIPO = "tipo_"


class ComputoNonValido(ValueError):
    """Errore di curatela del computo. Sollevata dalla validazione admin e
    dall'import Excel, mai dal motore."""


# --- risultati --------------------------------------------------------------


@dataclass(frozen=True)
class GrandezzaRisolta:
    code: str
    nome: str
    um: str
    valore: Decimal
    origine: str  # risposta | opzione | attesa | formula | riservata | ciclo


@dataclass(frozen=True)
class VoceComputo:
    voce_id: int
    codice: str | None
    descrizione: str
    um: str
    categoria_code: str
    sottocategoria_id: int
    quantita: Decimal
    importo: Decimal  # euro-cliente, non arrotondato
    traccia: str


@dataclass(frozen=True)
class ComputoResult:
    grandezze: dict[str, GrandezzaRisolta]
    #: Solo le voci incluse con importo > 0, nell'ordine del listino.
    voci: list[VoceComputo]
    #: Somma degli importi per categoria (euro-cliente, non arrotondata).
    per_categoria: dict[str, Decimal] = field(default_factory=dict)

    def voci_di(self, sottocategoria_id: int) -> list[VoceComputo]:
        return [v for v in self.voci if v.sottocategoria_id == sottocategoria_id]


# --- grandezze ----------------------------------------------------------------


def _arrotonda(valore: Decimal, modo: str) -> Decimal:
    if modo == "su":
        return valore.to_integral_value(rounding=ROUND_CEILING)
    if modo == "giu":
        return valore.to_integral_value(rounding=ROUND_FLOOR)
    if modo == "vicino":
        return valore.to_integral_value(rounding=ROUND_HALF_UP)
    return valore


def _fmt(valore: Decimal) -> str:
    """Numero leggibile per la traccia: niente zeri in coda."""
    testo = format(valore.normalize(), "f") if valore == valore.to_integral_value() else format(
        valore.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP).normalize(), "f"
    )
    return testo


def risolvi_grandezze(
    session: Session,
    *,
    mq: int,
    tipo: str,
    risposte: dict[str, Any],
) -> dict[str, GrandezzaRisolta]:
    """Valore di ogni grandezza attiva, nell'ordine documentato in
    `models/computo.py::Grandezza`.

    `risposte` sono quelle grezze del client: preset e default li applica
    `risolvi_scelte`, che e' la stessa porta del motore Free.
    """
    scelte = risolvi_scelte(session, risposte=risposte, tiers=(TIER_FREE, TIER_PRO), tipo=tipo)
    risposte_eff = scelte.risposte_effettive
    domande_visibili = {o.domanda_code for o in scelte.opzioni}
    id_scelte = {o.id for o in scelte.opzioni}

    grandezze = {g.code: g for g in session.query(Grandezza).filter(Grandezza.attiva.is_(True)).all()}
    termini: dict[str, list[TermineGrandezza]] = defaultdict(list)
    for t in session.query(TermineGrandezza).order_by(TermineGrandezza.ordine, TermineGrandezza.id).all():
        termini[t.grandezza_code].append(t)

    # Domanda numerica che porta la grandezza (`attributo_code`), se visibile.
    numeriche: dict[str, Domanda] = {}
    for d in scelte.domande:
        if (
            d.tipo_controllo in CONTROLLI_NUMERICI
            and d.attributo_code is not None
            and d.code in domande_visibili
        ):
            numeriche.setdefault(d.attributo_code, d)

    # Grandezze governate da opzioni di domande visibili: grandezza -> [(opzione_id, valore)]
    governate: dict[str, list[tuple[int, Decimal]]] = defaultdict(list)
    righe_valori = (
        session.query(ValoreGrandezzaOpzione, OpzioneDomanda.domanda_code)
        .join(OpzioneDomanda, OpzioneDomanda.id == ValoreGrandezzaOpzione.opzione_id)
        .filter(OpzioneDomanda.attiva.is_(True))
        .all()
    )
    for valore_row, domanda_code in righe_valori:
        if domanda_code in domande_visibili:
            governate[valore_row.grandezza_code].append((valore_row.opzione_id, valore_row.valore))

    attese = attese_per_mq(session, mq)
    tipi = [r.code for r in session.query(TipoRistrutturazione.code).all()]

    risolte: dict[str, GrandezzaRisolta] = {
        SORGENTE_MQ: GrandezzaRisolta(SORGENTE_MQ, "Metri quadri", "m²", Decimal(mq), "riservata")
    }
    for code_tipo in tipi:
        chiave = f"{PREFISSO_TIPO}{code_tipo}"
        risolte[chiave] = GrandezzaRisolta(
            chiave, f"Tipo {code_tipo}", "", Decimal(1 if code_tipo == tipo else 0), "riservata"
        )

    in_corso: set[str] = set()

    def valore(code: str) -> Decimal:
        if code in risolte:
            return risolte[code].valore
        g = grandezze.get(code)
        if g is None:
            return Decimal("0")
        if code in in_corso:
            risolte[code] = GrandezzaRisolta(code, g.nome, g.um, Decimal("0"), "ciclo")
            return Decimal("0")
        in_corso.add(code)

        origine = "formula"
        risultato: Decimal | None = None

        domanda = numeriche.get(code)
        if domanda is not None:
            numero = _as_decimal(risposte_eff.get(domanda.code))
            if numero is not None:
                risultato, origine = numero, "risposta"

        if risultato is None and code in governate:
            risultato = sum(
                (v for oid, v in governate[code] if oid in id_scelte), Decimal("0")
            )
            origine = "opzione"

        if risultato is None and g.da_attesa and code in attese:
            risultato, origine = Decimal(attese[code]), "attesa"

        if risultato is None:
            risultato = g.costante
            for t in termini.get(code, []):
                parziale = t.fattore * valore(t.sorgente_code)
                if t.per_grandezza_code:
                    parziale *= valore(t.per_grandezza_code)
                risultato += parziale

        risultato = _arrotonda(risultato, g.arrotondamento)
        if g.minimo is not None and risultato < g.minimo:
            risultato = g.minimo
        if g.massimo is not None and risultato > g.massimo:
            risultato = g.massimo

        in_corso.discard(code)
        if code not in risolte:  # un ciclo l'ha gia' fissata a 0
            risolte[code] = GrandezzaRisolta(code, g.nome, g.um, risultato, origine)
        return risolte[code].valore

    for code in sorted(grandezze, key=lambda c: (grandezze[c].ordine, c)):
        valore(code)
    return risolte


# --- voci -------------------------------------------------------------------


def listino_ha_regole(session: Session, listino: Listino) -> bool:
    """Il listino usa il computo parametrico se almeno una sua voce ha una
    regola attiva. Altrimenti il Free ricade sul calcolo EUR/m2 (MOT-03)."""
    codici = (
        session.query(Voce.codice)
        .join(Sottocategoria, Sottocategoria.id == Voce.sottocategoria_id)
        .filter(Sottocategoria.listino_id == listino.id, Voce.codice.isnot(None))
    )
    return (
        session.query(RegolaVoce.voce_codice)
        .filter(RegolaVoce.attiva.is_(True), RegolaVoce.voce_codice.in_(codici))
        .first()
        is not None
    )


def calcola_computo(
    session: Session,
    listino: Listino,
    *,
    mq: int,
    tipo: str,
    risposte: dict[str, Any],
    risoluzione_per_categoria: Callable[[str], RisoluzionePro],
) -> ComputoResult:
    """Quantita' e importo di ogni voce del listino.

    `risoluzione_per_categoria` da' gli assi Pro (inclusioni, fattori) da usare
    per le voci di ciascuna categoria: il Pro puo' avere un livello di finitura
    diverso per categoria, il Free usa la stessa risoluzione per tutte.
    """
    grandezze = risolvi_grandezze(session, mq=mq, tipo=tipo, risposte=risposte)

    def g(code: str | None) -> Decimal:
        if code is None:
            return Decimal("0")
        r = grandezze.get(code)
        return r.valore if r is not None else Decimal("0")

    categorie = {c.code: c for c in session.query(Categoria).all()}
    ordine_categoria = {c.code: c.ordine for c in categorie.values()}
    sotto_rows = (
        session.query(Sottocategoria).filter_by(listino_id=listino.id).all()
    )
    sotto_per_id = {s.id: s for s in sotto_rows}
    voci_rows = (
        session.query(Voce)
        .filter(Voce.sottocategoria_id.in_(list(sotto_per_id)))
        .all()
        if sotto_per_id
        else []
    )
    voci_rows.sort(
        key=lambda v: (
            ordine_categoria.get(sotto_per_id[v.sottocategoria_id].categoria_code, 0),
            sotto_per_id[v.sottocategoria_id].ordine,
            v.ordine,
            v.id,
        )
    )

    regole = {
        r.voce_codice: r
        for r in session.query(RegolaVoce).filter(RegolaVoce.attiva.is_(True)).all()
    }
    sorgenti: dict[str, list[str]] = defaultdict(list)
    for s in session.query(SorgenteRegola).order_by(SorgenteRegola.id).all():
        sorgenti[s.voce_codice].append(s.sorgente_codice)
    scaglioni: dict[str, list[ScaglioneRegola]] = defaultdict(list)
    for s in session.query(ScaglioneRegola).all():
        scaglioni[s.voce_codice].append(s)

    coeff_per_voce = {
        c.voce_id: c
        for c in session.query(CoefficienteQuantitaVoce).filter_by(tipo_code=tipo).all()
    }

    voci_per_codice: dict[str, list[Voce]] = defaultdict(list)
    voci_per_sotto_codice: dict[str, list[Voce]] = defaultdict(list)
    for v in voci_rows:
        if v.codice:
            voci_per_codice[v.codice].append(v)
        sotto = sotto_per_id[v.sottocategoria_id]
        if sotto.codice:
            voci_per_sotto_codice[sotto.codice].append(v)

    def espandi(codice_sorgente: str) -> list[Voce]:
        if codice_sorgente in voci_per_codice:
            return voci_per_codice[codice_sorgente]
        return voci_per_sotto_codice.get(codice_sorgente, [])

    risoluzioni: dict[str, RisoluzionePro] = {}

    def ris_di(categoria_code: str) -> RisoluzionePro:
        if categoria_code not in risoluzioni:
            risoluzioni[categoria_code] = risoluzione_per_categoria(categoria_code)
        return risoluzioni[categoria_code]

    calcolate: dict[int, tuple[Decimal, Decimal, str]] = {}
    in_corso: set[int] = set()

    def calcola(voce: Voce) -> tuple[Decimal, Decimal, str]:
        """(quantita', importo, traccia) — 0/0 se la voce non e' inclusa."""
        if voce.id in calcolate:
            return calcolate[voce.id]
        if voce.id in in_corso:
            return Decimal("0"), Decimal("0"), "ciclo di dipendenze"
        in_corso.add(voce.id)
        risultato = _calcola(voce)
        in_corso.discard(voce.id)
        calcolate[voce.id] = risultato
        return risultato

    def _calcola(voce: Voce) -> tuple[Decimal, Decimal, str]:
        sotto = sotto_per_id[voce.sottocategoria_id]
        ris = ris_di(sotto.categoria_code)
        if not ris.voce_inclusa(voce.id, sotto.id, sotto.categoria_code):
            return Decimal("0"), Decimal("0"), "esclusa da un asse o da un effetto"

        regola = regole.get(voce.codice) if voce.codice else None
        fattore_asse = ris.fattore(voce.id, sotto.id)
        prezzo = voce.prezzo_unitario_cliente

        if regola is None:
            base = ris.quantita_per_unita.get(voce.id)
            if base is not None:
                traccia = "quantita' dalle risposte (catalogo v2)"
            else:
                coeff = coeff_per_voce.get(voce.id)
                if coeff is not None and coeff.coefficiente_qta_per_mq is not None:
                    base = coeff.coefficiente_qta_per_mq * Decimal(mq)
                    traccia = f"coefficiente v2 {_fmt(coeff.coefficiente_qta_per_mq)} x {mq} m²"
                elif coeff is not None and coeff.default_conteggio is not None:
                    base = Decimal(coeff.default_conteggio)
                    traccia = f"conteggio v2 {coeff.default_conteggio}"
                else:
                    base, traccia = Decimal("0"), "nessuna regola"
            quantita = base * fattore_asse
            return quantita, quantita * prezzo, traccia

        if regola.condizione_grandezza_code and g(regola.condizione_grandezza_code) <= 0:
            return (
                Decimal("0"),
                Decimal("0"),
                f"condizione {regola.condizione_grandezza_code} = 0",
            )

        tipo_regola = regola.tipo_regola
        f = regola.fattore
        importo: Decimal | None = None

        if tipo_regola == REGOLA_FISSO:
            quantita = f
            traccia = f"fisso {_fmt(f)}"
        elif tipo_regola == REGOLA_GRANDEZZA:
            valore_g = g(regola.grandezza_code)
            quantita = f * valore_g
            traccia = f"{regola.grandezza_code} ({_fmt(valore_g)}) x {_fmt(f)}"
        elif tipo_regola == REGOLA_SCAGLIONI:
            valore_g = g(regola.grandezza_code)
            quantita = Decimal("0")
            ordinati = sorted(
                scaglioni.get(regola.voce_codice, []),
                key=lambda s: (s.fino_a is None, s.fino_a or Decimal("0")),
            )
            for s in ordinati:
                if s.fino_a is None or valore_g <= s.fino_a:
                    quantita = s.valore
                    break
            traccia = f"scaglione di {regola.grandezza_code} ({_fmt(valore_g)}) -> {_fmt(quantita)}"
        elif tipo_regola == REGOLA_DA_VOCI:
            totale = Decimal("0")
            for codice in sorgenti.get(regola.voce_codice, []):
                for sorgente in espandi(codice):
                    if sorgente.id != voce.id:
                        totale += calcola(sorgente)[0]
            quantita = f * totale
            traccia = (
                f"{_fmt(f)} x quantita' di {', '.join(sorgenti.get(regola.voce_codice, []))}"
                f" ({_fmt(totale)})"
            )
        elif tipo_regola in REGOLE_A_IMPORTO:
            base_importo = Decimal("0")
            for codice in sorgenti.get(regola.voce_codice, []):
                for sorgente in espandi(codice):
                    if sorgente.id != voce.id:
                        base_importo += calcola(sorgente)[1]
            elenco = ", ".join(sorgenti.get(regola.voce_codice, []))
            if tipo_regola == REGOLA_PERCENTUALE:
                quantita = f * Decimal(100)
                importo = f * base_importo
                traccia = f"{_fmt(f * 100)}% di {elenco} ({_fmt(base_importo)} €)"
            else:
                valore_g = g(regola.grandezza_code)
                quantita = valore_g
                importo = f * base_importo * valore_g
                traccia = (
                    f"{_fmt(f * 100)}% di {elenco} ({_fmt(base_importo)} €)"
                    f" x {regola.grandezza_code} ({_fmt(valore_g)})"
                )
        else:
            return Decimal("0"), Decimal("0"), f"tipo di regola sconosciuto {tipo_regola!r}"

        if fattore_asse != 1:
            quantita *= fattore_asse
            if importo is not None:
                importo *= fattore_asse
            traccia += f" x fattore {_fmt(fattore_asse)}"

        if importo is None:
            importo = quantita * prezzo

        if regola.importo_minimo is not None and Decimal("0") < importo < regola.importo_minimo:
            importo = regola.importo_minimo
            traccia += f"; a corpo minimo {_fmt(regola.importo_minimo)} €"

        return quantita, importo, traccia

    voci_out: list[VoceComputo] = []
    per_categoria: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for voce in voci_rows:
        quantita, importo, traccia = calcola(voce)
        if importo <= 0:
            continue
        sotto = sotto_per_id[voce.sottocategoria_id]
        voci_out.append(
            VoceComputo(
                voce_id=voce.id,
                codice=voce.codice,
                descrizione=voce.descrizione,
                um=voce.um,
                categoria_code=sotto.categoria_code,
                sottocategoria_id=sotto.id,
                quantita=quantita,
                importo=importo,
                traccia=traccia,
            )
        )
        per_categoria[sotto.categoria_code] += importo

    return ComputoResult(grandezze=grandezze, voci=voci_out, per_categoria=dict(per_categoria))


# --- punti d'ingresso condivisi da Free e Pro --------------------------------


def risposte_con_finitura(session: Session, risposte: dict[str, Any]) -> dict[str, Any]:
    """Il ponte fra `livello_finiture` (wizard) e l'asse Pro `finitura`.

    Le due domande condividono i codici d'opzione: senza il ponte chi sceglie
    "Alte" nel wizard avrebbe le voci B/C/D al default. Una risposta esplicita
    a `finitura` vince; un codice che l'asse non ha resta fuori, cosi' ricade
    sul default invece di diventare invalido.
    """
    risposte = dict(risposte or {})
    livello_wizard = risposte.get(DOMANDA_LIVELLO_FINITURE)
    if DOMANDA_FINITURA not in risposte and isinstance(livello_wizard, str):
        esiste = (
            session.query(OpzioneDomanda.code)
            .filter_by(domanda_code=DOMANDA_FINITURA, code=livello_wizard)
            .first()
        )
        if esiste is not None:
            risposte[DOMANDA_FINITURA] = livello_wizard
    return risposte


def computo_free(
    session: Session,
    listino: Listino,
    *,
    mq: int,
    tipo: str,
    risposte: dict[str, Any] | None,
) -> ComputoResult | None:
    """Il computo con una sola risoluzione degli assi per tutte le categorie:
    e' cio' che il Free somma per categoria. `None` se il listino non ha
    regole (il Free ricade sul calcolo EUR/m2, MOT-03).

    `risposte=None` vale come `{}`: nel computo non esiste un "layer spento",
    una stima senza risposte e' la stima del preset del tipo.
    """
    if not listino_ha_regole(session, listino):
        return None
    risposte_asse = risposte_con_finitura(session, risposte or {})
    ris = risolvi_effetti_pro(session, mq=mq, tipo=tipo, risposte=risposte_asse)
    return calcola_computo(
        session,
        listino,
        mq=mq,
        tipo=tipo,
        risposte=risposte_asse,
        risoluzione_per_categoria=lambda _codice: ris,
    )


# --- validazione (admin / import Excel) --------------------------------------


def valida_computo(session: Session) -> list[str]:
    """Errori di curatela leggibili, vuota se il computo e' coerente.

    Controlla: tipi di regola e arrotondamenti noti; grandezze e sorgenti che
    esistono; regole con grandezza / sorgenti / scaglioni quando servono;
    voci a corpo o a pezzo (`ac`, `cad`) con una regola che legge i m2
    direttamente; cicli fra grandezze e fra voci.
    """
    errori: list[str] = []
    grandezze = {g.code: g for g in session.query(Grandezza).all()}
    tipi = {r.code for r in session.query(TipoRistrutturazione.code).all()}
    riservate = {SORGENTE_MQ} | {f"{PREFISSO_TIPO}{t}" for t in tipi}
    note = set(grandezze) | riservate

    for g in grandezze.values():
        if g.arrotondamento not in ARROTONDAMENTI:
            errori.append(f"Grandezza {g.code}: arrotondamento {g.arrotondamento!r} non ammesso.")

    dipendenze_g: dict[str, set[str]] = defaultdict(set)
    for t in session.query(TermineGrandezza).all():
        if t.grandezza_code not in grandezze:
            errori.append(f"Termine {t.id}: grandezza {t.grandezza_code!r} inesistente.")
        for ref in (t.sorgente_code, t.per_grandezza_code):
            if ref is None:
                continue
            if ref not in note:
                errori.append(f"Grandezza {t.grandezza_code}: sorgente {ref!r} inesistente.")
            elif ref in grandezze:
                dipendenze_g[t.grandezza_code].add(ref)
    errori.extend(f"Ciclo fra grandezze: {c}" for c in _cicli(dipendenze_g))

    codici_voce = {r[0] for r in session.query(Voce.codice).filter(Voce.codice.isnot(None)).all()}
    codici_sotto = {
        r[0] for r in session.query(Sottocategoria.codice).filter(Sottocategoria.codice.isnot(None)).all()
    }
    um_per_codice = {r[0]: r[1] for r in session.query(Voce.codice, Voce.um).all() if r[0]}
    sorgenti: dict[str, list[str]] = defaultdict(list)
    for s in session.query(SorgenteRegola).all():
        sorgenti[s.voce_codice].append(s.sorgente_codice)
    con_scaglioni = {s.voce_codice for s in session.query(ScaglioneRegola).all()}

    dipendenze_v: dict[str, set[str]] = defaultdict(set)
    for r in session.query(RegolaVoce).all():
        etichetta = f"Regola {r.voce_codice}"
        if r.voce_codice not in codici_voce:
            errori.append(f"{etichetta}: nessuna voce con questo codice.")
        if r.tipo_regola not in TIPI_REGOLA:
            errori.append(
                f"{etichetta}: tipo {r.tipo_regola!r} non ammesso "
                f"({', '.join(sorted(TIPI_REGOLA))})."
            )
            continue
        for ref, ruolo in ((r.grandezza_code, "grandezza"), (r.condizione_grandezza_code, "condizione")):
            if ref is not None and ref not in note:
                errori.append(f"{etichetta}: {ruolo} {ref!r} inesistente.")
        if r.tipo_regola in REGOLE_CON_GRANDEZZA and not r.grandezza_code:
            errori.append(f"{etichetta}: il tipo {r.tipo_regola!r} richiede una grandezza.")
        if r.tipo_regola in REGOLE_CON_SORGENTI and not sorgenti.get(r.voce_codice):
            errori.append(f"{etichetta}: il tipo {r.tipo_regola!r} richiede almeno una voce sorgente.")
        if r.tipo_regola == REGOLA_SCAGLIONI and r.voce_codice not in con_scaglioni:
            errori.append(f"{etichetta}: il tipo 'scaglioni' richiede almeno uno scaglione.")
        if (
            um_per_codice.get(r.voce_codice, "").strip().lower() in ("ac", "cad")
            and r.tipo_regola == REGOLA_GRANDEZZA
            and r.grandezza_code == SORGENTE_MQ
        ):
            errori.append(
                f"{etichetta}: voce a corpo/a pezzo con quantita' proporzionale ai m² "
                "(usare una grandezza di conteggio o una regola fissa)."
            )
        for codice in sorgenti.get(r.voce_codice, []):
            if codice not in codici_voce and codice not in codici_sotto:
                errori.append(f"{etichetta}: sorgente {codice!r} non e' ne' una voce ne' una sottocategoria.")
            dipendenze_v[r.voce_codice].add(codice)

    # Le sottocategorie contano come nodi che dipendono dalle loro voci.
    for sotto_codice in codici_sotto:
        for (voce_codice,) in (
            session.query(Voce.codice)
            .join(Sottocategoria, Sottocategoria.id == Voce.sottocategoria_id)
            .filter(Sottocategoria.codice == sotto_codice, Voce.codice.isnot(None))
            .all()
        ):
            if voce_codice != sotto_codice:
                dipendenze_v[sotto_codice].add(voce_codice)
    for ciclo in _cicli(dipendenze_v):
        errori.append(f"Ciclo fra voci: {ciclo}")
    return errori


def _cicli(dipendenze: dict[str, set[str]]) -> list[str]:
    """I cicli del grafo, come 'a -> b -> a', uno per componente."""
    stato: dict[str, int] = {}
    pila: list[str] = []
    trovati: list[str] = []

    def visita(nodo: str) -> None:
        stato[nodo] = 1
        pila.append(nodo)
        for succ in sorted(dipendenze.get(nodo, ())):
            if stato.get(succ) == 1:
                inizio = pila.index(succ)
                trovati.append(" -> ".join(pila[inizio:] + [succ]))
            elif succ not in stato:
                visita(succ)
        pila.pop()
        stato[nodo] = 2

    for nodo in sorted(dipendenze):
        if nodo not in stato:
            visita(nodo)
    return trovati
