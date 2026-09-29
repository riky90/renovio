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


def riepilogo_iva_pro(
    categorie: list[tuple[Decimal, Decimal, Decimal]], extra: list[dict]
) -> Riepilogo:
    """Riepilogo IVA del dettaglio Pro (A2, D-16), stessa forma di `Riepilogo`.

    Il motore Pro somma prezzi cliente SENZA IVA ne' extra: qui l'IVA si applica per
    categoria (`categorie` = (imponibile_min, imponibile_max, iva_pct), solo quelle
    del totale lavori) e gli extra attivi entrano lordi, come nel Free
    (importo x (1 + iva) all'euro, ROUND_HALF_UP). Nessuna aliquota cablata."""
    gruppi: dict[Decimal, list[Decimal]] = {}

    def riga(iva_pct: Decimal) -> list[Decimal]:
        return gruppi.setdefault(iva_pct.normalize(), [Decimal(0), Decimal(0)])

    imp_min = Decimal(0)
    imp_max = Decimal(0)
    for c_min, c_max, iva_pct in categorie:
        c_min, c_max, aliq = _dec(c_min), _dec(c_max), _dec(iva_pct)
        imp_min += c_min
        imp_max += c_max
        r = riga(aliq)
        r[0] += (c_min * aliq).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        r[1] += (c_max * aliq).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    extra_totale = Decimal(0)
    for e in extra:
        importo = _dec(e["importo"])
        aliq = _dec(e["iva_pct"])
        lordo = (importo * (Decimal(1) + aliq)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        extra_totale += importo
        r = riga(aliq)
        r[0] += lordo - importo
        r[1] += lordo - importo

    chiavi = sorted(gruppi)
    righe = [RigaIva(k, gruppi[k][0], gruppi[k][1]) for k in chiavi]
    iva_min = sum((r.min for r in righe), Decimal(0))
    iva_max = sum((r.max for r in righe), Decimal(0))
    return Riepilogo(
        imponibile_lavori_min=imp_min,
        imponibile_lavori_max=imp_max,
        righe_iva=righe,
        extra=list(extra),
        extra_totale=extra_totale,
        totale_min=imp_min + iva_min + extra_totale,
        totale_max=imp_max + iva_max + extra_totale,
    )


@dataclass(frozen=True)
class LetturaCategoria:
    code: str
    eur_mq_min: int | None
    eur_mq_max: int | None
    peso_etichetta: str
    peso_fill_pct: float


def lettura_categorie_pro(
    categorie: list[tuple[str, Decimal, Decimal]], mq
) -> list[LetturaCategoria]:
    """EUR/m2 (IVA esclusa) e peso sul valore medio per categoria (D-14, D-15, A3):
    composizione di `incidenza_eur_mq`, `somma_medi` e `peso_categoria`; il
    denominatore e' la somma dei medi delle sole categorie passate."""
    somma = somma_medi([{"totale_min": mn, "totale_max": mx} for _, mn, mx in categorie])
    out: list[LetturaCategoria] = []
    for code, mn, mx in categorie:
        inc = incidenza_eur_mq(mn, mx, mq)
        peso = peso_categoria(mn, mx, somma)
        out.append(
            LetturaCategoria(
                code=code,
                eur_mq_min=inc[0] if inc else None,
                eur_mq_max=inc[1] if inc else None,
                peso_etichetta=peso.etichetta,
                peso_fill_pct=peso.fill_pct,
            )
        )
    return out


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


# --- budget (RIS-04) e avviso nel PDF ------------------------------------------


def stato_budget(budget, min, max) -> str | None:  # noqa: A002
    """Confini esatti D-06 (identici a statoBudget in risultato.ts): budget < min
    fuori; min <= budget <= max limite; oltre dentro. Nessun budget -> None."""
    if budget is None or budget <= 0:
        return None
    if budget < _dec(min):
        return "fuori"
    if budget <= _dec(max):
        return "limite"
    return "dentro"


#: Testi dell'avviso: stesse stringhe di TESTI_AVVISO in frontend/src/lib/risultato.ts.
#: Un test legge il sorgente TS e verifica che ogni testo fisso compaia li' (A5).
TESTI_AVVISO = {
    "titolo_fuori": "La stima supera il tuo budget",
    "titolo_limite": "Il tuo budget è al limite",
    "titolo_dentro": "Rientri nel tuo budget",
    "corpo_limite": (
        "Rientra nel range della stima, ma dipende dalle scelte che farai. "
        "Le finiture sono la leva più semplice."
    ),
    "corpo_dentro": "Anche nel caso più alto della stima resti sotto {budget}.",
    "fuori_meno_lavori": (
        "Per stare nel tuo budget servono meno lavori: prova a togliere qualche intervento."
    ),
    "confronto_corpo": (
        "Con finiture {livello} la stessa ristrutturazione costerebbe {range} "
        "(IVA inclusa), circa {delta} in meno."
    ),
    "fuori_economiche": (
        "Hai già scelto finiture economiche. Per stare nel tuo budget servono meno lavori: "
        "prova a togliere qualche intervento."
    ),
    "nota": "Il budget non cambia il prezzo della stima.",
}


def _fmt_importo(value) -> str:
    n = int(_dec(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"{n:,.0f}".replace(",", ".")


def _fmt_range(a, b) -> str:
    return f"{_fmt_importo(a)} – {_fmt_importo(b)} €"


def avviso_budget(
    budget,
    totale_min,
    totale_max,
    confronto: dict | None,
    finiture_al_minimo: bool,
    mostra_totale: bool = False,
) -> dict | None:
    """Avviso budget per il PDF: {stato, titolo, corpo, righe, nota}. None senza budget.

    `confronto` e' il dict del confronto finiture (totali anche come stringhe di
    snapshot). Nessun calcolo di prezzo: solo differenze tra totali gia' calcolati."""
    stato = stato_budget(budget, totale_min, totale_max)
    if stato is None:
        return None

    t = TESTI_AVVISO
    titolo = t[f"titolo_{stato}"]
    if stato == "limite":
        corpo = t["corpo_limite"]
    elif stato == "dentro":
        corpo = t["corpo_dentro"].format(budget=f"{_fmt_importo(budget)} €")
    else:
        corpo = t["fuori_meno_lavori"]

    righe: list[tuple[str, str]] = []
    delta_testo = None
    livello = None
    if stato == "fuori" and confronto:
        a = _dec(totale_min) - _dec(confronto["totale_min"])
        b = _dec(totale_max) - _dec(confronto["totale_max"])
        if not (a <= 0 and b <= 0):
            livello = str(confronto["livello_nome"]).lower()
            delta_testo = _fmt_range(min_(a, b), max_(a, b))
            corpo = t["confronto_corpo"].format(
                livello=livello,
                range=_fmt_range(confronto["totale_min"], confronto["totale_max"]),
                delta=delta_testo,
            )
    if delta_testo is None and stato == "fuori" and finiture_al_minimo:
        corpo = t["fuori_economiche"]

    if mostra_totale or delta_testo is not None:
        righe.append(("Ora (IVA inclusa)", _fmt_range(totale_min, totale_max)))
    if delta_testo is not None:
        righe.append(
            (
                f"Con finiture {livello}",
                _fmt_range(confronto["totale_min"], confronto["totale_max"]),
            )
        )
    return {
        "stato": stato,
        "titolo": titolo,
        "corpo": corpo,
        "righe": righe,
        "delta": delta_testo,
        "nota": t["nota"],
    }
