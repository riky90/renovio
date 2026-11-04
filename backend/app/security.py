"""Difese trasversali dell'API: IP reale, CSRF, header di sicurezza, tetto
alla dimensione delle richieste.

Middleware ASGI puri (non `BaseHTTPMiddleware`): non bufferizzano il body e
non rompono lo streaming dei file.

IP REALE
--------
Render sta dietro Cloudflare e il suo proxy APPENDE a `X-Forwarded-For`
invece di sostituirlo: il primo valore lo sceglie il client. Uvicorn con
`--forwarded-allow-ips="*"` usa proprio quel primo valore come
`request.client.host`, quindi un `X-Forwarded-For` casuale per richiesta
annullava ogni rate limit. Cloudflare invece SOVRASCRIVE `CF-Connecting-IP`
(e `True-Client-IP`) con l'indirizzo che vede: sono quelli di cui fidarsi.
In locale e nei test non ci sono, e si ricade su `request.client.host`.

CSRF
----
Il cookie di sessione e' `SameSite=None` (frontend su Vercel, API su Render:
domini diversi), quindi un sito qualunque puo' far partire una POST "semplice"
(form o multipart, nessun preflight CORS) col cookie dell'utente. Ogni
browser moderno manda `Origin` sulle richieste cross-origin che modificano:
se c'e' e non e' fra le origini ammesse, 403. Senza `Origin` (client non
browser, webhook Stripe, test) si guarda `Sec-Fetch-Site`: `cross-site` e'
rifiutato. Il webhook Stripe e' esente per nome: e' firmato.
"""

from __future__ import annotations

import json

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings

METODI_SICURI = frozenset({"GET", "HEAD", "OPTIONS"})
#: Percorsi chiamati da server terzi con la loro autenticazione (firma).
ESENTI_CSRF = ("/api/v1/stripe/webhook",)
#: Tetto al body di ogni richiesta. Il file piu' grande ammesso e' il listino
#: (10 MB, `listino_upload_service.MAX_UPLOAD_BYTES`) piu' l'involucro
#: multipart.
MAX_BODY_BYTES = 12 * 1024 * 1024


def client_ip(request: Request) -> str:
    """Indirizzo del client per rate limit e log: vedi docstring del modulo."""
    for header in ("cf-connecting-ip", "true-client-ip"):
        valore = request.headers.get(header)
        if valore:
            return valore.strip()
    return request.client.host if request.client else "sconosciuto"


def _origine(url: str) -> str:
    return url.rstrip("/").lower()


def origini_ammesse() -> frozenset[str]:
    return frozenset(
        _origine(o) for o in [*settings.cors_origins_list, settings.BACKEND_PUBLIC_URL] if o
    )


async def _rispondi(send: Send, status: int, dettaglio: str, extra: list | None = None) -> None:
    body = json.dumps({"detail": dettaglio}).encode()
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
        *(extra or []),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class OriginCheckMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in METODI_SICURI:
            await self.app(scope, receive, send)
            return
        if scope["path"] in ESENTI_CSRF:
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        origin = headers.get("origin")
        if origin is not None:
            if _origine(origin) not in origini_ammesse():
                await _rispondi(send, 403, "Origine della richiesta non ammessa.")
                return
        elif headers.get("sec-fetch-site") == "cross-site":
            await _rispondi(send, 403, "Origine della richiesta non ammessa.")
            return
        await self.app(scope, receive, send)


class BodySizeLimitMiddleware:
    """413 oltre `MAX_BODY_BYTES`: prima sul `Content-Length` dichiarato, poi
    contando i byte davvero ricevuti (un body chunked non lo dichiara)."""

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        for k, v in scope["headers"]:
            if k.lower() == b"content-length":
                try:
                    if int(v) > self.max_bytes:
                        await _rispondi(send, 413, "Richiesta troppo grande.")
                        return
                except ValueError:
                    await _rispondi(send, 400, "Content-Length non valido.")
                    return

        ricevuti = 0
        risposta_partita = False

        async def receive_limitato() -> Message:
            nonlocal ricevuti
            messaggio = await receive()
            if messaggio["type"] == "http.request":
                ricevuti += len(messaggio.get("body", b""))
                if ricevuti > self.max_bytes:
                    raise _TroppoGrande()
            return messaggio

        async def send_tracciato(messaggio: Message) -> None:
            nonlocal risposta_partita
            if messaggio["type"] == "http.response.start":
                risposta_partita = True
            await send(messaggio)

        try:
            await self.app(scope, receive_limitato, send_tracciato)
        except _TroppoGrande:
            if not risposta_partita:
                await _rispondi(send, 413, "Richiesta troppo grande.")


class _TroppoGrande(Exception):
    pass


class SecurityHeadersMiddleware:
    """Header di difesa su ogni risposta dell'API.

    L'API restituisce JSON, PDF e immagini (avatar): niente HTML da
    proteggere con una CSP articolata, quindi la piu' stretta possibile.
    Niente `Cross-Origin-Resource-Policy`: gli avatar serviti da qui li carica
    il frontend da un'altra origine con un `<img>`.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        base = [
            (b"x-content-type-options", b"nosniff"),
            (b"x-frame-options", b"DENY"),
            (b"referrer-policy", b"no-referrer"),
            (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=()"),
            (b"cross-origin-opener-policy", b"same-origin"),
        ]
        if settings.COOKIE_SECURE:
            base += [
                (b"strict-transport-security", b"max-age=63072000; includeSubDomains"),
                (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
            ]
        self.headers = base

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_con_header(messaggio: Message) -> None:
            if messaggio["type"] == "http.response.start":
                presenti = {k.lower() for k, _ in messaggio.get("headers", [])}
                messaggio.setdefault("headers", [])
                messaggio["headers"] = list(messaggio["headers"]) + [
                    (k, v) for k, v in self.headers if k not in presenti
                ]
            await send(messaggio)

        await self.app(scope, receive, send_con_header)
