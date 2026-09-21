"""FastAPI application entrypoint: CORS, rate limiting, router include."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.limiter import limiter
from app.routers import (
    admin,
    auth,
    dettaglio_pro,
    domande,
    health,
    lead,
    stima,
    stime_salvate,
    subscription,
)

app = FastAPI(title="ristruttura-stima API")

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
app.add_middleware(SessionMiddleware, secret_key=settings.OAUTH_SESSION_SECRET)

app.include_router(health.router, prefix="/api/v1")
app.include_router(stima.router, prefix="/api/v1")
app.include_router(domande.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(stime_salvate.router, prefix="/api/v1")
app.include_router(subscription.router, prefix="/api/v1")
app.include_router(dettaglio_pro.router, prefix="/api/v1")
app.include_router(lead.router, prefix="/api/v1")
