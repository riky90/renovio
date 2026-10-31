"""Email del Pro: conferma dell'acquisto e ricevuta del recesso.

La conferma e' il "supporto durevole" del contratto a distanza (Codice del
Consumo, art. 51, c. 7): riepiloga piano, prezzo, rinnovo e recesso e rimanda
alle condizioni di vendita. La ricevuta del recesso e' quella chiesta
dall'art. 54-bis (funzione di recesso online).

Testi in HTML semplice, come le email dei lead (`routers/lead.py`). Nessun
dato interno: solo cio' che l'utente ha comprato.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from html import escape

from app.config import settings

MESI = (
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
)


def data_it(valore: datetime) -> str:
    return f"{valore.day} {MESI[valore.month - 1]} {valore.year}"


def euro(importo: Decimal) -> str:
    testo = f"{importo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{testo.removesuffix(',00')} €"


def _url(path: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}"


def _pagina(titolo: str, corpo: str) -> str:
    return (
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.5;'
        'color:#1f1f1f;max-width:560px">'
        f'<h1 style="font-size:20px;margin:0 0 16px">{escape(titolo)}</h1>{corpo}'
        '<p style="margin-top:24px;font-size:13px;color:#6b6b6b">Renovio — stime di ristrutturazione '
        "indicative e pre-sopralluogo.</p></div>"
    )


def conferma_acquisto(
    *,
    nome: str,
    piano_code: str | None,
    importo: Decimal | None,
    intervallo: str | None,
    rinnovo_il: datetime | None,
    recesso_fino_al: datetime | None,
) -> tuple[str, str]:
    """(oggetto, html) della conferma d'acquisto del Pro."""
    piano = "annuale" if piano_code == "annuale" or intervallo == "year" else "mensile"
    prezzo = ""
    if importo is not None:
        prezzo = f"{euro(importo)} {'all’anno' if piano == 'annuale' else 'al mese'}, IVA inclusa"
    righe = [f"<li><b>Piano:</b> Renovio Pro {piano}{f' — {prezzo}' if prezzo else ''}</li>"]
    if rinnovo_il is not None:
        righe.append(
            f"<li><b>Rinnovo automatico:</b> il {data_it(rinnovo_il)}, e poi ogni "
            f"{'anno' if piano == 'annuale' else 'mese'}, salvo disdetta</li>"
        )
    corpo = (
        f"<p>Ciao {escape(nome)},</p>"
        "<p>grazie per aver scelto Renovio Pro: il tuo abbonamento è attivo da subito.</p>"
        f"<ul>{''.join(righe)}</ul>"
        "<p><b>Disdetta.</b> Puoi disdire il rinnovo in qualsiasi momento da Impostazioni → Abbonamento → "
        "«Gestisci abbonamento»: il Pro resta attivo fino alla fine del periodo pagato.</p>"
    )
    if recesso_fino_al is not None:
        corpo += (
            f"<p><b>Diritto di recesso.</b> Puoi recedere entro il {data_it(recesso_fino_al)} con il "
            "pulsante «Recedi dal contratto qui» in Impostazioni → Abbonamento: ti rimborsiamo "
            "l'intero importo e il Pro si disattiva subito.</p>"
        )
    corpo += (
        f'<p><a href="{_url("/impostazioni/abbonamento")}">Il tuo abbonamento</a> · '
        f'<a href="{_url("/condizioni-di-vendita")}">Condizioni di vendita</a> · '
        f'<a href="{_url("/privacy")}">Informativa privacy</a></p>'
        "<p>Ricevi a parte da Stripe la ricevuta del pagamento.</p>"
    )
    return "Il tuo abbonamento Renovio Pro è attivo", _pagina("Benvenuto in Renovio Pro", corpo)


def ricevuta_recesso(*, nome: str, rimborsato: Decimal, receduto_il: datetime) -> tuple[str, str]:
    """(oggetto, html) della ricevuta del recesso."""
    corpo = (
        f"<p>Ciao {escape(nome)},</p>"
        f"<p>abbiamo ricevuto il tuo recesso dal contratto Renovio Pro il {data_it(receduto_il)}.</p>"
        "<ul>"
        "<li>L'abbonamento è chiuso e non si rinnoverà.</li>"
        f"<li>Rimborso: <b>{euro(rimborsato)}</b> sullo stesso metodo di pagamento. Di solito arriva "
        "in 5-10 giorni lavorativi, a seconda della banca.</li>"
        "<li>Il tuo account torna gratuito: le stime salvate restano.</li>"
        "</ul>"
        f'<p>Per qualsiasi domanda rispondi a questa email. <a href="{_url("/condizioni-di-vendita")}">'
        "Condizioni di vendita</a></p>"
    )
    return "Conferma del recesso da Renovio Pro", _pagina("Recesso ricevuto", corpo)
