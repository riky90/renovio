"""Request/response schemas for GET/POST /me/stime/{id}/dettaglio-pro
(03-03-PLAN.md Task 2, generalizzati in 09-05-PLAN.md Task 1).

DTO a campi chiusi: nessun prezzo/moltiplicatore di listino ne' alcun dato
di margine riservato all'impresa in nessun modello di questo modulo (stessa
disciplina anti-leak di `schemas/stima.py`). Nessun `model_validate` su
entita' ORM — le risposte sono costruite campo-per-campo dal router.

`RisposteDomandeRequest` non limita piu' l'input non fidato con un range
`Field(ge=..., le=...)` fisso per tre campi cablati: dalla Fase 09-05 il
payload e' generico (`risposte: dict[codice, valore]`) e i limiti (quali
codici sono ammessi, quali numeri, quali opzioni) sono validati contro il
catalogo da `services/dettaglio_pro.py::valida_risposte_pro` (ASVS V5,
T-09-14) — lo schema garantisce solo la FORMA (dict di massimo 60 chiavi,
interi 0..10000 o codici opzione, `extra="forbid"`), il catalogo il
CONTENUTO.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.stima import BonusOut, ConfrontoFinitureOut, ExtraOut, Risposte


class VoceOut(BaseModel):
    codice: str | None
    descrizione: str
    um: str
    quantita_stimata: Decimal
    prezzo_min: Decimal
    prezzo_max: Decimal
    livello: str | None = None


class SottocategoriaOut(BaseModel):
    codice: str | None
    nome: str
    famiglia: str
    voci: list[VoceOut]
    totale_min: Decimal
    totale_max: Decimal


class CategoriaDettagliataOut(BaseModel):
    code: str
    nome: str
    sottocategorie: list[SottocategoriaOut]
    totale_min: Decimal
    totale_max: Decimal
    livello_scelto: str | None = None
    livello_scelto_nome: str | None = None


class LivelloFinituraOut(BaseModel):
    code: str
    nome: str
    ordine: int
    descrizione: str | None = None
    is_default: bool = False


class CategoriaLivelloOut(BaseModel):
    """Categoria che ammette un livello di finitura. Serve al form Pro, che
    deve costruire i selettori PRIMA che una stima esista — quindi prima che
    `DettaglioProOut.categorie` sia calcolabile."""

    code: str
    nome: str


class OpzioniProOut(BaseModel):
    categorie: list[CategoriaLivelloOut]
    livelli: list[LivelloFinituraOut]
    # Domande a scelta del configuratore (09-11): il wizard Pro le disegna allo
    # step 4 accanto ai livelli, PRIMA che una stima esista — stesso motivo per
    # cui `categorie`/`livelli` sono gia' qui. Escluse le numeriche (bagni/porte/
    # condizionatori): quelle il wizard le chiede allo step 2 dal catalogo Free.
    domande: list[DomandaProOut] = Field(default_factory=list)


class OpzioneProOut(BaseModel):
    """Un'opzione di una domanda del pannello 'Qualche dettaglio in piu''.
    Nessun campo di effetto: il client sa solo cosa mostrare, non cosa fa."""

    code: str
    etichetta: str
    descrizione: str | None = None
    is_default: bool = False


class DomandaProOut(BaseModel):
    """Una domanda del pannello con il valore GIA' risolto (D-07): la
    risposta salvata se valida, altrimenti il default di catalogo."""

    code: str
    testo: str
    help: str | None = None
    tipo_controllo: str
    opzioni: list[OpzioneProOut] = []
    valore: int | str | None = None
    valore_etichetta: str | None = None


class RigaIvaOut(BaseModel):
    iva_pct: Decimal
    min: Decimal
    max: Decimal


class RiepilogoIvaOut(BaseModel):
    """Riepilogo D-16 del dettaglio Pro: imponibile lavori, IVA per aliquota,
    extra, totale IVA inclusa. Solo valori lato cliente."""

    imponibile_lavori_min: Decimal
    imponibile_lavori_max: Decimal
    righe_iva: list[RigaIvaOut]
    extra: list[ExtraOut]
    extra_totale: Decimal
    totale_min: Decimal
    totale_max: Decimal


class LetturaCategoriaOut(BaseModel):
    code: str
    eur_mq_min: int | None = None
    eur_mq_max: int | None = None
    peso_etichetta: str
    peso_fill_pct: float


class DettaglioProOut(BaseModel):
    categorie: list[CategoriaDettagliataOut]
    totale_min: Decimal
    totale_max: Decimal
    # Totale lavori Pro IVA inclusa + extra attivi: base di barra e budget (A2).
    # totale_min/max restano il totale Pro IVA esclusa del motore.
    totale_ivato_min: Decimal | None = None
    totale_ivato_max: Decimal | None = None
    riepilogo_iva: RiepilogoIvaOut | None = None
    # EUR/m2 (IVA esclusa) e peso per categoria, solo categorie nel totale lavori.
    lettura_categorie: list[LetturaCategoriaOut] = []
    # Ricalcolo Pro con un livello di finitura sotto; IVA inclusa (D-10).
    confronto_finiture: ConfrontoFinitureOut | None = None
    finiture_al_minimo: bool = False
    # Bonus fiscali calcolati sui totali Pro (10-14, G6), stesso DTO del Free.
    bonus: BonusOut | None = None
    budget_eur: int | None = None
    # Eco delle risposte PERSISTITE ({codice: valore}), mai quelle del wizard
    # (che restano nel loro snapshot): un dict generico, non piu' tre campi
    # cablati (09-05).
    risposte: dict[str, int | str] = {}
    # True se l'utente ha DAVVERO risposto alle domande del pannello, cioe' se
    # `stima.risposte_pro_json` non e' NULL. Serve al client per decidere se
    # riaprire il pannello domande: dedurlo da una risposta qualsiasi diversa
    # da zero sbaglia sulla risposta legittima "tutti zero", che e'
    # esattamente cio' che invia il form Pro di chi non ha bagni da rifare.
    risposte_salvate: bool = False
    # Le domande del pannello, dal catalogo — nessuna etichetta cablata nel
    # client (CFG-01/QST-05). La finitura NON compare qui: resta sul
    # selettore per categoria esistente.
    domande: list[DomandaProOut] = []
    # Livelli EFFETTIVAMENTE applicati, in eco: la scelta dell'utente risolta
    # coi default di tabella. Il client mostra questi, non quelli che ha
    # mandato, altrimenti alla prima stima (senza scelta) non saprebbe cosa e'
    # stato applicato.
    livelli: dict[str, str] = {}
    # Catalogo dei livelli disponibili, cosi' la schermata Pro costruisce i
    # selettori senza una seconda chiamata.
    livelli_disponibili: list[LivelloFinituraOut] = []


class RisposteDomandeRequest(BaseModel):
    """Payload generico del pannello (09-05): un dict `{codice: valore}` al
    posto di tre campi cablati. `extra="forbid"` rifiuta qualunque campo
    top-level diverso da `risposte`/`livelli` — non e' piu' possibile
    postare `{"bagni": 2}` a livello radice, deve stare sotto `risposte`."""

    model_config = ConfigDict(extra="forbid")

    risposte: Risposte = Field(default_factory=dict)
    # Livelli di finitura per categoria ({"B-FINITURE": "medio", ...}). Chiavi e
    # valori sono validati contro il DB dal router (400), MAI fidati: qui il
    # tipo garantisce solo la forma. `None` = non toccare i livelli gia'
    # salvati; `{}` non e' un caso distinto perche' un dict vuoto significa
    # comunque "nessuna scelta" e il motore applica i default.
    livelli: dict[str, str] | None = None
