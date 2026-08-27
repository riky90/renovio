"""Server-side PDF rendering for the branded estimate PDFs (PDF-01/PDF-02, D-11).

`PdfService.render()` (Free) reads ONLY `StimaSalvata.risultato_json` — the
frozen snapshot written once at save time (02-07) — and renders it through
the Jinja2 template `templates/pdf_stima.html` with WeasyPrint. This method
must NEVER import or call the estimation engine (D-09/Pitfall 5, T-08-03):
the downloaded PDF must always match exactly what the user saw and saved,
even if admin-managed listini/coefficienti change later.

`PdfService.render_pro()` (Pro, 03-04) is DELIBERATELY the opposite: it
renders a `DettaglioProResult` that was calculated LIVE by the caller (the
router), via the exact same compute call used by the on-screen dettaglio-pro
JSON endpoint (03-RESEARCH.md Pitfall 2) — so screen and PDF can never
diverge, and the Pro detail stays responsive to admin-tuned coefficients
(Fase 4). This asymmetry with `render()` is intentional, not an oversight —
a future refactor must NOT "fix" `render_pro()` to read a frozen snapshot
instead, and must NOT "fix" `render()` to recompute live.
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

if TYPE_CHECKING:
    from app.services.dettaglio_pro import DettaglioProResult

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


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


class PdfService:
    """Renders the branded Free PDF from an immutable `StimaSalvata` snapshot."""

    @staticmethod
    def render(stima: StimaSalvata, user: User) -> bytes:
        # Imported lazily: WeasyPrint's native GTK/Pango/Cairo runtime may be
        # missing in local dev (Windows, 02-RESEARCH.md Pitfall 3). Deferring
        # the import here keeps the rest of the app importable/testable even
        # when the native lib isn't installed; only an actual PDF render
        # attempt fails, not the whole process.
        from weasyprint import HTML

        template = _env.get_template("pdf_stima.html")
        filename = build_filename(stima)
        html_content = template.render(
            stima=stima.risultato_json,
            nome=user.nome,
            data_generazione=datetime.now().strftime("%d/%m/%Y"),
            filename=filename,
        )
        return HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf()

    @staticmethod
    def render_pro(dettaglio: "DettaglioProResult", stima: StimaSalvata, user: User) -> bytes:
        """Renders the Pro multi-page branded PDF from a `DettaglioProResult`
        the caller already computed LIVE (see module docstring — this is the
        deliberate recompute-live asymmetry with `render()`, D-09/Pitfall 2).
        This method never calls the compute service itself: the router owns
        the single call site shared with the JSON dettaglio-pro endpoint, so
        the numbers can never drift apart."""
        from weasyprint import HTML

        template = _env.get_template("pdf_stima_pro.html")
        filename = build_filename_pro(stima)
        html_content = template.render(
            dettaglio=dettaglio,
            nome=user.nome,
            data_generazione=datetime.now().strftime("%d/%m/%Y"),
            citta=stima.citta,
            mq=stima.mq,
            tipo=stima.tipo,
            filename=filename,
        )
        return HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf()
