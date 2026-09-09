"""Request/response schemas for GET/POST /me/stime/{id}/dettaglio-pro
(03-03-PLAN.md Task 2).

DTO a campi chiusi: nessun prezzo/moltiplicatore di listino ne' alcun dato
di margine riservato all'impresa in nessun modello di questo modulo (stessa
disciplina anti-leak di `schemas/stima.py`). Nessun `model_validate` su
entita' ORM — le risposte sono costruite campo-per-campo dal router.

`RisposteDomandeRequest` limita l'input non fidato (ASVS V5, T-03-07):
bagni/porte/condizionatori sono interi non negativi con un tetto massimo,
stesso pattern di `StimaRequest.mq`.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


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


class RisposteDomandeOut(BaseModel):
    bagni: int = 0
    porte: int = 0
    condizionatori: int = 0


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


class DettaglioProOut(BaseModel):
    categorie: list[CategoriaDettagliataOut]
    totale_min: Decimal
    totale_max: Decimal
    risposte: RisposteDomandeOut
    # True se l'utente ha DAVVERO risposto alle domande mirate, cioe' se
    # `stima.risposte_pro_json` non e' NULL. Serve al client per decidere se
    # riaprire il pannello domande: dedurlo da `bagni+porte+condizionatori > 0`
    # sbaglia sulla risposta legittima {0, 0, 0}, che e' esattamente cio' che
    # invia il form Pro di chi non ha bagni da rifare.
    risposte_salvate: bool = False
    # Livelli EFFETTIVAMENTE applicati, in eco: la scelta dell'utente risolta
    # coi default di tabella. Il client mostra questi, non quelli che ha
    # mandato, altrimenti alla prima stima (senza scelta) non saprebbe cosa e'
    # stato applicato.
    livelli: dict[str, str] = {}
    # Catalogo dei livelli disponibili, cosi' la schermata Pro costruisce i
    # selettori senza una seconda chiamata.
    livelli_disponibili: list[LivelloFinituraOut] = []


class RisposteDomandeRequest(BaseModel):
    bagni: int = Field(ge=0, le=20)
    porte: int = Field(ge=0, le=100)
    condizionatori: int = Field(ge=0, le=50)
    # Livelli di finitura per categoria ({"B-FINITURE": "medio", ...}). Chiavi e
    # valori sono validati contro il DB dal router (400), MAI fidati: qui il
    # tipo garantisce solo la forma. `None` = non toccare i livelli gia'
    # salvati; `{}` non e' un caso distinto perche' un dict vuoto significa
    # comunque "nessuna scelta" e il motore applica i default.
    livelli: dict[str, str] | None = None
