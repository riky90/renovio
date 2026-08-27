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


class SottocategoriaOut(BaseModel):
    codice: str | None
    nome: str
    famiglia: str
    voci: list[VoceOut]


class CategoriaDettagliataOut(BaseModel):
    code: str
    nome: str
    sottocategorie: list[SottocategoriaOut]


class RisposteDomandeOut(BaseModel):
    bagni: int = 0
    porte: int = 0
    condizionatori: int = 0


class DettaglioProOut(BaseModel):
    categorie: list[CategoriaDettagliataOut]
    risposte: RisposteDomandeOut


class RisposteDomandeRequest(BaseModel):
    bagni: int = Field(ge=0, le=20)
    porte: int = Field(ge=0, le=100)
    condizionatori: int = Field(ge=0, le=50)
