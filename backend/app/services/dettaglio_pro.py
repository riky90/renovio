"""DettaglioProService: motore Pro bottom-up (PRO-01, 03-03-PLAN.md Task 1).

Indipendente dal motore di stima Free (D-01): questo modulo non importa
alcuna classe del servizio di stima Fase 1 e non riconcilia il proprio
risultato col totale della Fase 1 — sono misure diverse, e' atteso e
accettabile che i due numeri differiscano.

ALL math happens in `Decimal`; coefficienti/prezzi letti dal DB (mai
cablati nel codice, ENG-02). Nessun campo/colonna impresa esiste su `Voce`
(D-10) ne' viene mai letto o restituito da questo modulo: l'anti-leak e'
strutturale, non solo di schema-risposta (stessa disciplina di
`estimation.py` — dataclass frozen a campi chiusi).

Range per-voce (Assunzione A1, 03-RESEARCH.md Pattern 4): riuso di
`TipoRistrutturazione.range_pct` (10/15/20% per tipo, gia' a DB per il
Free) applicato a `quantita_stimata * prezzo_unitario_cliente`.

GLI ASSI DI SCELTA SONO DATI (Fase 09-03) — le sottocategorie
`famiglia='catalogo'` sono cataloghi di ALTERNATIVE, non addendi.
`PAVIMENTI E RIVESTIMENTI GRES`, `PAVIMENTI` e `PAVIMENTI PARQUET` sono tre
pavimentazioni per la STESSA stanza: sommarle tutte gonfia il totale per
costruzione. Da questa fase il filtro non e' piu' una colonna (`livello` di
`Voce`) letta a mano da questo modulo, ma la RISOLUZIONE del
catalogo domande (`app/services/effetti.py::risolvi_effetti_pro`), la stessa
che gia' serve il layer Free: una domanda con effetti `includi` diventa un
asse, e ogni voce entra nel computo solo se l'asse che la governa (se c'e')
ha scelto l'opzione che la include.

ORDINE DI RISOLUZIONE (contratto ereditato da `effetti.py`, applicato qui
voce per voce):
  1. si parte da tutte le voci del listino
  2. le esclusioni vincono sempre (`RisoluzionePro.voce_inclusa`)
  3. per ogni asse restano solo le voci dell'opzione scelta (o del default)
  4. le voci non governate da alcun asse restano sempre incluse
  5. la quantita' viene da `quantita_per_unita` se presente per la voce,
     altrimenti dalla catena esistente di `CoefficienteQuantitaVoce`
     (coefficiente-per-mq, poi conteggio di default), poi si applica
     `fattore_quantita` (`RisoluzionePro.fattore`)
  6. le sottocategorie rimaste vuote dopo il filtro si scartano

La colonna `livello` di `Voce` e `coefficiente_qta_voce.domanda_mirata_key`
restano a DB come dati storici (D-41: nessuna perdita nella migrazione) ma
questo modulo non li legge piu': l'asse `finitura` e gli effetti
`quantita_per_unita` del catalogo ne hanno preso il posto.

CONTRATTO API GENERICO (Fase 09-05): il pannello 'Qualche dettaglio in
piu'' non manda piu' tre campi cablati (bagni/porte/condizionatori) ma un
dict generico `{codice: valore}`. `valida_risposte_pro()` e' il gate ASVS
V5 su questo input non fidato: ogni chiave deve essere il codice di una
domanda restituita da `domande_configuratore()` (quindi con almeno un
effetto Pro attivo), ogni valore un intero 0..99 per le domande numeriche o
il codice di un'opzione attiva per le domande a scelta — mai un range
`Field(ge=..., le=...)` fisso nello schema, perche' il limite vero e' il
catalogo, non una costante nel codice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.models.catalogo import Categoria, LivelloFinitura, TipoRistrutturazione
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Sottocategoria, Voce
from app.models.domanda import Domanda, EffettoOpzione, OpzioneDomanda
from app.models.listino import Listino
from app.services.effetti import (
    CONTROLLI_NUMERICI,
    DOMANDA_FINITURA,
    TIPI_EFFETTO_PRO,
    RisoluzionePro,
    attese_per_mq,
    risolvi_effetti_pro,
)


def _eur(value: Decimal) -> Decimal:
    """Quantize to whole euro (ROUND_HALF_UP) — used only on output fields."""
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _qta(value: Decimal) -> Decimal:
    """Quantize a stimata quantity to 0.01 (ROUND_HALF_UP)."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class VoceEstimata:
    codice: str | None
    descrizione: str
    um: str
    quantita_stimata: Decimal
    prezzo_min: Decimal
    prezzo_max: Decimal
    # Codice dell'opzione dell'asse `finitura` che include questa voce (es.
    # "medio"), o None se la voce non e' governata da quell'asse (comune a
    # tutti i livelli, o governata da un altro asse come `tipo_pavimento`).
    livello: str | None = None


@dataclass(frozen=True)
class SottocategoriaEstimata:
    codice: str | None
    nome: str
    famiglia: str
    voci: list[VoceEstimata] = field(default_factory=list)
    # Subtotale a range = somma dei prezzi min/max delle voci (D-11: sempre a
    # range, mai un punto). Calcolato dal servizio, unica fonte per schermata
    # e PDF (03-RESEARCH.md Pitfall 2).
    totale_min: Decimal = Decimal("0")
    totale_max: Decimal = Decimal("0")


@dataclass(frozen=True)
class CategoriaDettagliata:
    code: str
    nome: str
    sottocategorie: list[SottocategoriaEstimata] = field(default_factory=list)
    totale_min: Decimal = Decimal("0")
    totale_max: Decimal = Decimal("0")
    # Livello EFFETTIVAMENTE applicato a questa categoria (None dove il livello
    # non e' selezionabile, es. A-EDILE). E' il valore risolto — la scelta
    # dell'utente oppure il default di tabella — non quello grezzo in input:
    # e' cio' che schermata e PDF devono mostrare.
    livello_scelto: str | None = None
    livello_scelto_nome: str | None = None


@dataclass(frozen=True)
class OpzioneConfiguratore:
    """Un'opzione del pannello 'Qualche dettaglio in piu'' (09-05): stessi tre
    campi che il client mostra, niente di piu' (nessun effetto/coefficiente)."""

    code: str
    etichetta: str
    descrizione: str | None
    is_default: bool


@dataclass(frozen=True)
class DomandaConfiguratore:
    """Una domanda del configuratore Pro con il valore GIA' risolto (D-07):
    la risposta salvata se valida, altrimenti il default di catalogo (opzione
    `is_default` per le scelte, l'atteso di `attesa_immobile` per gli
    stepper). Il pannello e il PDF Pro leggono `valore`/`valore_etichetta`,
    mai gli effetti che l'hanno prodotto."""

    code: str
    testo: str
    help: str | None
    tipo_controllo: str
    opzioni: list[OpzioneConfiguratore] = field(default_factory=list)
    valore: int | str | None = None
    # Solo per le domande a scelta: l'etichetta dell'opzione risolta in
    # `valore` (es. "Gres"). None per le numeriche, che non hanno etichetta.
    valore_etichetta: str | None = None


@dataclass(frozen=True)
class DettaglioProResult:
    categorie: list[CategoriaDettagliata] = field(default_factory=list)
    # Totale generale a range = somma dei totali di categoria.
    totale_min: Decimal = Decimal("0")
    totale_max: Decimal = Decimal("0")
    # Le domande del pannello "Qualche dettaglio in piu'" (09-05), gia' coi
    # valori risolti — la finitura NON compare qui (resta sul selettore per
    # categoria esistente).
    domande: list[DomandaConfiguratore] = field(default_factory=list)


class LivelliNonValidi(ValueError):
    """Input `livelli` non ammesso. Il router la traduce in 400."""


def validate_livelli(session: Session, livelli: dict[str, str] | None) -> None:
    """Valida le CHIAVI oltre ai valori: `livelli` arriva dal client, e un dict
    non validato e' un dict di cui non si sa nulla. Le chiavi devono essere
    categorie con `livello_selezionabile=True` (mandare un livello per A-EDILE
    e' un errore, non un no-op silenzioso) e i valori codici esistenti in
    `livello_finitura`. Entrambi i vincoli sono letti dal DB, mai da una
    costante nel codice."""
    if not livelli:
        return
    codici_categoria = {
        row.code
        for row in session.query(Categoria).filter_by(livello_selezionabile=True).all()
    }
    codici_livello = {row.code for row in session.query(LivelloFinitura).all()}
    for categoria_code, livello_code in livelli.items():
        if categoria_code not in codici_categoria:
            raise LivelliNonValidi(
                f"La categoria '{categoria_code}' non prevede un livello di finitura"
            )
        if livello_code not in codici_livello:
            raise LivelliNonValidi(f"Livello di finitura '{livello_code}' non valido")


class RisposteNonValide(ValueError):
    """Input `risposte` (pannello configuratore) non ammesso. Il router la
    traduce in 400."""


def _as_int_valido(valore: object) -> int | None:
    """Un intero vero, non un booleano: `True`/`False` sono `int` in Python,
    e una risposta booleana mandata per errore su uno stepper non deve
    diventare silenziosamente 1 o 0."""
    if isinstance(valore, bool):
        return None
    if isinstance(valore, int):
        return valore
    return None


def domande_configuratore(
    session: Session, *, mq: int, risposte: dict
) -> list[DomandaConfiguratore]:
    """Le domande del pannello 'Qualche dettaglio in piu'' (D-06): quelle che
    governano DAVVERO il computo, cioe' hanno almeno un effetto Pro attivo
    (`TIPI_EFFETTO_PRO`) su un'opzione attiva. Esclude sempre la domanda
    `finitura`, che resta sul selettore per categoria esistente.

    Il valore di ognuna e' gia' risolto (D-07): la risposta salvata se valida
    per quella domanda, altrimenti il default di catalogo — mai un campo
    vuoto che il pannello dovrebbe interpretare da solo."""
    codici_domanda = [
        row[0]
        for row in (
            session.query(Domanda.code)
            .join(OpzioneDomanda, OpzioneDomanda.domanda_code == Domanda.code)
            .join(EffettoOpzione, EffettoOpzione.opzione_id == OpzioneDomanda.id)
            .filter(
                Domanda.attiva.is_(True),
                Domanda.code != DOMANDA_FINITURA,
                OpzioneDomanda.attiva.is_(True),
                EffettoOpzione.attivo.is_(True),
                EffettoOpzione.tipo_effetto.in_(sorted(TIPI_EFFETTO_PRO)),
            )
            .distinct()
            .all()
        )
    ]
    if not codici_domanda:
        return []

    domande_rows = (
        session.query(Domanda)
        .filter(Domanda.code.in_(codici_domanda))
        .order_by(Domanda.ordine, Domanda.code)
        .all()
    )

    opzioni_per_domanda: dict[str, list[OpzioneDomanda]] = {c: [] for c in codici_domanda}
    for o in (
        session.query(OpzioneDomanda)
        .filter(OpzioneDomanda.domanda_code.in_(codici_domanda), OpzioneDomanda.attiva.is_(True))
        .order_by(OpzioneDomanda.domanda_code, OpzioneDomanda.ordine, OpzioneDomanda.id)
        .all()
    ):
        opzioni_per_domanda[o.domanda_code].append(o)

    attese: dict[str, Decimal] | None = None

    def attese_lazy() -> dict[str, Decimal]:
        nonlocal attese
        if attese is None:
            attese = attese_per_mq(session, mq)
        return attese

    risultato: list[DomandaConfiguratore] = []
    for domanda in domande_rows:
        opzioni_attive = opzioni_per_domanda.get(domanda.code, [])
        opzioni_out = [
            OpzioneConfiguratore(
                code=o.code, etichetta=o.etichetta, descrizione=o.descrizione, is_default=o.is_default
            )
            for o in opzioni_attive
        ]

        if domanda.tipo_controllo in CONTROLLI_NUMERICI:
            valore_numerico = _as_int_valido(risposte.get(domanda.code))
            if valore_numerico is None:
                if domanda.attributo_code is not None and domanda.attributo_code in attese_lazy():
                    valore_numerico = int(attese_lazy()[domanda.attributo_code])
                else:
                    valore_numerico = 0
            risultato.append(
                DomandaConfiguratore(
                    code=domanda.code,
                    testo=domanda.testo,
                    help=domanda.help,
                    tipo_controllo=domanda.tipo_controllo,
                    opzioni=opzioni_out,
                    valore=valore_numerico,
                    valore_etichetta=None,
                )
            )
            continue

        risposta = risposte.get(domanda.code)
        scelta = next((o for o in opzioni_attive if o.code == risposta), None)
        if scelta is None:
            scelta = next((o for o in opzioni_attive if o.is_default), None)
        risultato.append(
            DomandaConfiguratore(
                code=domanda.code,
                testo=domanda.testo,
                help=domanda.help,
                tipo_controllo=domanda.tipo_controllo,
                opzioni=opzioni_out,
                valore=scelta.code if scelta is not None else None,
                valore_etichetta=scelta.etichetta if scelta is not None else None,
            )
        )
    return risultato


def valida_risposte_pro(session: Session, risposte: dict) -> dict:
    """Valida le risposte del pannello contro il catalogo (ASVS V5): ogni
    chiave deve essere il codice di una domanda del configuratore, ogni
    valore un intero 0..99 (bool rifiutato) per le numeriche o il codice di
    un'opzione attiva per le scelte. Restituisce il dict validato — mai il
    dict grezzo del client."""
    if not risposte:
        return {}
    domande = domande_configuratore(session, mq=1, risposte={})
    per_code = {d.code: d for d in domande}
    validato: dict = {}
    for codice, valore in risposte.items():
        domanda = per_code.get(codice)
        if domanda is None:
            raise RisposteNonValide(f"Domanda '{codice}' non prevista nel dettaglio Pro")
        if domanda.tipo_controllo in CONTROLLI_NUMERICI:
            numero = _as_int_valido(valore)
            if numero is None:
                raise RisposteNonValide(f"'{codice}' deve essere un numero intero")
            if numero < 0 or numero > 99:
                raise RisposteNonValide(f"'{codice}' deve essere compreso tra 0 e 99")
            validato[codice] = numero
        else:
            codici_opzione = {o.code for o in domanda.opzioni}
            if not isinstance(valore, str) or valore not in codici_opzione:
                raise RisposteNonValide(f"Opzione '{valore}' non valida per '{codice}'")
            validato[codice] = valore
    return validato


class DettaglioProService:
    """Server-side calculation: (listino, mq, tipo, risposte) -> DettaglioProResult."""

    @staticmethod
    def compute(
        session: Session,
        listino: Listino,
        mq: int,
        tipo: str,
        risposte: dict[str, int],
        livelli: dict[str, str] | None = None,
    ) -> DettaglioProResult:
        """`livelli` ha un default proprio perche' tutte le chiamate esistenti
        (test compresi) restano valide senza modifiche: assente significa
        "applica il livello di default di tabella", non "prendi tutte le
        voci"."""
        tipo_row = session.query(TipoRistrutturazione).filter_by(code=tipo).one()
        range_pct = tipo_row.range_pct

        risposte_base = dict(risposte or {})
        livelli_scelti = livelli or {}
        livelli_rows = session.query(LivelloFinitura).order_by(LivelloFinitura.ordine).all()
        livelli_nomi = {row.code: row.nome for row in livelli_rows}
        livello_default = next((row.code for row in livelli_rows if row.is_default), None)

        # Una risoluzione per valore DISTINTO di finitura: il pannello puo'
        # mandare un valore diverso per categoria via `livelli`, ma il
        # catalogo ha una sola domanda `finitura` — la si risolve una volta
        # per ciascun valore effettivamente in gioco, non una volta a voce.
        risoluzioni: dict[str | None, RisoluzionePro] = {}

        def risoluzione_per(valore_finitura: str | None) -> RisoluzionePro:
            if valore_finitura not in risoluzioni:
                risposte_asse = dict(risposte_base)
                if valore_finitura is not None:
                    risposte_asse[DOMANDA_FINITURA] = valore_finitura
                risoluzioni[valore_finitura] = risolvi_effetti_pro(
                    session, mq=mq, tipo=tipo, risposte=risposte_asse
                )
            return risoluzioni[valore_finitura]

        categorie_rows = session.query(Categoria).order_by(Categoria.ordine).all()

        categorie: list[CategoriaDettagliata] = []
        for cat in categorie_rows:
            valore_finitura_cat = (
                (livelli_scelti.get(cat.code) or risposte_base.get(DOMANDA_FINITURA))
                if cat.livello_selezionabile
                else risposte_base.get(DOMANDA_FINITURA)
            )
            ris = risoluzione_per(valore_finitura_cat)

            sotto_rows = (
                session.query(Sottocategoria)
                .filter_by(listino_id=listino.id, categoria_code=cat.code)
                .order_by(Sottocategoria.ordine)
                .all()
            )

            sottocategorie: list[SottocategoriaEstimata] = []
            for sotto in sotto_rows:
                voce_rows = (
                    session.query(Voce).filter_by(sottocategoria_id=sotto.id).order_by(Voce.ordine).all()
                )
                voce_rows_incluse = [
                    v for v in voce_rows if ris.voce_inclusa(v.id, sotto.id, cat.code)
                ]

                voci: list[VoceEstimata] = []
                for voce in voce_rows_incluse:
                    coeff = (
                        session.query(CoefficienteQuantitaVoce)
                        .filter_by(voce_id=voce.id, tipo_code=tipo)
                        .one_or_none()
                    )

                    quantita_stimata = DettaglioProService._quantita(coeff, mq, voce.id, ris, sotto.id)

                    totale_voce = quantita_stimata * voce.prezzo_unitario_cliente
                    prezzo_min = _eur(totale_voce * (Decimal("1") - range_pct))
                    prezzo_max = _eur(totale_voce * (Decimal("1") + range_pct))

                    voci.append(
                        VoceEstimata(
                            codice=voce.codice,
                            descrizione=voce.descrizione,
                            um=voce.um,
                            quantita_stimata=quantita_stimata,
                            prezzo_min=prezzo_min,
                            prezzo_max=prezzo_max,
                            livello=ris.opzione_asse(DOMANDA_FINITURA, voce.id),
                        )
                    )

                # Sottocategoria svuotata DAL FILTRO -> scartata: un accordion
                # vuoto a 0 EUR e' rumore. Una sottocategoria gia' priva di voci
                # in partenza resta invece visibile com'era prima dei livelli.
                if voce_rows and not voci:
                    continue

                sotto_min = sum((v.prezzo_min for v in voci), Decimal("0"))
                sotto_max = sum((v.prezzo_max for v in voci), Decimal("0"))
                sottocategorie.append(
                    SottocategoriaEstimata(
                        codice=sotto.codice,
                        nome=sotto.nome,
                        famiglia=sotto.famiglia,
                        voci=voci,
                        totale_min=sotto_min,
                        totale_max=sotto_max,
                    )
                )

            # Categoria senza NESSUNA sottocategoria nel listino -> scartata,
            # per la stessa ragione della sottocategoria svuotata poco sopra:
            # una card a 0 EUR e' rumore. Il caso vivo e' `E-ARREDO`, che
            # esiste in tabella per il Free (forfait) e per le voci Pro che
            # arriveranno con l'import Excel: finche' quelle voci non ci sono,
            # la categoria non ha niente da mostrare nel dettaglio.
            if not sotto_rows:
                continue

            # Livello EFFETTIVAMENTE scelto per la categoria: la prima opzione
            # scelta sull'asse `finitura`, o il default di tabella se la
            # domanda `finitura` non esiste a DB (retrocompatibilita' su un
            # DB migrato ma non ri-seminato — stesso precedente di prima della
            # Fase 09-03).
            if cat.livello_selezionabile:
                opzioni_finitura_scelte = ris.opzioni_scelte.get(DOMANDA_FINITURA)
                livello_scelto = opzioni_finitura_scelte[0] if opzioni_finitura_scelte else livello_default
            else:
                livello_scelto = None

            cat_min = sum((s.totale_min for s in sottocategorie), Decimal("0"))
            cat_max = sum((s.totale_max for s in sottocategorie), Decimal("0"))
            categorie.append(
                CategoriaDettagliata(
                    code=cat.code,
                    nome=cat.nome,
                    sottocategorie=sottocategorie,
                    totale_min=cat_min,
                    totale_max=cat_max,
                    livello_scelto=livello_scelto,
                    livello_scelto_nome=livelli_nomi.get(livello_scelto) if livello_scelto else None,
                )
            )

        totale_min = sum((c.totale_min for c in categorie), Decimal("0"))
        totale_max = sum((c.totale_max for c in categorie), Decimal("0"))
        domande = domande_configuratore(session, mq=mq, risposte=risposte_base)
        return DettaglioProResult(
            categorie=categorie,
            totale_min=totale_min,
            totale_max=totale_max,
            domande=domande,
        )

    @staticmethod
    def _quantita(
        coeff: CoefficienteQuantitaVoce | None,
        mq: int,
        voce_id: int,
        ris: RisoluzionePro,
        sottocategoria_id: int,
    ) -> Decimal:
        """La quantita' di una voce: `quantita_per_unita` del catalogo se
        presente per questa voce, altrimenti la catena esistente di
        `CoefficienteQuantitaVoce` (coefficiente-per-mq, poi conteggio di
        default; MAI `domanda_mirata_key`, che il catalogo Pro ha
        sostituito), poi il `fattore_quantita` risolto per voce/sottocategoria.
        Se non c'e' copertura la quantita' e' 0."""
        base = ris.quantita_per_unita.get(voce_id)
        if base is None:
            if coeff is None:
                base = Decimal("0")
            elif coeff.coefficiente_qta_per_mq is not None:
                base = coeff.coefficiente_qta_per_mq * Decimal(mq)
            elif coeff.default_conteggio is not None:
                base = Decimal(coeff.default_conteggio)
            else:
                base = Decimal("0")
        return _qta(base * ris.fattore(voce_id, sottocategoria_id))
