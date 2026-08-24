---
phase: 01-stima-free-end-to-end
reviewed: 2026-08-24T00:00:00Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - backend/app/config.py
  - backend/app/db.py
  - backend/app/limiter.py
  - backend/app/main.py
  - backend/app/models/catalogo.py
  - backend/app/models/listino.py
  - backend/app/routers/health.py
  - backend/app/routers/stima.py
  - backend/app/schemas/stima.py
  - backend/app/services/city_resolver.py
  - backend/app/services/estimation.py
  - backend/alembic/env.py
  - backend/alembic/versions/0001_initial_schema.py
  - backend/scripts/seed.py
  - backend/tests/test_estimation.py
  - backend/tests/test_health.py
  - backend/tests/test_no_leak.py
  - backend/tests/test_seed.py
  - backend/tests/test_stima_api.py
  - frontend/src/App.tsx
  - frontend/src/api/client.ts
  - frontend/src/api/stima.ts
  - frontend/src/components/CategoryCard.tsx
  - frontend/src/components/CityAutocomplete.tsx
  - frontend/src/components/EstimateForm.tsx
  - frontend/src/components/FallbackDisclaimer.tsx
  - frontend/src/components/SoftWallCta.tsx
  - frontend/src/components/TotalCard.tsx
  - frontend/src/lib/currency.ts
  - frontend/src/pages/EstimatePage.tsx
findings:
  critical: 0
  warning: 6
  info: 3
  total: 9
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-08-24
**Depth:** standard
**Files Reviewed:** 27 (+3 supporting files read for context)
**Status:** issues_found

## Summary

Reviewed the full backend estimation stack (models, services, router, schemas, alembic migration, seed script) and the frontend estimate flow. The core domain invariant — the impresa secret (`coefficiente_impresa`, `base_eur_mq`, `moltiplicatore`, `prezzo_impresa`) never reaching the response — is correctly enforced: `EstimationService.compute` only ever builds `CategoriaEstimata`/`ExtraEstimato`/`StimaResult` dataclasses with an explicit closed field set, and `routers/stima.py` hand-builds `StimaResponse` field-by-field rather than `model_validate`-ing an ORM entity. All category/extra monetary math traced through `estimation.py` and `routers/stima.py` uses `Decimal` exclusively — no floats found in the calculation path. `test_no_leak.py` backs this up with substring/key assertions on the live response.

No BLOCKER-level issues were found. The issues below are robustness gaps (SQLite FK enforcement, unguarded `.one()`/`.one_or_none()` lookups that can 500 on data-integrity edge cases not currently reachable via the public API), a UI data-accuracy mismatch in how extras are displayed, and minor code-quality items (dead export, duplicated fetch-base logic).

## Warnings

### WR-01: SQLite foreign keys are not enforced, `resolve_listino` can return `None` for the listino

**File:** `backend/app/db.py:12-14`, `backend/app/services/city_resolver.py:17-31`
**Issue:** `db.py` sets `check_same_thread: False` for SQLite but never enables `PRAGMA foreign_keys = ON` (no `event.listens_for(engine, "connect", ...)` handler). SQLite does not enforce `FOREIGN KEY` constraints by default, so nothing actually prevents a `comune_listino` row from referencing a deleted/nonexistent `listino.id`. In that case `resolve_listino` does:
```python
row = session.query(ComuneListino).filter_by(comune_slug=slug).one_or_none()
if row is not None:
    listino = session.get(Listino, row.listino_id)
    return listino, False
```
`session.get` returns `None` for an orphaned FK, and the function's declared return type `tuple[Listino, bool]` is violated — `crea_stima` then calls `EstimationService.compute(session, listino, ...)` with `listino=None`, which crashes with `AttributeError: 'NoneType' object has no attribute 'id'` (uncaught 500) instead of falling back to the default listino as the docstring promises.
**Fix:** Enable FK enforcement for SQLite connections, and/or guard the `None` case explicitly:
```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
```
and in `resolve_listino`, treat `listino is None` the same as "no dedicated listino found" (fall back to default) rather than trusting the FK blindly.

### WR-02: No DB constraint preventing multiple `Listino.is_default = True` rows

**File:** `backend/app/models/listino.py:22`, `backend/app/services/city_resolver.py:30`
**Issue:** `resolve_listino`'s fallback path does `session.query(Listino).filter_by(is_default=True).one()`. There is no unique/partial-unique constraint on `is_default`, so if more than one listino is ever marked default (future admin tooling, a bad migration, a re-run of a modified seed script), `.one()` raises `MultipleResultsFound` and every fallback request 500s.
**Fix:** Add a partial unique index (e.g. `Index("uq_listino_default", "is_default", unique=True, sqlite_where=text("is_default = 1"))` or an application-level invariant check in `seed.py`), and/or use `.first()` with an explicit ordering plus a startup sanity check instead of a hard `.one()`.

### WR-03: `EstimationService.compute` and `resolve_listino`'s default lookup use unguarded `.one()` for per-listino category/multiplier rows

**File:** `backend/app/services/estimation.py:74-83`
**Issue:** For every category, `compute()` does `ListinoCategoria... .one()` and `Moltiplicatore... .one()`. If a future listino is added without a complete set of 4 `listino_categoria` rows (nothing enforces completeness at insert time), any request against that listino/città raises `NoResultFound` → unhandled 500 rather than a clean error response. Same risk applies to `TipoRistrutturazione... .one()` at line 64 if the `tipo` seed row is ever missing.
**Fix:** Either validate listino completeness at seed/admin-write time (a DB constraint or an application-level check), or wrap the lookups and raise a structured `HTTPException(500, ...)`/`404` with a safe message instead of letting the ORM exception surface as a bare 500.

### WR-04: `allow_credentials=True` combined with `allow_methods=["*"]`/`allow_headers=["*"]` is broader than the app needs

**File:** `backend/app/main.py:17-23`
**Issue:** The API is a stateless public JSON endpoint — the frontend fetch calls (`frontend/src/api/client.ts`, `frontend/src/api/stima.ts`) never send `credentials: "include"` or cookies, and there's no auth/session mechanism in Phase 1. Enabling `allow_credentials=True` widens the CORS attack surface for no functional benefit (it also forces browsers to require an explicit, non-wildcard origin list, which the code does provide, but the credential flag itself is unused and should be paired with the endpoints that actually need it, once auth exists).
**Fix:** Set `allow_credentials=False` until a credentialed flow (e.g. sessions/auth) is actually introduced; narrow `allow_methods`/`allow_headers` to what's used (`GET`, `POST`, `Content-Type`).

### WR-05: Extra line items shown in the UI display the net (IVA-excluded) amount while everything else on screen is IVA-inclusive

**File:** `frontend/src/pages/EstimatePage.tsx:98-108`, `backend/app/schemas/stima.py:48-54`
**Issue:** `ExtraOut.importo` is the pre-IVA net amount (`ExtraOut(..., importo=ex.importo, iva_pct=ex.iva_pct)` in `routers/stima.py:80-83`), but `EstimationService`/`TotalCard` compute and display the grand total using the IVA-inclusive gross for extras (`extra_imponibile_sum + extra_iva_sum`). The per-extra rows in `EstimatePage` render `formatEur(extra.importo)` — the net figure — right next to category cards that show IVA-inclusive ranges (`CategoryCard` renders `totale_min/max`), and next to a `TotalCard` labelled "Totale IVA inclusa" whose figure includes IVA on the extras. A user manually summing the visible category totals + visible extra rows will not match the displayed grand total (off by the extras' IVA, ~22% or ~10% depending on `iva_pct`), which reads as a bug/miscalculation from the user's perspective even though the underlying total is correct.
**Fix:** Either display the gross (IVA-inclusive) amount for each extra (`importo * (1 + iva_pct)`, already computed server-side as `ExtraEstimato.totale` but not exposed on `ExtraOut`) or label the row explicitly as "netto, IVA esclusa" so the numbers visibly reconcile.

### WR-06: `apiGet` in `client.ts` is dead code; `postStima` duplicates its base-URL/error-handling logic instead of reusing it

**File:** `frontend/src/api/client.ts:21-33`, `frontend/src/api/stima.ts:139-157`
**Issue:** `apiGet<T>` is exported but never imported/called anywhere in the codebase (only referenced in a comment in `stima.ts`). Meanwhile `postStima` re-implements the same `VITE_API_BASE` guard, `fetch`, and `ApiError` throw logic inline instead of a shared generic `apiFetch`/`apiPost` helper, so any future change to base-URL handling or error formatting has to be kept in sync in two places.
**Fix:** Either remove `apiGet` if truly unused, or generalize `client.ts` into a shared `apiFetch(path, init)` used by both GET and POST call sites.

## Info

### IN-01: `resolve_listino` return type annotation is a lie under the WR-01 failure mode

**File:** `backend/app/services/city_resolver.py:17`
**Issue:** Declared as `-> tuple[Listino, bool]`, but as noted in WR-01 the first element can be `None` at runtime given an orphaned FK. Type-checkers (mypy/pyright) would not catch the downstream `None.id` access because the annotation asserts non-null.
**Fix:** Once WR-01 is fixed with an explicit `None` fallback, update the annotation accordingly (or keep it accurate to the guaranteed-non-null contract after the fix).

### IN-02: Health endpoint has no rate limiting

**File:** `backend/app/routers/health.py:13-17`
**Issue:** `/api/v1/health/db` runs a live `COUNT(*)` query on every call and is unauthenticated/unlimited, unlike `POST /stima` which is capped at `20/minute` via `@limiter.limit`. The query is cheap today, but it's the only unrated endpoint in the app and could be used as a trivial DB-hammering vector if traffic grows.
**Fix:** Add a light rate limit (e.g. `@limiter.limit("60/minute")`) for consistency, low priority.

### IN-03: `Limiter(key_func=get_remote_address)` is only effective without a reverse proxy in front of it

**File:** `backend/app/limiter.py:10`
**Issue:** `get_remote_address` uses the direct TCP peer address. Once this API is deployed behind a reverse proxy/load balancer (Railway, Render, nginx, etc. — a near-certainty given the project's target deployment), every request will appear to originate from the proxy's IP, making the `20/minute` rate limit on `POST /stima` apply globally across all users combined rather than per-client, either blocking all users after one heavy user or (depending on proxy config) becoming trivially bypassable.
**Fix:** Configure slowapi's `key_func` to read `X-Forwarded-For` (with awareness of trusted-proxy count) once a deployment target is chosen; not urgent for local/dev use in Phase 1.

---

_Reviewed: 2026-08-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
