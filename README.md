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

### Pagine pubbliche, SEO e guide ai costi

`npm run build` prerenderizza in HTML statico le pagine pubbliche (home, guide ai
costi, domande frequenti) e genera `sitemap.xml`, `robots.txt`, `llms.txt`,
`404.html` e `app.html` (il guscio delle pagine di account e admin, servito dai
rewrite di `vercel.json`). Le pagine indicizzabili sono in
`PAGINE_PUBBLICHE` (`frontend/src/routes.tsx`).

- **Dominio.** Canonical, Open Graph, sitemap e llms.txt usano `VITE_SITE_URL`
  (default `https://stima-lovat.vercel.app`, provvisorio). Al cambio di dominio
  basta impostare la variabile su Vercel e rifare il deploy.
- **Cifre delle guide.** Vengono dal motore di stima: `GET /api/v1/guide/costi`
  (`backend/app/services/guide_costi.py`). Il build usa una copia committata,
  `frontend/src/data/guide-costi.json`, che il browser aggiorna dal vivo. Dopo
  una modifica al listino o ai coefficienti va rigenerata, così anche l'HTML
  statico letto da motori di ricerca e assistenti AI ha i numeri nuovi:

  ```bash
  cd backend
  DATABASE_URL=... PYTHONPATH=. .venv/bin/python scripts/esporta_dati_guide.py
  ```

## Documenti di progetto

Pianificazione GSD in `.planning/`. Brief fondante in `BRIEF-DISCUSSIONE.md`. Regole di dominio non negoziabili in `CLAUDE.md`. Sorgente dati in `docs/computo-base-reggio-emilia.xlsx`.
