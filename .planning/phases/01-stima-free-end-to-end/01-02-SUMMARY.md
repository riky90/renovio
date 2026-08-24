---
phase: 01-stima-free-end-to-end
plan: 02
subsystem: backend
tags: [sqlalchemy, decimal, tdd, estimation-engine, seed]

# Dependency graph
requires: [01-01]
provides:
  - Idempotent seed loading the Reggio Emilia listino (4 categorie, 3 tipi, 12 moltiplicatori, 2 extra, 2 comune_listino aliases)
  - EstimationService.compute(session, listino, mq, tipo) -> StimaResult (server-side, Decimal-only)
  - resolve_listino(session, citta) -> (Listino, fallback_bool) with RE default fallback
affects: [01-03, 01-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Idempotent upsert seed: query-by-natural-key then insert-or-update, never blind insert"
    - "EstimationService returns hand-built frozen dataclasses (CategoriaEstimata/ExtraEstimato/StimaResult) with a closed field set — coefficiente_impresa and base_eur_mq are read from ORM entities internally but never placed on the result (anti-leak boundary, T-02-01)"
    - "Decimal end-to-end; quantize(ROUND_HALF_UP) only on output fields, never mid-calculation"
    - "Range applied only to the 4 category subtotals; extras are fixed gross values, summed in afterward"

key-files:
  created:
    - backend/scripts/seed.py
    - backend/app/services/estimation.py
    - backend/app/services/city_resolver.py
    - backend/tests/test_seed.py
    - backend/tests/test_estimation.py
    - backend/scripts/__init__.py
    - backend/app/services/__init__.py
  modified: []

key-decisions:
  - "comune_listino seeded with 2 rows for RE (\"Reggio Emilia\", \"Reggio nell'Emilia\") rather than a single row, so both aliases resolve to RE with fallback=False as required by the city-resolver behavior spec (\"reggio emilia\" case-insensitive matches the first row via slugify; \"Reggio nell'Emilia\" is a genuinely different slug and needs its own row)"
  - "scripts/seed.py includes a small sys.path bootstrap so it runs both as `python scripts/seed.py` (plan's verification command) and as `python -m scripts.seed`, since backend/ is only auto-added to sys.path in the pytest package-discovery case"

requirements-completed: [ENG-01, ENG-03, EST-03, EST-04, EST-06]

# Metrics
duration: 20min
completed: 2026-08-24
---

# Phase 1 Plan 02: Seed + EstimationService Summary

**Idempotent upsert seed loads the Reggio Emilia listino from `docs/seed-coefficienti-base.json`, and a Decimal-only `EstimationService.compute()` turns `(listino, mq, tipo)` into 4 category ranges with per-category IVA plus fixed extras, matching the plausibility oracles exactly.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 1 TDD feature (RED -> GREEN, no REFACTOR needed) — 2 gate commits
- **Files created:** 7 (2 implementation modules + seed script + 2 test files + 2 `__init__.py`)
- **Tests:** 12/12 passing

## Accomplishments
- `backend/scripts/seed.py` upserts by natural key (listino by nome, categoria by code, listino_categoria by (listino,categoria), tipo by code, moltiplicatore by (tipo,categoria), extra by code, comune_listino by comune_slug) — running it twice against a real SQLite DB (`alembic upgrade head` -> seed -> seed) leaves identical row counts: 1 listino, 4 categorie, 3 tipi, 12 moltiplicatori, 2 extra, 2 comune_listino.
- `coefficiente_impresa` mapped A-EDILE->0.65, B-FINITURE->0.6, C-SERRAMENTI->0.55, D-PRODOTTI->0.5 per 01-RESEARCH.md's resolved Open Question 1; stored on `ListinoCategoria` but never read by anything client-facing.
- `app/services/city_resolver.py`'s `resolve_listino()` slug-matches `comune_listino` (via `python-slugify`) and falls back to the `is_default=True` listino + `fallback=True` when no dedicated listino exists.
- `app/services/estimation.py`'s `EstimationService.compute()` reads `base_eur_mq`, `moltiplicatore.valore`, `tipo.range_pct`, `categoria.iva_pct`, and `extra` rows from the DB (zero hardcoded coefficients — verified by grep), computes `imponibile = base * molt * mq`, applies per-category IVA, then applies `±range_pct` to each category's (imponibile+IVA) subtotal only, and sums fixed extra gross values (`importo * (1+iva_pct)`, never scaled by range) on top.
- **Primary oracle pinned exactly:** 85 mq, tipo=totale -> totale_min=47985, totale_max=70575 (matches `docs/seed-listino-reggio-emilia.md` plausibility table to the euro).
- Secondary oracles (60mq and 110mq, tipo=totale) verified within ±1€.
- Reconciliation verified exactly: Σ(4 category totale_min) + Σ(fixed extras gross) == `result.totale_min` (same for max) — not just within tolerance, exact equality by construction.
- Fixed extras verified: CSE_CSP (800) + pratiche (1500), both at 22% IVA, sum to a fixed gross of 2.806€ that is identical at both totale_min and totale_max (never scaled by the range).
- Low-multiplier edge case (Serramenti in `leggera`, moltiplicatore=0.10) returns a valid non-negative `min <= max` range, never `None`/`NaN`.
- Anti-leak assertion: `repr(StimaResult(...))` contains neither `coefficiente_impresa` nor any of the raw coefficient values (0.65/0.55) — the result dataclasses are hand-built with a closed field set, never `model_validate`'d off an ORM entity.

## Task Commits

TDD gate sequence (single feature, RED -> GREEN):

1. **RED** — `0e58b91` (test): failing `test_seed.py` + `test_estimation.py`, confirmed collection-time `ModuleNotFoundError` before any implementation existed.
2. **GREEN** — `d0a40cc` (feat): `scripts/seed.py`, `app/services/city_resolver.py`, `app/services/estimation.py` — all 12 tests pass.
3. **REFACTOR** — not needed; implementation was clean on first pass (no duplication, no dead code).

**Plan metadata:** (this commit, docs: complete plan)

## TDD Gate Compliance

RED gate commit (`0e58b91`, `test(...)`) precedes the GREEN gate commit (`d0a40cc`, `feat(...)`) in git log — sequence verified. No REFACTOR commit was needed.

## Files Created/Modified
- `backend/scripts/seed.py` — idempotent upsert seed from `docs/seed-coefficienti-base.json`; runnable both as `python scripts/seed.py` and `python -m scripts.seed`.
- `backend/scripts/__init__.py` — makes `scripts` importable as a package (for tests and `-m` execution).
- `backend/app/services/estimation.py` — `EstimationService.compute()` + `CategoriaEstimata`/`ExtraEstimato`/`StimaResult` frozen dataclasses (closed, anti-leak field set).
- `backend/app/services/city_resolver.py` — `resolve_listino(session, citta) -> (Listino, fallback: bool)`.
- `backend/app/services/__init__.py` — services package docstring documenting the anti-leak boundary.
- `backend/tests/test_seed.py` — idempotency + full-dataset-count regression tests.
- `backend/tests/test_estimation.py` — oracle regression (primary pinned exactly, secondary within ±1€), reconciliation, per-category IVA, fixed-extras, low-multiplier range, anti-leak, city-resolver fallback tests.

## Decisions Made
- `comune_listino` seeded with 2 rows for RE aliases ("Reggio Emilia", "Reggio nell'Emilia") rather than exactly 1 — required so both `resolve_listino("reggio emilia")` and `resolve_listino("Reggio nell'Emilia")` return `fallback=False` per the plan's own city-resolver behavior spec (these two strings slugify to different values, so one row cannot cover both). The must_haves narrative phrase "1 comune_listino for RE" is read as "the RE mapping" collectively, not a literal single-row count — the literal test-visible requirement (both aliases resolving without fallback) governed the implementation.
- Added a `sys.path` bootstrap at the top of `scripts/seed.py` so the plan's exact verification command (`uv run python scripts/seed.py`, run directly rather than as `-m scripts.seed`) works — without it, `python scripts/seed.py` cannot import the `app` package because only `scripts/`'s own directory (not `backend/`) is auto-added to `sys.path` when a script is executed directly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `python scripts/seed.py` direct execution couldn't import `app`**
- **Found during:** Manual verification of the plan's exact command (`uv run python scripts/seed.py`, twice)
- **Issue:** Running the script directly only adds `scripts/`'s own directory to `sys.path` (Python's standard behavior for `python <file>`), not `backend/` — so `import app.models` failed with `ModuleNotFoundError`, even though the equivalent `pytest`-driven import worked (pytest adds `backend/` via package-rootdir discovery, since `scripts/__init__.py`/`app/__init__.py` exist).
- **Fix:** Added a small `sys.path.insert(0, str(backend_dir))` bootstrap at the top of `scripts/seed.py`, computed from `Path(__file__).resolve().parent.parent`, before importing any `app.*` module.
- **Files modified:** `backend/scripts/seed.py`
- **Verification:** `rm dev.db && alembic upgrade head && uv run python scripts/seed.py` (twice) — both runs succeed and leave identical row counts (1/4/3/12/2/2).
- **Committed in:** `d0a40cc` (GREEN commit — the fix is part of the initial implementation, not a separate patch)

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** Necessary to make the plan's own verification command work exactly as written; no scope creep.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required
None. Seed runs entirely against the local dev SQLite DB (`sqlite:///./dev.db`) created by `alembic upgrade head`; no external service or secret needed.

## Next Phase Readiness
- `EstimationService` and `resolve_listino` are ready to be wired into a `POST /api/v1/stima` router (Plan 01-03) — the response DTO (`app/schemas/`) will map `StimaResult`'s dataclasses onto the Pydantic `StimaResponse` contract from 01-RESEARCH.md, still without ever touching `coefficiente_impresa`/`base_eur_mq`/`moltiplicatore`.
- The seed is safe to run against a fresh `dev.db` or CI DB at any point (idempotent); Plan 01-03/04 test suites can call `seed(session, load_seed_data())` directly in fixtures, as demonstrated by `tests/test_estimation.py`.
- No blockers. Rate limiting (slowapi, already wired in `app/main.py` from 01-01) and CORS remain available for the upcoming public `/stima` endpoint.

---
*Phase: 01-stima-free-end-to-end*
*Completed: 2026-08-24*

## Self-Check: PASSED

All 6 created files verified present on disk; both commits (0e58b91, d0a40cc) verified present in git log.
