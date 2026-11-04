FROM python:3.13-slim

# Librerie native richieste da WeasyPrint (Pango/Cairo/GDK-Pixbuf/HarfBuzz)
# per la generazione dei PDF del preventivo.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
      libgdk-pixbuf-2.0-0 libffi-dev libharfbuzz0b \
      fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

# uv per installare dalle lock (pyproject.toml + uv.lock). Versione FISSA:
# `latest` cambierebbe il build sotto i piedi a ogni rilascio (riproducibilita'
# e supply chain). Aggiornarla di proposito, insieme a uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

WORKDIR /app

# Prima le sole lock per sfruttare la cache dei layer
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Poi il resto del sorgente (app/, alembic/, scripts/, templates...)
COPY . .

# Il processo NON gira come root: se un giorno una libreria (Pillow,
# WeasyPrint, openpyxl) avesse una falla sfruttabile da un file caricato,
# l'attaccante si ritroverebbe un utente senza privilegi nel container.
# HOME scrivibile serve a fontconfig (WeasyPrint) per la sua cache.
RUN useradd --system --create-home --home-dir /home/app --uid 10001 app \
 && chown -R app:app /app
USER app
ENV PATH="/app/.venv/bin:$PATH"

# Render inietta $PORT a runtime; default 8000 in locale.
ENV PORT=8000

# Applica migrazioni, semina il listino (idempotente: upsert per chiave
# naturale, sicuro a ogni boot) e avvia uvicorn. Su free tier (istanza
# singola) eseguire questi step al boot e' sicuro. I comandi partono
# direttamente dal virtualenv: `uv run` a runtime proverebbe a
# risincronizzare l'ambiente, cosa che un utente non root non deve fare.
#
# --proxy-headers + --forwarded-allow-ips=* : dietro il proxy di Render fa sì
# che uvicorn onori X-Forwarded-Proto (https), così request.url_for() genera
# redirect https corretti per il callback Google OAuth (evita redirect_uri
# mismatch). L'IP del client per i rate limit NON viene da qui (il primo
# valore di X-Forwarded-For lo sceglie il client): vedi app/security.py.
CMD alembic upgrade head && \
    python scripts/seed.py && \
    uvicorn app.main:app --host 0.0.0.0 --port $PORT \
      --proxy-headers --forwarded-allow-ips="*" --no-server-header
