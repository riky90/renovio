FROM python:3.13-slim

# Librerie native richieste da WeasyPrint (Pango/Cairo/GDK-Pixbuf/HarfBuzz)
# per la generazione dei PDF del preventivo.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
      libgdk-pixbuf-2.0-0 libffi-dev libharfbuzz0b \
      fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

# uv per installare dalle lock (pyproject.toml + uv.lock)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Prima le sole lock per sfruttare la cache dei layer
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Poi il resto del sorgente (app/, alembic/, scripts/, templates...)
COPY . .

# Render inietta $PORT a runtime; default 8000 in locale.
ENV PORT=8000

# Applica migrazioni, semina il listino (idempotente: upsert per chiave
# naturale, sicuro a ogni boot) e avvia uvicorn. Su free tier (istanza
# singola) eseguire questi step al boot e' sicuro.
# --proxy-headers + --forwarded-allow-ips=* : dietro il proxy di Render fa sì
# che uvicorn onori X-Forwarded-Proto (https), così request.url_for() genera
# redirect https corretti per il callback Google OAuth (evita redirect_uri
# mismatch). Il container riceve traffico solo tramite il proxy di Render.
CMD uv run alembic upgrade head && \
    uv run python scripts/seed.py && \
    uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT \
      --proxy-headers --forwarded-allow-ips="*"
