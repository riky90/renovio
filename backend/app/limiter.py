"""Shared slowapi Limiter instance.

Defined in its own module (not `main.py`) so routers can import and decorate
endpoints with `@limiter.limit(...)` without a circular import on `app.main`.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
