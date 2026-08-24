# Walking Skeleton — ristruttura-stima

**Phase:** 1
**Generated:** 2026-08-24

## Capability Proven End-to-End

An anonymous visitor loads the React page in the browser, which calls `GET /api/v1/health/db` on the FastAPI backend; the endpoint executes a real query against the seeded database and returns a row count, and the page renders "Database connesso — N listini" — exercising Browser → FastAPI → SQLAlchemy → PostgreSQL/SQLite → Browser.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI 0.141 + Uvicorn 0.52 (Python 3.13) | Typed API, Pydantic-native validation; matches user's other projects; the calc secret stays server-side (RESEARCH Responsibility Map). |
| Data layer | SQLAlchemy 2.0 (`Mapped[]`/`mapped_column`) + Alembic 1.19; `Numeric`→`Decimal` for currency | ENG-02 (prices in DB); exact monetary precision (Pitfall 1); Alembic versions the schema that Phases 3/4 extend. |
| Database | PostgreSQL 16 on Railway (target); SQLite for local dev via the same SQLAlchemy dialect | Postgres addon native on Railway; local Postgres absent → SQLite fallback documented in RESEARCH Environment Availability. Run tests on Postgres before deploy. |
| DB driver | psycopg 3 (`psycopg[binary]`) | Modern v3 driver recommended for SQLAlchemy 2.0. |
| Config | pydantic-settings (`DATABASE_URL`, `CORS_ORIGINS` from env; `.env` git-ignored) | 12-factor; secrets never in git (V6/Info Disclosure). |
| Frontend framework | React 19 + Vite 8 + TypeScript 5.9 (stable, NOT npm 7.x preview) | User's toolchain; typed API contract prevents client/server drift. |
| Data fetching | @tanstack/react-query 5 | Idiomatic loading/error/cache around `POST /stima`. |
| Styling / components | Tailwind CSS 4 + shadcn/ui ("New York" style, base color Slate, CSS variables) | Per UI-SPEC; trustworthy calm aesthetic, mobile-first. |
| API surface | Versioned prefix `/api/v1`; anti-scraping rate limit (slowapi); CORS whitelist | Public anonymous endpoint; V13 API controls. |
| City autocomplete | Static ISTAT `comuni.json` bundled client-side (no external API) | Zero runtime deps, no privacy leak; city selects listino only (D-06). |
| Directory layout | `backend/app/{models,schemas,services,routers,data}` + `backend/{alembic,scripts,tests}`; `frontend/src/{api,components,pages,data}` | Per RESEARCH "Recommended Project Structure"; keeps ORM entities (secret) separate from Pydantic response schemas (anti-leak gate). |

## Stack Touched in Phase 1

- [x] Project scaffold (FastAPI app + Vite/React/TS, ruff/pytest, dev run command) — Plan 01
- [x] Routing — `GET /api/v1/health/db` (skeleton) then `POST /api/v1/stima` (Plan 03)
- [x] Database — real read (health count) in Plan 01; seed write in Plan 02; estimate reads in Plan 02/03
- [x] UI — health page (Plan 01) then interactive estimate form + result screen (Plan 04)
- [x] Deployment — documented local full-stack run command in SKELETON + backend README (Railway deploy is a later concern)

## Out of Scope (Deferred to Later Slices)

- Authentication, sessions, user accounts, admin role → Phase 2
- Saving estimates, branded PDF export → Phase 2
- Pro sub-category detail (a.1/a.2 voci), paywall, parametric quantity-per-m² engine → Phase 3
- Lead submission / professional contact, email delivery, admin CRUD (listini, coefficienti, città, referenti, testi) → Phase 4
- Zone-based price multipliers, multi-partner operations → post-v1
- The `referente` table exists in the schema from day 1 (multi-referente domain rule) but has NO endpoint or UI in Phase 1

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- Phase 2: Account (email + Google auth), saved estimates, branded Free PDF
- Phase 3: Pro sub-category breakdown behind paywall + detailed PDF
- Phase 4: Lead capture + email + admin dashboard/CRUD for listini, coefficienti, città, referenti, testi
