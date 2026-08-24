# ristruttura-stima

App web che trasforma il computo metrico estimativo Excel usato oggi per i preventivi di ristrutturazione in uno strumento self-service: da città + mq + tipo di ristrutturazione a una stima dei costi a range.

## Struttura

- `backend/` — FastAPI + SQLAlchemy 2.0 + Alembic (Python 3.13, gestito con `uv`)
- `frontend/` — React 19 + Vite + TypeScript (gestito con `npm`)

## Run locale

### Backend

```bash
cd backend
cp .env.example .env   # se non già presente
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Il backend serve su `http://localhost:8000`, con l'API sotto `/api/v1`.

### Frontend

```bash
cd frontend
cp .env.example .env.development   # se non già presente
npm install
npm run dev
```

Il frontend serve su `http://localhost:5173` e chiama il backend tramite `VITE_API_BASE`.

## Documenti di progetto

Pianificazione GSD in `.planning/`. Brief fondante in `BRIEF-DISCUSSIONE.md`. Regole di dominio non negoziabili in `CLAUDE.md`. Sorgente dati in `docs/computo-base-reggio-emilia.xlsx`.
