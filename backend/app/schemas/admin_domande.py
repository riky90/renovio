"""Schemi admin del catalogo domande (0014).

Stesso fork deliberato di `schemas/admin_coefficienti.py`: queste classi sono
usate SOLO dalle route di `routers/admin/domande.py`, tutte dietro
`Depends(require_admin)`, e non sono mai le stesse classi degli schemi pubblici
(`schemas/stima.py`). Nessun campo di questo modulo espone il margine impresa:
le correzioni del catalogo sono in euro-cliente, come `base_eur_mq`.

Bound numerici e di lunghezza ovunque (ASVS V5): anche un endpoint admin riceve
input, e un admin che sbaglia a incollare non deve poter scrivere una stringa da
un megabyte in una colonna String(64).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class DomandaAdminOut(BaseModel):
    code: str
    testo: str
    help: str | None
    tipo_controllo: str
    gruppo: str
    ordine: int
    tier_minimo: str
    attributo_code: str | None
    obbligatoria: bool
    visibile_se_domanda_code: str | None
    visibile_se_opzione_code: str | None
    attiva: bool


class DomandaAdminCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    testo: str = Field(min_length=1, max_length=300)
    help: str | None = Field(default=None, max_length=500)
    tipo_controllo: str = Field(min_length=1, max_length=24)
    gruppo: str = Field(default="", max_length=64)
    ordine: int = Field(default=0, ge=0, le=10_000)
    tier_minimo: str = Field(default="free", max_length=8)
    attributo_code: str | None = Field(default=None, max_length=32)
    obbligatoria: bool = False
    visibile_se_domanda_code: str | None = Field(default=None, max_length=64)
    visibile_se_opzione_code: str | None = Field(default=None, max_length=64)
    attiva: bool = True


class DomandaAdminIn(BaseModel):
    """PATCH: `exclude_unset` sul model_dump, quindi omettere un campo lo lascia
    com'e' — stesso contratto del PATCH su `voce.livello`."""

    testo: str | None = Field(default=None, min_length=1, max_length=300)
    help: str | None = Field(default=None, max_length=500)
    tipo_controllo: str | None = Field(default=None, min_length=1, max_length=24)
    gruppo: str | None = Field(default=None, max_length=64)
    ordine: int | None = Field(default=None, ge=0, le=10_000)
    tier_minimo: str | None = Field(default=None, max_length=8)
    attributo_code: str | None = Field(default=None, max_length=32)
    obbligatoria: bool | None = None
    visibile_se_domanda_code: str | None = Field(default=None, max_length=64)
    visibile_se_opzione_code: str | None = Field(default=None, max_length=64)
    attiva: bool | None = None


class OpzioneAdminOut(BaseModel):
    id: int
    domanda_code: str
    code: str
    etichetta: str
    descrizione: str | None
    immagine_url: str | None
    is_default: bool
    ordine: int
    attiva: bool


class OpzioneAdminCreateIn(BaseModel):
    domanda_code: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=64)
    etichetta: str = Field(min_length=1, max_length=200)
    descrizione: str | None = Field(default=None, max_length=500)
    immagine_url: str | None = Field(default=None, max_length=500)
    is_default: bool = False
    ordine: int = Field(default=0, ge=0, le=10_000)
    attiva: bool = True


class OpzioneAdminIn(BaseModel):
    etichetta: str | None = Field(default=None, min_length=1, max_length=200)
    descrizione: str | None = Field(default=None, max_length=500)
    immagine_url: str | None = Field(default=None, max_length=500)
    is_default: bool | None = None
    ordine: int | None = Field(default=None, ge=0, le=10_000)
    attiva: bool | None = None


class EffettoAdminOut(BaseModel):
    id: int
    opzione_id: int
    domanda_code: str
    opzione_code: str
    bersaglio: str
    tipo_effetto: str
    target_categoria_code: str | None
    target_sottocategoria_id: int | None
    target_voce_id: int | None
    tipo_code: str | None
    valore: Decimal | None
    attivo: bool


class EffettoAdminCreateIn(BaseModel):
    opzione_id: int
    tipo_effetto: str = Field(min_length=1, max_length=32)
    target_categoria_code: str | None = Field(default=None, max_length=32)
    target_sottocategoria_id: int | None = None
    target_voce_id: int | None = None
    tipo_code: str | None = Field(default=None, max_length=32)
    # Bound largo ma finito: regge sia un fattore (1.08) sia un importo
    # (1.900 EUR/unita'), e non lascia scrivere un numero che non significa
    # niente.
    valore: Decimal | None = Field(default=None, ge=-1_000_000, le=1_000_000)
    attivo: bool = True


class EffettoAdminIn(BaseModel):
    valore: Decimal | None = Field(default=None, ge=-1_000_000, le=1_000_000)
    tipo_code: str | None = Field(default=None, max_length=32)
    attivo: bool | None = None


class AttesaAdminOut(BaseModel):
    id: int
    attributo_code: str
    fascia_mq_min: int
    fascia_mq_max: int
    valore_atteso: Decimal
    attiva: bool


class AttesaAdminCreateIn(BaseModel):
    attributo_code: str = Field(min_length=1, max_length=32)
    fascia_mq_min: int = Field(ge=0, le=10_000)
    fascia_mq_max: int = Field(ge=0, le=10_000)
    valore_atteso: Decimal = Field(ge=0, le=10_000)
    attiva: bool = True


class AttesaAdminIn(BaseModel):
    fascia_mq_max: int | None = Field(default=None, ge=0, le=10_000)
    valore_atteso: Decimal | None = Field(default=None, ge=0, le=10_000)
    attiva: bool | None = None


# --- anteprima --------------------------------------------------------------


class EffettoTracciaOut(BaseModel):
    """Una riga di "cosa ha sparato". E' il materiale con cui si tara: senza,
    la curatela dei coefficienti e' a occhio."""

    domanda_code: str
    opzione_code: str
    tipo_effetto: str
    categoria_code: str | None
    valore: Decimal | None
    unita: Decimal | None
    contributo: Decimal | None
    applicato: bool
    nota: str | None


class AnteprimaCategoriaOut(BaseModel):
    code: str
    nome: str
    base_min: Decimal
    base_max: Decimal
    totale_min: Decimal
    totale_max: Decimal
    delta_min: Decimal
    delta_max: Decimal


class AnteprimaIn(BaseModel):
    citta: str = Field(min_length=1, max_length=100)
    mq: int = Field(ge=1, le=2000)
    tipo: str = Field(min_length=1, max_length=32)
    risposte: dict[str, object] = Field(default_factory=dict)


class AnteprimaOut(BaseModel):
    citta: str
    fallback: bool
    mq: int
    tipo: str
    attese: dict[str, Decimal]
    categorie: list[AnteprimaCategoriaOut]
    base_totale_min: Decimal
    base_totale_max: Decimal
    totale_min: Decimal
    totale_max: Decimal
    delta_min: Decimal
    delta_max: Decimal
    effetti: list[EffettoTracciaOut]
    avvisi: list[str]
