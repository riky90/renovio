"""Istanza Authlib OAuth registrata per Google (AUTH-02).

Modulo dedicato per evitare import circolari tra `main.py` e
`routers/auth.py` (stesso pattern di `app/limiter.py`). Lo scambio
state/PKCE/JWKS e la verifica dell'id_token sono interamente delegati
ad Authlib (02-RESEARCH.md Pattern 2, Don't Hand-Roll) — non reinventati.
"""

from __future__ import annotations

from authlib.integrations.starlette_client import OAuth

from app.config import settings

oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    client_kwargs={"scope": "openid email profile"},
)
