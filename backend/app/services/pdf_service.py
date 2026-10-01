"""Server-side PDF rendering for the branded estimate PDFs (PDF-01/PDF-02, D-11).

`PdfService.render()` (Free) reads ONLY `StimaSalvata.risultato_json` — the
frozen snapshot written once at save time (02-07) — and renders it through
the Jinja2 template `templates/pdf_stima.html` with WeasyPrint. This method
must NEVER import or call the estimation engine (D-09/Pitfall 5, T-08-03):
the downloaded PDF must always match exactly what the user saw and saved,
even if admin-managed listini/coefficienti change later.

`PdfService.render_pro()` (Pro, 03-04) is DELIBERATELY the opposite: it
renders a `CalcoloDettaglioPro` (risultato Pro + riepilogo IVA + lettura)
that was calculated LIVE by the caller (the router), via the exact same compute call used by the on-screen dettaglio-pro
JSON endpoint (03-RESEARCH.md Pitfall 2) — so screen and PDF can never
diverge, and the Pro detail stays responsive to admin-tuned coefficients
(Fase 4). This asymmetry with `render()` is intentional, not an oversight —
a future refactor must NOT "fix" `render_pro()` to read a frozen snapshot
instead, and must NOT "fix" `render()` to recompute live.

Nota (0009): `stima.tier` congela il piano con cui la stima e' nata, e il
router rifiuta `pdf-pro` su una stima Free. Questo NON intacca l'asimmetria
qui descritta — congela CHI puo' scaricare il PDF Pro, non COME viene
calcolato. Il calcolo di `render_pro()` resta live.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from app.models.stima_salvata import StimaSalvata
from app.models.user import User
from app.services.risultato import (
    avviso_budget,
    incidenza_eur_mq,
    peso_categoria,
    riepilogo_iva,
    scala_barra,
    somma_medi,
)

if TYPE_CHECKING:
    from app.routers.dettaglio_pro import CalcoloDettaglioPro

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


def _fmt_eur(value) -> str:
    """Formatta un importo come intero in stile italiano: separatore delle
    migliaia con il punto e nessun decimale. Es. 47985.4 -> '47.985'.
    Usato SOLO per gli importi monetari nei PDF (non per le quantita', che
    conservano i decimali). Non altera il valore in DB: e' pura presentazione.
    """
    try:
        n = round(float(value))
    except (TypeError, ValueError):
        return str(value)
    # f-string usa la virgola come separatore migliaia -> la trasformo in punto.
    return f"{n:,.0f}".replace(",", ".")


_env.filters["eur"] = _fmt_eur


def _fmt_pct(value) -> str:
    """Float -> 2 decimali con il punto, per valori CSS (mai la virgola)."""
    return f"{float(value):.2f}"


_env.filters["pct"] = _fmt_pct


def _slugify(value: str) -> str:
    """ASCII, lowercase, hyphen-separated slug for the filename (D-12)."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "stima"


def build_filename(stima: StimaSalvata) -> str:
    """`stima-ristrutturazione-<citta-slug>-<YYYY-MM-DD>.pdf` (D-12)."""
    citta_slug = _slugify(stima.citta)
    data_str = stima.created_at.strftime("%Y-%m-%d")
    return f"stima-ristrutturazione-{citta_slug}-{data_str}.pdf"


def build_filename_pro(stima: StimaSalvata) -> str:
    """`stima-ristrutturazione-<citta-slug>-dettaglio-<YYYY-MM-DD>.pdf`."""
    citta_slug = _slugify(stima.citta)
    data_str = stima.created_at.strftime("%Y-%m-%d")
    return f"stima-ristrutturazione-{citta_slug}-dettaglio-{data_str}.pdf"


def _etichetta_rata(voci: list[dict]) -> str:
    """Etichetta della rata annua aggregata, derivata dal `rate_annuali` di
    ogni voce (dato admin, mai cablato: WR-05). Con durate diverse la rata
    aggregata e' la somma delle rate solo finche' tutte le voci sono attive,
    cioe' nei primi N anni con N = durata piu' breve. Snapshot senza
    `rate_annuali` sulle voci: nessuna durata dichiarata."""
    durate = sorted({int(v["rate_annuali"]) for v in voci if v.get("rate_annuali")})
    if not durate:
        return "Rata annua"
    n = durate[0]
    periodo = "1 anno" if n == 1 else f"{n} anni"
    if len(durate) == 1:
        return f"Rata annua ({periodo})"
    return "Rata annua (primo anno)" if n == 1 else f"Rata annua (primi {periodo})"


def _bonus_pdf(bonus: dict | None) -> dict | None:
    """Presentazione del blocco bonus per il PDF Free (G10): separa le voci sui
    lavori da quelle sull'arredo (`su_arredo`, decisa dal server) e sceglie i
    totali sui soli lavori, con ripiego sui totali complessivi per gli snapshot
    precedenti a G5/G10. Nessun calcolo: solo scelta di campi gia' congelati."""
    if not bonus:
        return None
    voci = bonus.get("bonus") or []

    def _pick(preferito: str, ripiego: str):
        v = bonus.get(preferito)
        return v if v is not None else bonus.get(ripiego)

    lavori = [v for v in voci if not v.get("su_arredo")]
    return {
        "lavori": lavori,
        "arredo": [v for v in voci if v.get("su_arredo")],
        "etichetta_rata": _etichetta_rata(lavori),
        "detrazione_min": _pick("detrazione_lavori_min", "detrazione_min"),
        "detrazione_max": _pick("detrazione_lavori_max", "detrazione_max"),
        "rata_min": _pick("rata_annua_lavori_min", "rata_annua_min"),
        "rata_max": _pick("rata_annua_lavori_max", "rata_annua_max"),
        "disclaimer": bonus.get("disclaimer"),
    }


class PdfService:
    """Renders the branded Free PDF from an immutable `StimaSalvata` snapshot."""

    @staticmethod
    def render_html(stima: StimaSalvata, user: User) -> str:
        """HTML del PDF Free, calcolato SOLO dallo snapshot `risultato_json`
        (piu' i derivati di presentazione di `services/risultato.py`).
        Separato da `render()` cosi' e' testabile senza WeasyPrint."""
        snap = stima.risultato_json
        categorie = snap.get("categorie") or []
        extra = snap.get("extra") or []
        totale = snap["totale"]
        mq = (snap.get("input") or {}).get("mq")
        # Il budget vive in una colonna della stessa riga, non nel motore: la
        # stima pre-fase ha NULL e il PDF non emette ne' tacca ne' riquadro.
        budget = getattr(stima, "budget_eur", None)

        # Base IVA esclusa (G2). Gli snapshot piu' vecchi senza imponibile_* per
        # categoria ricadono su totale_* per non far fallire il PDF.
        def _imp(c: dict) -> tuple:
            return (
                c.get("imponibile_min", c["totale_min"]),
                c.get("imponibile_max", c["totale_max"]),
            )

        somma = somma_medi(
            [{"imponibile_min": _imp(c)[0], "imponibile_max": _imp(c)[1]} for c in categorie]
        )
        derivati = {
            c["code"]: {
                "incidenza": incidenza_eur_mq(c["imponibile_min"], c["imponibile_max"], mq),
                "peso": peso_categoria(_imp(c)[0], _imp(c)[1], somma),
            }
            for c in categorie
        }

        template = _env.get_template("pdf_stima.html")
        return template.render(
            stima=snap,
            bonus_pdf=_bonus_pdf(snap.get("bonus")),
            nome=user.nome,
            data_generazione=datetime.now().strftime("%d/%m/%Y"),
            filename=build_filename(stima),
            barra=scala_barra(totale["totale_min"], totale["totale_max"], budget),
            riepilogo=riepilogo_iva(categorie, extra, totale),
            derivati_categorie=derivati,
            budget_eur=budget,
            avviso=avviso_budget(
                budget,
                totale["totale_min"],
                totale["totale_max"],
                snap.get("confronto_finiture"),
                bool(snap.get("finiture_al_minimo", False)),
            ),
        )

    @staticmethod
    def render(stima: StimaSalvata, user: User) -> bytes:
        # Imported lazily: WeasyPrint's native GTK/Pango/Cairo runtime may be
        # missing in local dev (Windows, 02-RESEARCH.md Pitfall 3). Deferring
        # the import here keeps the rest of the app importable/testable even
        # when the native lib isn't installed; only an actual PDF render
        # attempt fails, not the whole process.
        from weasyprint import HTML

        html_content = PdfService.render_html(stima, user)
        return HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf()

    @staticmethod
    def render_html_pro(calcolo: "CalcoloDettaglioPro", stima: StimaSalvata, user: User) -> str:
        """HTML del PDF Pro. `calcolo` arriva dall'unico `_compute_dettaglio` del
        router: riepilogo IVA, EUR/m2 e peso sono gli stessi valori della vista
        Pro a schermo; qui non si chiama nessun motore."""
        riepilogo = calcolo.riepilogo
        confronto = calcolo.confronto.model_dump(mode="json") if calcolo.confronto else None
        template = _env.get_template("pdf_stima_pro.html")
        return template.render(
            dettaglio=calcolo.result,
            riepilogo=riepilogo,
            lettura={lc.code: lc for lc in calcolo.lettura},
            barra=scala_barra(riepilogo.totale_min, riepilogo.totale_max, stima.budget_eur),
            avviso=avviso_budget(
                stima.budget_eur,
                riepilogo.totale_min,
                riepilogo.totale_max,
                confronto,
                calcolo.finiture_al_minimo,
                mostra_totale=True,
            ),
            nome=user.nome,
            data_generazione=datetime.now().strftime("%d/%m/%Y"),
            citta=stima.citta,
            mq=stima.mq,
            tipo=stima.tipo,
            filename=build_filename_pro(stima),
        )

    @staticmethod
    def render_pro(calcolo: "CalcoloDettaglioPro", stima: StimaSalvata, user: User) -> bytes:
        """Renders the Pro multi-page branded PDF from the `CalcoloDettaglioPro`
        the caller already computed LIVE (see module docstring: this is the
        deliberate recompute-live asymmetry with `render()`, D-09/Pitfall 2).
        This method never calls the compute service itself: the router owns
        the single call site shared with the JSON dettaglio-pro endpoint, so
        the numbers can never drift apart."""
        from weasyprint import HTML

        html_content = PdfService.render_html_pro(calcolo, stima, user)
        return HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf()
