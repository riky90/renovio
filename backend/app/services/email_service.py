"""Transactional email utility (D-04) — minimal SMTP abstraction, reusable
by the Fase 4 lead-notification flow without refactor (same env-var-driven
shape: `to`/`subject`/`html_body` in, nothing SMTP-specific leaks to
callers).

Uses `aiosmtplib` directly against `SMTP_HOST/PORT/USER/PASSWORD/FROM`
(settings) — no provider-specific code, any standard SMTP relay works via
env vars alone. In dev, when `SMTP_HOST` is not configured, the email
content is logged instead of attempting a real send: this is an explicit,
documented fallback (never a silent failure and never a raised exception),
so the reset-password flow stays fully usable without real SMTP
credentials in every environment. Never raises or connects at import time
— safe to import with an entirely empty SMTP config.
"""

from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_body: str) -> None:
    if not settings.SMTP_HOST:
        logger.info(
            "SMTP non configurato (dev fallback) — email non inviata.\nTo: %s\nSubject: %s\nBody:\n%s",
            to,
            subject,
            html_body,
        )
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM or settings.SMTP_USER
    message["To"] = to
    message["Subject"] = subject
    message.set_content("Questo messaggio richiede un client email che supporti HTML.")
    message.add_alternative(html_body, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER or None,
        password=settings.SMTP_PASSWORD or None,
        start_tls=True,
    )
