"""Request/response schemas for POST /api/v1/stima.

`StimaRequest` bounds untrusted input (ASVS V5, T-03-02). The response
models (`CategoriaOut`, `ExtraOut`, `TotaleOut`, `StimaResponse`) declare
ONLY the fields in the API contract from 01-RESEARCH.md — no
`base_eur_mq`, `moltiplicatore`, `coefficiente_impresa`, or
`prezzo_impresa` anywhere in this module (T-03-01, EST-05).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Annotated, TypeAlias

from pydantic import BaseModel, Field, StringConstraints


class TipoEnum(str, Enum):
    leggera = "leggera"
    moderata = "moderata"
    totale = "totale"


class DestinazioneEnum(str, Enum):
    """Abitazione principale vs altri immobili: e' cio' che separa il 50% dal
    36% sul bonus ristrutturazione."""

    prima_casa = "prima_casa"
    altro = "altro"


#: Il codice di un'opzione del catalogo domande (`opzione_domanda.code`).
CodiceOpzione: TypeAlias = Annotated[str, StringConstraints(min_length=1, max_length=64)]

#: Il valore di una risposta: un numero (stepper), il codice di un'opzione
#: (scelta singola / toggle) o una lista di codici (scelta multipla). Tutti e
#: tre i rami sono limitati: `risposte` arriva dal client, quindi e' input non
#: fidato e va bloccato allo schema (ASVS V5, stesso criterio di `mq`).
ValoreRisposta: TypeAlias = (
    Annotated[int, Field(ge=0, le=10_000)]
    | CodiceOpzione
    | Annotated[list[CodiceOpzione], Field(max_length=30)]
)

#: Le risposte del wizard. `None` NON significa "nessuna risposta": significa
#: layer parametrico spento, quindi stima identica a prima che il catalogo
#: domande esistesse. Un dizionario vuoto invece lo accende, e le domande non
#: risposte cadono sul loro default. La distinzione e' cio' che tiene in piedi
#: la retrocompatibilita' dei client che postano ancora {citta, mq, tipo}.
Risposte: TypeAlias = Annotated[dict[CodiceOpzione, ValoreRisposta], Field(max_length=60)]


class StimaRequest(BaseModel):
    citta: str = Field(min_length=1, max_length=100)
    mq: int = Field(ge=1, le=2000)
    tipo: TipoEnum
    # DEFAULT OBBLIGATORIO: decine di test e i client esistenti postano
    # {citta, mq, tipo}. Senza default questo campo sarebbe un breaking change
    # dell'API pubblica.
    destinazione: DestinazioneEnum = DestinazioneEnum.prima_casa
    risposte: Risposte | None = None


class StimaInputEcho(BaseModel):
    citta: str
    mq: int
    tipo: TipoEnum
    # Anche qui con default: gli snapshot v1 congelati non hanno questa chiave
    # e devono restare ricostruibili (`StimaInputEcho(**snapshot["input"])`).
    destinazione: DestinazioneEnum = DestinazioneEnum.prima_casa
    # Le risposte tornano nell'eco perche' finiscono nello snapshot
    # congelato: una stima salvata deve restare ricalcolabile e spiegabile
    # anche dopo che l'admin ha cambiato i coefficienti.
    risposte: Risposte | None = None


class CategoriaOut(BaseModel):
    code: str
    nome: str
    imponibile_min: Decimal
    imponibile_max: Decimal
    iva_pct: Decimal
    iva_min: Decimal
    iva_max: Decimal
    totale_min: Decimal
    totale_max: Decimal


class ExtraOut(BaseModel):
    """Fixed single values — no min/max range on extras (D-13/01-02 rule)."""

    code: str
    nome: str
    importo: Decimal
    iva_pct: Decimal


class TotaleOut(BaseModel):
    imponibile_min: Decimal
    imponibile_max: Decimal
    iva_min: Decimal
    iva_max: Decimal
    totale_min: Decimal
    totale_max: Decimal


class BonusDettaglioOut(BaseModel):
    code: str
    nome: str
    descrizione: str | None
    base_min: Decimal
    base_max: Decimal
    aliquota_pct: Decimal
    tetto_spesa_eur: Decimal | None
    tetto_modalita: str | None
    tetto_raggiunto: bool
    rate_annuali: int
    detrazione_min: Decimal
    detrazione_max: Decimal
    rata_annua_min: Decimal
    rata_annua_max: Decimal
    # G10: True quando la voce esiste solo grazie alla base arredo (es. Bonus
    # Mobili): il client la mostra nella card Arredo e non nel pannello Bonus.
    # Assente negli snapshot precedenti a G10 = False.
    su_arredo: bool = False


class BonusOut(BaseModel):
    """Il disclaimer viaggia QUI DENTRO, non accanto: cosi' finisce nello
    snapshot congelato e nel PDF, e non e' rimovibile dal client. E' materia
    fiscale — la stima e' commerciale, non consulenza."""

    bonus: list[BonusDettaglioOut]
    detrazione_min: Decimal
    detrazione_max: Decimal
    rata_annua_min: Decimal
    rata_annua_max: Decimal
    disclaimer: str
    # Assenti negli snapshot precedenti al gap G5 (default None).
    detrazione_lavori_min: Decimal | None = None
    detrazione_lavori_max: Decimal | None = None
    netto_min: Decimal | None = None
    netto_max: Decimal | None = None
    # G10: rata annua dei soli lavori (senza le voci su_arredo). Assente prima di G10.
    rata_annua_lavori_min: Decimal | None = None
    rata_annua_lavori_max: Decimal | None = None


class ArredoAmbienteOut(BaseModel):
    """Un ambiente arredato: importi LORDI, IVA inclusa, come li vede il
    cliente in un negozio di arredamento."""

    code: str
    nome: str
    eur_min: Decimal
    eur_max: Decimal


class ArredoOut(BaseModel):
    """Il forfait di arredo. Sta ACCANTO a `totale`, non dentro: l'arredo non
    e' una lavorazione, e il totale che l'utente confronta con un preventivo
    edile non deve contenerlo.

    Il disclaimer viaggia qui dentro, come per i bonus: cosi' finisce nello
    snapshot congelato e nel PDF, e non e' rimovibile dal client."""

    livello_code: str
    livello_nome: str
    ambienti: list[ArredoAmbienteOut]
    totale_min: Decimal
    totale_max: Decimal
    disclaimer: str


class ConfrontoFinitureOut(BaseModel):
    """La stessa ristrutturazione con finiture un livello sotto (ricalcolo vero
    del motore Free). Totali LAVORI, IVA inclusa, arredo escluso. DTO chiuso:
    solo valori lato cliente."""

    livello_code: str
    livello_nome: str
    totale_min: Decimal
    totale_max: Decimal


class StimaResponse(BaseModel):
    input: StimaInputEcho
    fallback: bool
    disclaimer: str | None
    valuta: str
    categorie: list[CategoriaOut]
    extra: list[ExtraOut]
    totale: TotaleOut
    # None = nessun bonus applicabile (o snapshot v1 salvato prima di questa
    # feature). Mai una sezione a zero.
    bonus: BonusOut | None = None
    # None = nessun ambiente da arredare scelto, nessun forfait curato, o
    # snapshot salvato prima di questa feature. Mai una sezione a zero.
    arredo: ArredoOut | None = None
    # None = nessun confronto (layer spento, finiture gia' al minimo, o il
    # ricalcolo non abbassa il massimo). Default per snapshot e client vecchi;
    # sezione opzionale: None, mai a zero.
    confronto_finiture: ConfrontoFinitureOut | None = None
    finiture_al_minimo: bool = False
