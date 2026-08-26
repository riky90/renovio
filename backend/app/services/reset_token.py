"""Signed, expiring password-reset tokens (D-04).

Follows 02-RESEARCH.md Code Examples verbatim: `URLSafeTimedSerializer`
signs `{"user_id": ...}` with `settings.SECRET_KEY` (NOT
`OAUTH_SESSION_SECRET`, which is a separate secret dedicated to the
Authlib/Starlette `SessionMiddleware` OAuth state — 02-RESEARCH.md Pitfall
1) and a dedicated salt (`"password-reset"`) so a token from another
context can never be mistaken for a reset token.

`read_reset_token` returns `None` on BOTH expiry (`SignatureExpired`) and
tampering (`BadSignature`) — the caller doesn't need to distinguish; either
way the router responds with the same generic 400 (T-06-02/T-06-04).

The serializer is built lazily on every call (not module-level) so tests
that need to exercise a fresh `settings.SECRET_KEY` value are not bound to
whatever value happened to be set at import time.
"""

from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

RESET_TOKEN_SALT = "password-reset"
RESET_TOKEN_MAX_AGE_SECONDS = 3600


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt=RESET_TOKEN_SALT)


def make_reset_token(user_id: int) -> str:
    return _serializer().dumps({"user_id": user_id})


def read_reset_token(token: str, max_age_seconds: int = RESET_TOKEN_MAX_AGE_SECONDS) -> int | None:
    try:
        data = _serializer().loads(token, max_age=max_age_seconds)
    except (SignatureExpired, BadSignature):
        return None
    return data.get("user_id")
