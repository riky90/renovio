"""Shared slowapi Limiter instance.

Defined in its own module (not `main.py`) so routers can import and decorate
endpoints with `@limiter.limit(...)` without a circular import on `app.main`.

La chiave e' l'IP reale del client (`app.security.client_ip`), non
`get_remote_address`: dietro Render quello e' il primo valore di
`X-Forwarded-For`, che sceglie il client.
"""

from slowapi import Limiter

from app.security import client_ip

limiter = Limiter(key_func=client_ip)
