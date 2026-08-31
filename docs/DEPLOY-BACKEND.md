# Deploy backend — Render vs Vercel

Guida passo-passo al deploy del backend FastAPI di `ristruttura-stima`.
Il frontend è già su **Vercel**; qui trattiamo il backend.

---

## TL;DR — quale scegliere

| Vincolo del backend | Render (Web Service) | Vercel (Serverless) |
|---|---|---|
| **WeasyPrint** (PDF, richiede GTK/Pango/Cairo nativi) | ✅ con Docker | ❌ impossibile installare le lib native |
| Processo persistente (uvicorn long-running) | ✅ | ❌ funzioni stateless a invocazione |
| SessionMiddleware / rate limit in-memory | ✅ | ⚠️ resettati a ogni cold start |
| Postgres gestito incluso | ✅ | ✅ (Neon/Vercel Postgres) |
| Costo | Free tier (dorme dopo 15′) o ~7$/mese | Free tier |

**Verdetto: usa Render.** Il PDF con WeasyPrint da solo esclude Vercel per questo
backend. Vercel è ottimo per il frontend (già fatto), ma per un'app FastAPI con
generazione PDF nativa e sessioni server-side è la scelta sbagliata. Il percorso
Vercel è documentato in fondo **solo** per completezza, con i suoi blocchi.

---

## Parte 0 — Preparazione comune (fai questo PRIMA, per entrambi)

Queste modifiche servono a prescindere dalla piattaforma. Sono 3 punti.

### 0.1 — Database: da SQLite a Postgres gestito

In locale usi `dev.db` (SQLite). In produzione il filesystem è effimero: SQLite
verrebbe azzerato a ogni deploy/riavvio. Il backend ha già `psycopg[binary]` tra
le dipendenze → è pensato per Postgres. Userai un Postgres gestito (lo crei nella
Parte 1/2).

⚠️ **Gotcha psycopg v3**: il progetto usa `psycopg` (v3), NON `psycopg2`.
L'URL che la piattaforma ti dà è tipo `postgresql://user:pass@host:5432/db`.
SQLAlchemy con quello schema cerca `psycopg2` e fallisce. Devi forzare lo schema
psycopg3:

```
postgresql+psycopg://user:pass@host:5432/db
```

Cioè: prendi l'URL fornito dalla piattaforma e sostituisci il prefisso
`postgresql://` con `postgresql+psycopg://` quando lo metti nella variabile
`DATABASE_URL`. (In alternativa aggiungi una normalizzazione in `app/db.py`; vedi
0.4.)

### 0.2 — Cookie di sessione cross-site (fondamentale per l'auth)

Frontend su `renovio.vercel.app` e backend su `xxx.onrender.com` sono **siti
diversi**. Il cookie di sessione è impostato con `samesite="lax"`
(`app/services/auth_service.py:54`): con `lax` il browser **non invia** il cookie
sulle richieste `fetch` cross-site → dopo il login le chiamate autenticate
falliscono con 401.

Due modi per risolvere (scegline uno):

**Opzione A — cookie cross-site (rapido).** In `app/services/auth_service.py`
cambia il cookie di sessione in `samesite="none"` (richiede `secure=True`, cioè
`COOKIE_SECURE=True` in prod, già previsto). Con `none`+`secure` il cookie viaggia
cross-site su HTTPS.

```python
# app/services/auth_service.py, dentro response.set_cookie(...)
samesite="none",          # era "lax"
secure=settings.COOKIE_SECURE,   # deve essere True in prod
```

**Opzione B — stesso dominio radice (più pulito, consigliato a regime).**
Assegna domini custom sullo stesso eTLD+1: `app.renovio.it` (frontend Vercel) e
`api.renovio.it` (backend Render). Essendo *same-site*, `samesite="lax"` continua
a funzionare e non tocchi il codice. Richiede di possedere il dominio e
configurare i DNS.

Per andare in prod subito parti con **A**; passa a **B** quando colleghi il
dominio definitivo.

> Nota: il cookie separato del `SessionMiddleware` di Starlette (usato SOLO per lo
> scambio state/PKCE di Google OAuth) funziona con `lax` perché il ritorno da
> Google è una navigazione top-level verso il backend, non una fetch cross-site.
> Quello NON va toccato.

### 0.3 — Variabili d'ambiente di produzione

Rispetto a `.env.example`, in prod dovrai valorizzare (le imposterai nella
dashboard della piattaforma, MAI committarle):

| Variabile | Valore in prod |
|---|---|
| `DATABASE_URL` | URL Postgres **con** `postgresql+psycopg://` (vedi 0.1) |
| `CORS_ORIGINS` | URL esatto del frontend, es. `https://renovio.vercel.app` |
| `FRONTEND_URL` | come sopra (usato nei link email e redirect post-OAuth) |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `OAUTH_SESSION_SECRET` | come sopra, **diverso** da SECRET_KEY |
| `COOKIE_SECURE` | `True` |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | dalle credenziali OAuth Google |
| `SMTP_HOST/PORT/USER/PASSWORD/FROM` | provider email transazionale |
| `ADMIN_EMAIL` | la tua email admin |

⚠️ **Google OAuth**: in Google Cloud Console → Credenziali → il tuo Client OAuth,
aggiungi agli **Authorized redirect URIs** l'URL del callback sul dominio di prod
del backend (es. `https://xxx.onrender.com/api/v1/auth/google/callback` — verifica
il path esatto in `app/routers/auth.py`). Senza questo, il login Google dà
`redirect_uri_mismatch`.

### 0.4 — Migrazioni Alembic

Lo schema va creato sul Postgres di prod con:

```
alembic upgrade head
```

`alembic/env.py` legge già `DATABASE_URL` da settings, quindi punterà al Postgres
di prod se la variabile è impostata. Lo lancerai come *release/pre-deploy command*
(vedi Parte 1). Il primo admin lo promuovi con `python -m scripts.seed` se lo
script lo prevede — controlla `scripts/seed.py`.

---

## Parte 1 — Deploy su RENDER (percorso consigliato)

Render fa girare un container persistente. Per avere WeasyPrint funzionante il
modo affidabile è un **Dockerfile** (controllo totale sulle lib native). Sotto
trovi sia il path Docker (consigliato) sia il path nativo con i suoi limiti.

### 1.1 — Crea il Postgres gestito

1. Vai su https://dashboard.render.com → **New** → **Postgres**.
2. Nome (`renovio-db`), regione (Frankfurt per l'Italia), piano Free.
3. Creato il DB, copia la **Internal Database URL** (per servizi nello stesso
   account Render è più veloce/gratis del traffico esterno).
4. Ricorda: quando la userai come `DATABASE_URL`, cambia `postgresql://` →
   `postgresql+psycopg://` (Parte 0.1).

### 1.2 — Aggiungi un Dockerfile al backend

Crea `backend/Dockerfile`:

```dockerfile
FROM python:3.13-slim

# Librerie native richieste da WeasyPrint (Pango/Cairo/GDK-Pixbuf/HarfBuzz)
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
      libgdk-pixbuf-2.0-0 libffi-dev libharfbuzz0b \
      fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

# uv per installare dalle lock (pyproject.toml + uv.lock)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Render inietta $PORT
ENV PORT=8000
CMD uv run alembic upgrade head && \
    uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

> Il `CMD` lancia le migrazioni e poi uvicorn. Se preferisci separare le
> migrazioni dal boot (consigliato per evitare che ogni istanza le rilanci),
> togli `alembic upgrade head` dal CMD e mettilo come **Pre-Deploy Command** nel
> passo 1.4.

Verifica che `.dockerignore` (crealo se manca) escluda roba inutile:

```
.venv/
dev.db
__pycache__/
*.pyc
.env
.pytest_cache/
```

### 1.3 — Committa e pusha

```bash
cd C:/Users/RINALDIR/ristruttura-stima
git add backend/Dockerfile backend/.dockerignore
git commit -m "chore(backend): Dockerfile per deploy Render con WeasyPrint"
git push
```

### 1.4 — Crea il Web Service su Render

1. Dashboard Render → **New** → **Web Service** → collega il repo GitHub.
2. **Root Directory**: `backend` (così Render trova il Dockerfile lì).
3. **Runtime**: Docker (rilevato in automatico dal Dockerfile).
4. **Region**: la stessa del DB (Frankfurt).
5. **Instance type**: Free per iniziare (dorme dopo 15′ di inattività, primo hit
   lento ~30s) oppure Starter ~7$/mese per tenerlo sveglio.
6. **Environment**: incolla tutte le variabili della tabella 0.3.
   - `DATABASE_URL` = Internal URL del DB con `postgresql+psycopg://`.
7. (Se hai tolto la migrazione dal CMD) **Pre-Deploy Command**:
   `uv run alembic upgrade head`.
8. **Create Web Service**. Render builda l'immagine e avvia.

### 1.5 — Verifica

1. Guarda i **Logs**: devi vedere `Uvicorn running on ...` senza traceback.
2. Apri `https://<tuo-servizio>.onrender.com/api/v1/health` (verifica il path
   reale nel router `health`). Deve rispondere OK.
3. Testa la generazione PDF da un endpoint reale: se WeasyPrint non trova una lib,
   vedrai un errore tipo `cannot load library 'libpango...'` → aggiungi il
   pacchetto mancante al Dockerfile (passo 1.2) e ri-deploya.
4. Testa il login Google end-to-end dal frontend Vercel (verifica redirect URI,
   CORS, e che il cookie di sessione arrivi — è il punto 0.2).

### 1.6 — Collega il frontend

Nel progetto frontend su Vercel, imposta la variabile che punta all'API (es.
`VITE_API_URL=https://<tuo-servizio>.onrender.com`) e ri-deploya il frontend.
Assicurati che `CORS_ORIGINS` sul backend contenga esattamente l'origin del
frontend.

### (Alternativa) Render senza Docker — perché la sconsiglio

Render ha un runtime Python nativo (rileva `uv.lock`), con:
- **Build Command**: `uv sync --frozen --no-dev`
- **Start Command**: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`

MA il runtime nativo **non ti fa installare pacchetti apt**, quindi WeasyPrint non
trova Pango/Cairo e il PDF crasha a runtime. Andrebbe bene solo se rinunci al PDF.
Per questo il Dockerfile è il path corretto qui.

---

## Parte 2 — Deploy su VERCEL (documentato, ma con blocchi)

Vercel esegue funzioni serverless Python (basate su AWS Lambda). Va tenuto conto
di questi blocchi **specifici di questo backend**:

- ❌ **WeasyPrint non funziona**: non puoi installare le lib native GTK/Pango/
  Cairo in una function. Gli endpoint PDF crasheranno. Le uniche vie sono
  rimuovere la feature PDF o riscriverla con un motore PDF puro-Python o un
  servizio esterno.
- ⚠️ **Stateless**: `SessionMiddleware` e il rate limiter in-memory (slowapi) si
  resettano tra invocazioni/cold start. L'auth via cookie firmato regge, ma
  qualsiasi stato in RAM no.
- ⚠️ **uv non è il flusso nativo**: la Python runtime di Vercel si aspetta un
  `requirements.txt`.

Se accetti questi limiti (es. deployi il backend *senza* PDF solo per testare le
API), ecco i passi.

### 2.1 — Genera requirements.txt

```bash
cd C:/Users/RINALDIR/ristruttura-stima/backend
uv export --no-dev --no-hashes -o requirements.txt
```

Poi **rimuovi la riga `weasyprint`** dal `requirements.txt` (altrimenti il build
prova a compilarla e fallisce) — e sappi che gli endpoint PDF resteranno rotti.

### 2.2 — Entrypoint per Vercel

Vercel monta come ASGI il modulo esposto in `api/`. Crea `backend/api/index.py`:

```python
from app.main import app  # noqa: F401
```

E `backend/vercel.json`:

```json
{
  "builds": [{ "src": "api/index.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "api/index.py" }]
}
```

### 2.3 — Postgres

Crea un Postgres gestito (Vercel Storage → Postgres, che è Neon). Usa la connection
string con `postgresql+psycopg://` (Parte 0.1). Su serverless valuta la variante
**pooled** della connessione (Neon fornisce un endpoint `-pooler`) per non
esaurire le connessioni.

### 2.4 — Deploy

1. Su Vercel: **Add New → Project**, stesso repo, **Root Directory** = `backend`.
2. Imposta tutte le env var della tabella 0.3 (con `DATABASE_URL` pooled+psycopg).
3. Le **migrazioni** non hanno un hook di deploy comodo come Render: lanciale a
   mano una tantum dal tuo PC puntando `DATABASE_URL` al Postgres di prod →
   `uv run alembic upgrade head`.
4. Deploy. Testa `/api/v1/health`. **Non** testare il PDF (è rotto per design su
   Vercel).

### 2.5 — Perché comunque conviene Render

Su Vercel perdi il PDF e combatti con lo stateless. Su Render hai un container
normale dove tutto il backend gira come in locale. A parità di sforzo, Render ti
dà l'app completa; Vercel te ne dà una mutilata. Tieni il frontend su Vercel, il
backend su Render.

---

## Checklist finale (Render)

- [ ] `backend/Dockerfile` + `.dockerignore` committati e pushati
- [ ] Postgres creato; `DATABASE_URL` con `postgresql+psycopg://`
- [ ] `samesite="none"` + `COOKIE_SECURE=True` (o domini same-site)
- [ ] Tutte le env var 0.3 impostate su Render
- [ ] `alembic upgrade head` gira (CMD o Pre-Deploy)
- [ ] Redirect URI di prod aggiunto in Google Cloud Console
- [ ] `CORS_ORIGINS` = origin esatto del frontend Vercel
- [ ] `/health` risponde; PDF generato senza errori di libreria
- [ ] Login Google end-to-end funziona dal frontend
- [ ] Frontend Vercel punta a `VITE_API_URL` del backend Render
