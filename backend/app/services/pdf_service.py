"""Server-side PDF rendering for the Free branded estimate (PDF-01, D-11).

`PdfService.render()` reads ONLY `StimaSalvata.risultato_json` — the frozen
snapshot written once at save time (02-07) — and renders it through the
Jinja2 template `templates/pdf_stima.html` with WeasyPrint. This module must
NEVER import or call the estimation engine (D-09/Pitfall 5, T-08-03): the
downloaded PDF must always match exactly what the user saw and saved, even
if admin-managed listini/coefficienti change later.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.models.stima_salvata import StimaSalvata
from app.models.user import User

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
