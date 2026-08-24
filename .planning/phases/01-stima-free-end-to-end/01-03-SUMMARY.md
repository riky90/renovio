---
phase: 01-stima-free-end-to-end
plan: 03
subsystem: api
tags: [fastapi, pydantic-v2, slowapi, anti-leak, tdd]

# Dependency graph
requires:
  - phase: 01-stima-free-end-to-end plan 02
    provides: EstimationService.compute() and resolve_listino() (server-side, Decimal-only, anti-leak result objects)
provides:
  - "Public POST /api/v1/stima endpoint: bounded request validation, 4 category ranges + fixed extras + reconciling total, fallback/disclaimer"
  - "Anti-leak Pydantic response schema (StimaResponse/CategoriaOut/ExtraOut/TotaleOut) with a closed field set"
  - "Recursive + substring domain-guard test proving the impresa secret never reaches the wire"
  - "Shared app/limiter.py slowapi Limiter instance, rate-limiting the public endpoint at 20/minute"
affects: [01-04, phase-2-frontend-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared Limiter instance in app/limiter.py (not main.py) so routers can import @limiter.limit without a circular import on app.main"
    - "Exact imponibile/IVA split recovered post-hoc from a category's already-ranged gross totale via totale/(1+iva_pct), never re-derived from raw base_eur_mq/moltiplicatore (which the router never touches)"
    - "Response DTOs built field-by-field from StimaResult dataclasses, never model_validate() on an ORM entity (anti-leak boundary, T-03-01)"

key-files:
  created:
    - backend/app/schemas/stima.py
    - backend/app/routers/stima.py
    - backend/app/limiter.py
    - backend/app/schemas/__init__.py
    - backend/tests/test_stima_api.py
    - backend/tests/test_no_leak.py
  modified:
    - backend/app/main.py

key-decisions:
  - "Introduced app/limiter.py (not in the plan's files_modified list) to share a single slowapi Limiter instance between main.py (app.state.limiter) and routers/stima.py (@limiter.limit decorator) — avoids both a circular import on app.main and a second, disconnected Limiter instance that slowapi's rate-limit bookkeeping would not recognize."
  - "The API contract's imponibile_min/max + iva_min/max per category (not present as separate fields on EstimationService's CategoriaEstimata, which only exposes iva_pct + totale_min/max) are recovered in the router via an exact algebraic split: imponibile = totale/(1+iva_pct), iva = totale-imponibile. This is exact, not approximate, because both the imponibile and IVA components were scaled by the same ±range factor before being combined into totale_min/max — no re-derivation from base_eur_mq/moltiplicatore was needed or performed."
  - "Extra's imponibile/IVA split for the totale block reuses the service's own rounded ExtraEstimato.totale (ex.totale - ex.importo = iva) rather than recomputing importo*iva_pct independently, guaranteeing totale.totale_min/max always reconciles exactly with categorie+extra sums (verified by test, not just tolerance)."

requirements-completed: [EST-01, EST-02, EST-05, EST-06]

# Metrics
duration: ~20min
completed: 2026-08-24
---

# Phase 1 Plan 03: Public Estimate Endpoint Summary

**`POST /api/v1/stima` now returns the full anti-leak contract (4 category ranges + fixed extras + reconciling total + fallback/disclaimer) built explicitly from `EstimationService`/`resolve_listino`, rate-limited and provably free of the impresa secret on the wire.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 (1 TDD feature RED→GREEN, 1 folded into the same TDD cycle) — 2 gate commits
- **Files created:** 6 (2 implementation modules + 1 shared limiter module + package init + 2 test files)
- **Files modified:** 1 (`app/main.py`)
- **Tests:** 26/26 passing (14 new: 5 in `test_stima_api.py` param groups + `test_invalid_input_returns_422` x4, and `test_no_leak.py` x6 parametrized)

## Accomplishments
- `backend/app/schemas/stima.py` defines `StimaRequest` (citta 1..100, mq 1..2000, tipo enum) and a fully closed response model tree (`StimaResponse` → `CategoriaOut`/`ExtraOut`/`TotaleOut`) — none of `base_eur_mq`, `moltiplicatore`, `coefficiente_impresa`, `prezzo_impresa` appear anywhere in the module.
- `backend/app/routers/stima.py` implements `POST /api/v1/stima`: resolves città via `resolve_listino`, computes via `EstimationService.compute`, and builds `StimaResponse` explicitly field-by-field (never `model_validate`'d off an ORM row).
- Oracle pinned exactly: 85 mq/totale/Reggio Emilia → `totale_min=47985`, `totale_max=70575`, `fallback=False`, empty disclaimer. Modena (any tipo) → `fallback=True` with a disclaimer mentioning Reggio Emilia.
- Reconciliation verified: `totale.totale_min/max == Σ categorie.totale_min/max + Σ extra gross` (±1€, matches the service's own authoritative sum) — and additionally `totale.imponibile + totale.iva == totale.totale` exactly, by construction (no rounding drift), across both category and extra components.
- `ExtraOut` exposes exactly `{code, nome, importo, iva_pct}` — no min/max fields, per the fixed-extras rule from Plan 02.
- 422 returned for `mq=0`, `mq=5000`, unknown `tipo`, and empty `citta` (Pydantic v2 `Field` bounds).
- `backend/tests/test_no_leak.py` recursively scans every key in the parsed JSON at any depth plus the raw serialized text for 4 forbidden substrings and 4 forbidden coefficient values (0.65/0.6/0.55/0.5), across both a non-fallback (RE) and a fallback (Modena) città and all 3 tipi (6 parametrized cases) — all pass, proving EST-05 on the wire.
- `app/limiter.py` centralizes the slowapi `Limiter` so `app/main.py` (`app.state.limiter`) and `app/routers/stima.py` (`@limiter.limit("20/minute")`) share one instance instead of two disconnected ones.

## Task Commits

TDD gate sequence (single feature spanning both plan tasks, RED → GREEN):

1. **RED** — `ea929b5` (test): `test_stima_api.py` + `test_no_leak.py`, confirmed `ModuleNotFoundError` (no `app.routers.stima` yet) across all 14 new tests before any implementation existed.
2. **GREEN** — `05224d6` (feat): `app/schemas/stima.py`, `app/routers/stima.py`, `app/limiter.py`, `app/main.py` wiring — all 26 backend tests pass (12 pre-existing + 14 new).
3. **REFACTOR** — not needed; implementation was clean on first pass.

**Plan metadata:** (this commit, docs: complete plan)

## TDD Gate Compliance

RED gate commit (`ea929b5`, `test(...)`) precedes the GREEN gate commit (`05224d6`, `feat(...)`) in git log — sequence verified via `git log --oneline`. No REFACTOR commit was needed.

## Files Created/Modified
- `backend/app/schemas/stima.py` — `StimaRequest` (bounded) + `StimaInputEcho`/`CategoriaOut`/`ExtraOut`/`TotaleOut`/`StimaResponse` (anti-leak, closed field sets).
- `backend/app/schemas/__init__.py` — package docstring documenting the anti-leak gate contract.
- `backend/app/routers/stima.py` — `POST /api/v1/stima`: resolves città, computes via `EstimationService`, builds response explicitly, exact imponibile/IVA split, fallback disclaimer.
- `backend/app/limiter.py` — shared slowapi `Limiter` instance (new file, not in the plan's original `files_modified` list — see Deviations).
- `backend/app/main.py` — imports the shared limiter, registers `stima.router` under `/api/v1`.
- `backend/tests/test_stima_api.py` — oracle regression, fixed-extras shape, reconciliation, fallback/disclaimer, 4x 422 bounds cases.
- `backend/tests/test_no_leak.py` — recursive key scan + substring/coefficient-value scan across RE + Modena × 3 tipi (6 parametrized cases).

## Decisions Made
- Added `app/limiter.py` as a new shared module (deviation from the plan's `files_modified` list, which only listed `main.py`/`routers/stima.py`) — necessary so the endpoint's `@limiter.limit` decorator uses the same `Limiter` instance registered on `app.state.limiter` in `main.py`, rather than either a second disconnected instance or a circular `app.main` import from the router.
- Recovered the API contract's per-category `imponibile_min/max`/`iva_min/max` fields (not present on `EstimationService`'s `CategoriaEstimata`, which only carries `iva_pct` + combined `totale_min/max`) via an exact post-hoc algebraic split in the router, rather than modifying the already-committed, oracle-pinned `EstimationService` from Plan 02.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Shared Limiter instance needed to avoid circular import**
- **Found during:** Task 1 (wiring the rate limiter onto the new router)
- **Issue:** `main.py` defines and owns the `Limiter` instance registered as `app.state.limiter`; the plan's `files_modified` list didn't account for how `routers/stima.py` would access that same instance to decorate the endpoint with `@limiter.limit`. Importing `limiter` from `app.main` into the router would create a circular import (`main.py` imports the `stima` router, which would import back from `main.py`).
- **Fix:** Extracted the `Limiter` instantiation into a new `app/limiter.py` module, imported by both `app/main.py` and `app/routers/stima.py`.
- **Files modified:** `backend/app/limiter.py` (new), `backend/app/main.py`
- **Verification:** `uv run pytest -q` — all 26 tests pass; app imports cleanly with no circular-import error.
- **Committed in:** `05224d6` (GREEN commit)

**2. [Rule 1 - Bug] Recovered imponibile/IVA split absent from EstimationService's category result**
- **Found during:** Task 1 (mapping `EstimationService`'s `CategoriaEstimata` onto `CategoriaOut`)
- **Issue:** The API contract prescribed in 01-RESEARCH.md requires `imponibile_min/max` and `iva_min/max` per category, but Plan 02's already-committed `CategoriaEstimata` dataclass only exposes `iva_pct` + combined `totale_min/max` (imponibile+IVA pre-summed before the range was applied) — there was no field to map directly.
- **Fix:** Added `_split_imponibile_iva()` in the router: since `totale = imponibile*(1+iva_pct)` was scaled by the same range factor on both terms, `imponibile = totale/(1+iva_pct)` is an exact (not approximate) recovery; `iva = totale - imponibile` guarantees the two always sum back to `totale` with zero rounding drift. No modification to the locked `EstimationService` was needed.
- **Files modified:** `backend/app/routers/stima.py`
- **Verification:** `test_totale_reconciles_with_categorie_and_extra` in `test_stima_api.py` passes; manual check confirms `imponibile_min + iva_min == totale_min` exactly for all 4 categories at the 85mq/totale oracle.
- **Committed in:** `05224d6` (GREEN commit)

---

**Total deviations:** 2 auto-fixed (both blocking/bug-fix, both necessary to deliver the contract without touching the already-locked Plan 02 service).
**Impact on plan:** No scope creep — both fixes were required to make the plan's own acceptance criteria (full API contract shape, working rate limit) achievable given the exact shape Plan 02 already committed.

## Issues Encountered
None beyond the two auto-fixed deviations above.

## User Setup Required
None. The endpoint runs entirely against the local dev SQLite DB (or an isolated in-memory/temp-file SQLite DB in tests); no external service or secret needed.

## Next Phase Readiness
- `POST /api/v1/stima` is a complete, tested, anti-leak public contract — ready for frontend integration (Plan 01-04) to call directly with `{citta, mq, tipo}` and render the 4 category cards + total + fallback disclaimer.
- The shared `app/limiter.py` pattern is now the place any future public endpoint should import its rate limiter from.
- No blockers. `GET /api/v1/comuni` (optional autocomplete backend endpoint) was not built in this plan — RESEARCH marks it optional in favor of a client-side bundled JSON dataset, deferred to Plan 01-04 if the frontend needs it.

---
*Phase: 01-stima-free-end-to-end*
*Completed: 2026-08-24*

## Self-Check: PASSED

All 6 created/key files verified present on disk (`app/schemas/stima.py`, `app/routers/stima.py`, `app/limiter.py`, `tests/test_no_leak.py`, `tests/test_stima_api.py`, this SUMMARY.md); both commits (`ea929b5`, `05224d6`) verified present in `git log`.
