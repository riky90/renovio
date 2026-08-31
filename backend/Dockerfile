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

# Applica le migrazioni e avvia uvicorn. Su free tier (istanza singola)
# eseguire le migrazioni al boot e' sicuro.
CMD uv run alembic upgrade head && \
    uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
