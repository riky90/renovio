---
phase: 01-stima-free-end-to-end
plan: 01
subsystem: infra
tags: [fastapi, sqlalchemy, alembic, react, vite, typescript, react-query, sqlite, walking-skeleton]

# Dependency graph
requires: []
provides:
  - Runnable FastAPI backend (uv project) with CORS + slowapi rate limiter wired
  - Runnable React 19 + Vite + TypeScript frontend
  - Full Phase 1 database schema (8 tables) as an applied Alembic migration
  - Working Browser -> API -> DB -> Browser health round-trip (GET /api/v1/health/db)
  - Directory layout backend/app/{models,routers,...}, frontend/src/{api,...}
affects: [01-02, 01-03, 01-04]

# Tech tracking
tech-stack:
  added: [fastapi==0.141.1, uvicorn==0.52.4, sqlalchemy==2.0.52, alembic==1.19.1, "psycopg[binary]==3.3.4", pydantic==2.13.4, pydantic-settings==2.15.0, slowapi==0.1.10, python-slugify==8.0.4, pytest==9.1.1, httpx2==2.12.0, react==19.2.8, vite==8.2.2, typescript==5.9.3, "@tanstack/react-query==5", "tailwindcss==4"]
  patterns:
    - "ORM entities (backend/app/models/) hold the pricing secret (coefficiente_impresa); Pydantic response schemas will be built separately so the secret is never serializable (anti-leak gate, per RESEARCH Pattern 1)"
    - "Numeric/Decimal for every monetary and coefficient column, never float"
    - "pydantic-settings for config (DATABASE_URL, CORS_ORIGINS) from .env, never hardcoded"
    - "Typed fetch wrapper (frontend/src/api/client.ts) as the single point reading VITE_API_BASE"

key-files:
  created:
    - backend/app/main.py
    - backend/app/config.py
    - backend/app/db.py
    - backend/app/models/listino.py
    - backend/app/models/catalogo.py
    - backend/app/routers/health.py
    - backend/alembic/env.py
    - backend/alembic/versions/0001_initial_schema.py
    - backend/tests/test_health.py
    - frontend/src/api/client.ts
    - frontend/src/App.tsx
    - frontend/src/main.tsx
    - README.md
  modified:
    - .gitignore

key-decisions:
  - "Pinned typescript to 5.9.3 (stable) instead of the vite scaffold's default ~6.0.2, per RESEARCH/plan acceptance criteria requiring the 5.9 stable line, not any newer preview-adjacent line"
  - "Added httpx2 as a backend dev dependency (not in the original plan's package list) because starlette 1.6 (pulled in by fastapi 0.141.1) requires it for TestClient"
  - "Used uv add --native-tls (and UV_NATIVE_TLS=1) to work around the corporate proxy's self-signed cert blocking uv's default TLS stack, per RESEARCH's documented SSL note"
  - "SQLite (sqlite:///./dev.db) as local DATABASE_URL default; Postgres is the Railway deploy target per RESEARCH Environment Availability"

requirements-completed: [ENG-02]

# Metrics
duration: 25min
completed: 2026-08-24
---

# Phase 1 Plan 01: Walking Skeleton Summary

**FastAPI + SQLAlchemy 2.0/Alembic backend and React 19/Vite/TS frontend scaffolded, full 8-table Phase 1 schema migrated, and a live GET /api/v1/health/db round-trip (Browser -> FastAPI -> SQLAlchemy -> SQLite -> Browser) proven end-to-end.**

## Performance

- **Duration:** ~25 min (13:27–13:33 CET commit span; scaffold/setup work preceded first commit)
- **Started:** 2026-08-24T13:23:00+02:00 (approx, uv init)
- **Completed:** 2026-08-24T13:32:28+02:00
- **Tasks:** 3/3 completed
- **Files modified:** 48 (36 + 8 + 12, with some overlap across tasks)

## Accomplishments
- Backend (`backend/`) is a `uv` project with the exact RESEARCH-pinned stack (fastapi 0.141.1, sqlalchemy 2.0.52, alembic 1.19.1, psycopg3, pydantic-settings 2.15.0, slowapi, python-slugify, pytest); `uv run python -c "import app.main"` succeeds.
- Frontend (`frontend/`) is a Vite + React 19 + TypeScript 5.9.3 (stable, not the 6.x/7.x preview lines) scaffold with @tanstack/react-query 5 and tailwindcss 4 installed; `npm run build` passes with zero TS errors.
- All 8 Phase 1 tables (listino, categoria, listino_categoria, tipo_ristrutturazione, moltiplicatore, extra, comune_listino, referente) exist as SQLAlchemy 2.0 typed entities and as Alembic migration `0001_initial_schema.py`; `alembic upgrade head` applies cleanly. Zero `Float` columns — every monetary/coefficient column uses `Numeric`.
- `coefficiente_impresa` (the internal margin secret) is mapped only on the `ListinoCategoria` ORM entity; the health endpoint returns nothing from that table's price columns, only a count.
- `GET /api/v1/health/db` runs a real `SELECT count(*) FROM listino` via `SessionLocal` and returns `{"status": "ok", "listini": <int>}`; covered by `backend/tests/test_health.py` (passing).
- `App.tsx` is wrapped in `QueryClientProvider`, fetches `/health/db` on mount via react-query, and renders "Database connesso — N listini" or an error — proving the full Browser → API → DB → Browser loop.

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold backend + frontend + config + dev run** - `e8c40ab` (feat)
2. **Task 2: Full Phase 1 schema — SQLAlchemy 2.0 models + Alembic migration** - `1fbc0f6` (feat)
3. **Task 3: End-to-end health loop (Browser → API → DB → Browser)** - `bbbc6f3` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `backend/app/main.py` - FastAPI app: CORS from CORS_ORIGINS, slowapi Limiter on app.state, /api/v1 router include
- `backend/app/config.py` - pydantic-settings: DATABASE_URL, CORS_ORIGINS from .env
- `backend/app/db.py` - SQLAlchemy 2.0 engine, SessionLocal, declarative Base
- `backend/app/models/listino.py` - Listino, ListinoCategoria (coefficiente_impresa SECRET, Numeric everywhere)
- `backend/app/models/catalogo.py` - Categoria, TipoRistrutturazione, Moltiplicatore, Extra, ComuneListino, Referente
- `backend/alembic/env.py` - wired to Base.metadata and app.config.settings.DATABASE_URL
- `backend/alembic/versions/0001_initial_schema.py` - creates all 8 tables + UNIQUE constraints
- `backend/app/routers/health.py` - GET /health/db, real DB count query
- `backend/tests/test_health.py` - pytest regression for the health endpoint
- `frontend/src/api/client.ts` - typed fetch wrapper on VITE_API_BASE
- `frontend/src/App.tsx` - health-check UI via react-query
- `frontend/src/main.tsx` - QueryClientProvider wrapper
- `README.md` - documents backend/frontend local run commands
- `.gitignore` - allow `.env.example` through the blanket `.env.*` ignore

## Decisions Made
- typescript pinned to 5.9.3 exact (not the scaffold's ~6.0.2 default) to satisfy the plan's explicit "5.9 stable line, not preview" constraint.
- httpx2 added as a backend dev dependency — required transitively by starlette 1.6 for TestClient; not anticipated in the plan's package list but necessary to run the verification command.
- `uv add --native-tls` / `UV_NATIVE_TLS=1` used for every backend install to route around the corporate proxy's self-signed certificate (documented risk in 01-RESEARCH.md).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Root .gitignore blocked `.env.example` files**
- **Found during:** Task 1 (staging files for commit)
- **Issue:** Root `.gitignore` has a blanket `.env.*` rule that also matched `.env.example`, preventing the required example files from being committed (plan acceptance criteria explicitly requires them to exist in the repo).
- **Fix:** Added `!.env.example` negation pattern after `.env.*` in root `.gitignore`.
- **Files modified:** `.gitignore`
- **Verification:** `git add backend/.env.example frontend/.env.example` succeeded without `-f`.
- **Committed in:** e8c40ab (Task 1 commit)

**2. [Rule 3 - Blocking] typescript scaffolded at ~6.0.2 instead of the 5.9 stable line**
- **Found during:** Task 1 (frontend scaffold)
- **Issue:** `npm create vite@latest -- --template react-ts` installed typescript `~6.0.2` by default; the plan/RESEARCH require the "5.9 stable line, not 7.x preview" and the acceptance criteria checks for the 5.9 line specifically.
- **Fix:** `npm install typescript@5.9.3 --save-exact`.
- **Files modified:** `frontend/package.json`, `frontend/package-lock.json`
- **Verification:** `npm run build` (tsc -b && vite build) passes with zero errors on 5.9.3.
- **Committed in:** e8c40ab (Task 1 commit)

**3. [Rule 3 - Blocking] Corporate proxy SSL blocked default `uv add` TLS**
- **Found during:** Task 1 (`uv add` of the pinned backend stack)
- **Issue:** `uv add` failed with `invalid peer certificate: UnknownIssuer` — the corporate proxy's self-signed cert isn't trusted by uv's bundled TLS stack (documented risk in 01-RESEARCH.md's Package Legitimacy Audit note).
- **Fix:** Re-ran with `uv add --native-tls`, which uses the OS certificate store (where the corporate cert is trusted).
- **Files modified:** none (install-time flag only)
- **Verification:** All 9 runtime + pytest dev dependencies installed successfully at the exact pinned versions.
- **Committed in:** e8c40ab (Task 1 commit)

**4. [Rule 3 - Blocking] `TestClient` requires `httpx2`, not in the plan's dependency list**
- **Found during:** Task 3 (verification command for the health endpoint)
- **Issue:** `fastapi.testclient.TestClient` raised `RuntimeError: The starlette.testclient module requires the httpx2 package to be installed` — starlette 1.6.0 (pulled in transitively by fastapi 0.141.1) switched its test client dependency to `httpx2`, which wasn't in RESEARCH's package list (a newer starlette release than RESEARCH anticipated).
- **Fix:** `uv add --native-tls --dev httpx2` (resolved cleanly from PyPI at 2.12.0, confirming it's a real, current package — not a typosquat).
- **Files modified:** `backend/pyproject.toml`, `backend/uv.lock`
- **Verification:** `uv run pytest -q tests/test_health.py` and the plan's inline `TestClient` verify command both pass.
- **Committed in:** bbbc6f3 (Task 3 commit)

**5. [Rule 1 - Bug/cleanup] Removed unused Vite starter assets**
- **Found during:** Task 3 (rewriting App.tsx)
- **Issue:** Replacing the Vite starter page left `hero.png`, `react.svg`, `vite.svg` as dead imports/unreferenced files.
- **Fix:** Deleted `frontend/src/assets/{hero.png,react.svg,vite.svg}` and the now-empty `assets/` directory.
- **Files modified:** deletions only
- **Verification:** `npm run build` succeeds with no missing-import errors.
- **Committed in:** bbbc6f3 (Task 3 commit)

---

**Total deviations:** 5 auto-fixed (4 blocking, 1 bug/cleanup)
**Impact on plan:** All fixes were necessary to satisfy the plan's own acceptance criteria (typescript version, .env.example presence) or to make the verification commands runnable at all (native-tls, httpx2). No scope creep — no functionality was added beyond what the plan specified.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required. Local dev uses SQLite by default (`sqlite:///./dev.db`); Postgres is the documented Railway deploy target for a later phase.

## Next Phase Readiness
- Architecture is fixed: directory layout, config pattern, data layer, and the anti-leak boundary (ORM entity vs. future Pydantic response schemas) are all in place per SKELETON.md.
- Plan 01-02 (seed + calculation engine) can now populate `listino`/`listino_categoria`/etc. from `docs/seed-coefficienti-base.json` and build `EstimationService` on top of this schema without any migration rework.
- `coefficiente_impresa` exists in the DB but has no seed data yet (all 8 tables are empty after migration) — expected, seeding is Plan 01-02's job.
- No blockers.

---
*Phase: 01-stima-free-end-to-end*
*Completed: 2026-08-24*
