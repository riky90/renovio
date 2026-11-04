"""FastAPI application entrypoint: CORS, rate limiting, router include."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.limiter import limiter
from app.security import BodySizeLimitMiddleware, OriginCheckMiddleware, SecurityHeadersMiddleware
from app.routers import (
    admin,
    auth,
    avatars,
    dettaglio_pro,
    domande,
    guide,
    health,
    lead,
    pagamenti,
    stima,
    stime_salvate,
    subscription,
)

# In produzione (COOKIE_SECURE) niente /docs, /redoc, /openapi.json: la
# mappa completa dell'API admin non deve essere pubblica.
_IN_PRODUZIONE = settings.COOKIE_SECURE
app = FastAPI(
    title="ristruttura-stima API",
    docs_url=None if _IN_PRODUZIONE else "/docs",
    redoc_url=None if _IN_PRODUZIONE else "/redoc",
    openapi_url=None if _IN_PRODUZIONE else "/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SessionMiddleware di Starlette: usato SOLO da Authlib per lo scambio
# state/PKCE del flusso Google OAuth (AUTH-02). Segreto DEDICATO
# (OAUTH_SESSION_SECRET), cookie DISTINTO dal cookie applicativo
# `session_id` gestito a mano da AuthService — mai lo stesso secret/nome,
# altrimenti cookie-clobbering silenzioso tra i due meccanismi
# (02-RESEARCH.md Pitfall 1, T-05-02).
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.OAUTH_SESSION_SECRET,
    https_only=settings.COOKIE_SECURE,
    max_age=15 * 60,  # serve solo per il giro di andata e ritorno da Google
)

# Ultimi aggiunti = primi eseguiti. Ordine effettivo di una richiesta:
# header di sicurezza (avvolge tutto, anche i 403/413) -> tetto al body ->
# controllo Origin (CSRF) -> CORS -> sessione OAuth -> app.
app.add_middleware(OriginCheckMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(health.router, prefix="/api/v1")
app.include_router(stima.router, prefix="/api/v1")
app.include_router(domande.router, prefix="/api/v1")
app.include_router(guide.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(avatars.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(stime_salvate.router, prefix="/api/v1")
app.include_router(subscription.router, prefix="/api/v1")
app.include_router(pagamenti.router, prefix="/api/v1")
app.include_router(dettaglio_pro.router, prefix="/api/v1")
app.include_router(lead.router, prefix="/api/v1")
