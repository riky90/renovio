"""Funzioni pure di PRESENTAZIONE del risultato Free, usate dai PDF.

Nessuna query, nessun import del motore di stima o di modelli ORM: leggono solo dict
nella forma dello snapshot `risultato_json` (i Decimal arrivano come stringhe).
Sono il mirror di `frontend/src/lib/risultato.ts`: ogni modifica va fatta su
entrambi i lati, cosi' web e PDF dicono le stesse cose.

Le costanti qui sono geometria della barra (D-11), non prezzi.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

FATTORE_TETTO = Decimal("1.2")
LARGHEZZA_MINIMA_PCT = 4
SOGLIA_PASSO = 100000
PASSO_PICCOLO = 1000
PASSO_GRANDE = 5000

# `min`/`max` sono nomi di parametri di scala_barra: alias dei builtin per il corpo.
max_ = max
min_ = min


def _dec(value) -> Decimal:
    """Accetta Decimal/int/float/str (snapshot JSON)."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True)
class ScalaBarra:
    tetto: int
    left_pct: float
    right_pct: float
    budget_pct: float | None

    @property
    def width_pct(self) -> float:
        return self.right_pct - self.left_pct


@dataclass(frozen=True)
class PesoCategoria:
    etichetta: str
    fill_pct: float


@dataclass(frozen=True)
class RigaIva:
    iva_pct: Decimal
    min: Decimal
    max: Decimal

    @property
    def etichetta(self) -> str:
        return f"IVA {round(self.iva_pct * 100)}%"


@dataclass(frozen=True)
class Riepilogo:
    imponibile_lavori_min: Decimal
    imponibile_lavori_max: Decimal
    righe_iva: list[RigaIva]
    extra: list[dict]
    extra_totale: Decimal
    totale_min: Decimal
    totale_max: Decimal


def scala_barra(min, max, budget=None) -> ScalaBarra:  # noqa: A002
    """Asse 0 -> tetto (D-11): il segmento min-max occupa la sua quota reale."""
    mn = float(_dec(min))
    mx = float(_dec(max))
    bud = float(_dec(budget)) if budget else 0.0
    grezzo = max_(float(FATTORE_TETTO) * mx, bud)
    passo = PASSO_PICCOLO if grezzo < SOGLIA_PASSO else PASSO_GRANDE
    tetto = max_(passo, math.ceil(grezzo / passo) * passo)

    left = mn / tetto * 100
    right = mx / tetto * 100
    if right - left < LARGHEZZA_MINIMA_PCT:
        centro = (left + right) / 2
        left = centro - LARGHEZZA_MINIMA_PCT / 2
        right = centro + LARGHEZZA_MINIMA_PCT / 2
        if left < 0:
            right -= left
            left = 0
        if right > 100:
            left -= right - 100
            right = 100
        left = max_(0, left)
        right = min_(100, right)

    budget_pct = bud / tetto * 100 if bud > 0 else None
    return ScalaBarra(tetto=int(tetto), left_pct=left, right_pct=right, budget_pct=budget_pct)


def _euro(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def incidenza_eur_mq(imp_min, imp_max, mq) -> tuple[int, int] | None:
    """Incidenza EUR/m2 su imponibile (IVA esclusa), D-14."""
    m = _dec(mq) if mq is not None else Decimal(0)
    if not m > 0:
        return None
    return _euro(_dec(imp_min) / m), _euro(_dec(imp_max) / m)


def somma_medi(categorie: list[dict]) -> Decimal:
    """Denominatore del peso: solo categorie, senza extra ne' arredo."""
    total = Decimal(0)
    for c in categorie:
        total += (_dec(c["totale_min"]) + _dec(c["totale_max"])) / 2
    return total


def peso_categoria(cat_min, cat_max, somma) -> PesoCategoria:
    """Peso della categoria sul valore medio (D-15)."""
    s = _dec(somma)
    if s <= 0:
        return PesoCategoria("0%", 0)
    raw = float((_dec(cat_min) + _dec(cat_max)) / 2 / s * 100)
    etichetta = "<1%" if raw < 1 else f"{_euro(Decimal(str(raw)))}%"
    return PesoCategoria(etichetta, min_(100.0, max_(raw, 2.0)))


def riepilogo_iva(categorie: list[dict], extra: list[dict], totale: dict) -> Riepilogo:
    """Riepilogo D-16. L'imponibile lavori somma le categorie (totale.imponibile
    include gli extra). La riga con aliquota piu' alta assorbe l'arrotondamento
    cosi' che le righe sommino esattamente a totale.iva."""
    gruppi: dict[Decimal, list[Decimal]] = {}

    def riga(iva_pct: Decimal) -> list[Decimal]:
        return gruppi.setdefault(iva_pct.normalize(), [Decimal(0), Decimal(0)])

    imp_min = Decimal(0)
    imp_max = Decimal(0)
    for c in categorie:
        imp_min += _dec(c["imponibile_min"])
        imp_max += _dec(c["imponibile_max"])
        r = riga(_dec(c["iva_pct"]))
        r[0] += _dec(c["iva_min"])
        r[1] += _dec(c["iva_max"])

    extra_totale = Decimal(0)
    for e in extra:
        importo = _dec(e["importo"])
        extra_totale += importo
        iva = importo * _dec(e["iva_pct"])
        r = riga(_dec(e["iva_pct"]))
        r[0] += iva
        r[1] += iva

    chiavi = sorted(gruppi)
    if chiavi:
        altre_min = sum((gruppi[k][0] for k in chiavi[:-1]), Decimal(0))
        altre_max = sum((gruppi[k][1] for k in chiavi[:-1]), Decimal(0))
        gruppi[chiavi[-1]][0] = _dec(totale["iva_min"]) - altre_min
        gruppi[chiavi[-1]][1] = _dec(totale["iva_max"]) - altre_max

    righe = [RigaIva(k, gruppi[k][0], gruppi[k][1]) for k in chiavi]
    return Riepilogo(
        imponibile_lavori_min=imp_min,
        imponibile_lavori_max=imp_max,
        righe_iva=righe,
        extra=list(extra),
        extra_totale=extra_totale,
        totale_min=_dec(totale["totale_min"]),
        totale_max=_dec(totale["totale_max"]),
    )


def livello_corrente(opzioni: list[tuple[str, int, bool]], scelto: str | None) -> str | None:
    """Il livello effettivo: quello scelto se e' tra le opzioni, altrimenti il default.

    `opzioni` = (code, ordine, is_default). Nessun livello e' cablato: l'ordine
    arriva dai dati (`opzione_domanda.ordine`)."""
    codici = {c for c, _, _ in opzioni}
    if scelto in codici:
        return scelto
    for code, _, is_default in opzioni:
        if is_default:
            return code
    return None


def livello_inferiore(opzioni: list[tuple[str, int, bool]], scelto: str | None) -> str | None:
    """Il livello un gradino sotto quello corrente; None se gia' al minimo o se
    il codice scelto e' sconosciuto."""
    ordinate = sorted(opzioni, key=lambda o: o[1])
    codici = [c for c, _, _ in ordinate]
    if scelto is not None and scelto not in codici:
        return None
    corrente = livello_corrente(opzioni, scelto)
    if corrente is None:
        return None
    idx = codici.index(corrente)
    return codici[idx - 1] if idx > 0 else None
