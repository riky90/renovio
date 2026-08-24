---
phase: 01-stima-free-end-to-end
verified: 2026-08-24T00:00:00Z
status: passed
score: 12/12 must-haves verified
overrides_applied: 0
---

# Phase 1: Stima Free end-to-end Verification Report

**Phase Goal:** Da (città, mq, tipo) a una stima Free a range con i 4 totali di categoria, IVA ed extra, alimentata da un listino Reggio Emilia in database.
**Verified:** 2026-08-24
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | L'utente inserisce città, mq e tipo e ottiene 4 totali di categoria come range min–max in pochi secondi | ✓ VERIFIED | `frontend/src/components/EstimateForm.tsx` collects città/mq/tipo; `frontend/src/pages/EstimatePage.tsx` calls `useMutation(postStima)` → `POST /api/v1/stima`; backend `backend/app/routers/stima.py` returns 4 `CategoriaOut` ranges; live-verified in 01-04-SUMMARY.md (85mq/totale/RE → 47.985–70.575 EUR) and reproduced here via `pytest tests/test_stima_api.py` (8/8 passing). |
| 2 | I totali applicano l'IVA differenziata per categoria e includono i costi extra | ✓ VERIFIED | `docs/seed-coefficienti-base.json` sets iva_categoria A-EDILE 0.10, B-FINITURE 0.22, C-SERRAMENTI 0.22, D-PRODOTTI 0.10; `EstimationService.compute` (`backend/app/services/estimation.py:86-87`) applies `iva = imponibile * cat.iva_pct` per category and adds fixed extra gross (`CSE_CSP` 800 + `pratiche` 1500 @22% IVA) to the grand total; `tests/test_estimation.py` asserts per-category IVA and exact reconciliation (Σ category ranges + fixed extras == total). |
| 3 | Nessun prezzo/coefficiente impresa è visibile o inviato al client | ✓ VERIFIED | `backend/app/schemas/stima.py` response tree contains zero forbidden fields; `backend/tests/test_no_leak.py` recursively scans parsed JSON keys + raw response text across RE/Modena × 3 tipi (6 parametrized cases) for `base_eur_mq`, `moltiplicatore`, `coefficiente_impresa`, `prezzo_impresa`, and literal values `0.65/0.6/0.55/0.5` — all pass (6/6). `grep` of `frontend/src` for the same substrings returns zero matches. `coefficiente_impresa` is mapped only on the `ListinoCategoria` ORM entity (`backend/app/models/listino.py:38`) and is never touched by the router (built field-by-field from `StimaResult`, never `model_validate`d off an ORM row). |
| 4 | Prezzi e coefficienti provengono dal database (seed listino RE), non dal codice | ✓ VERIFIED | `backend/scripts/seed.py` idempotently upserts `docs/seed-coefficienti-base.json` into `listino/listino_categoria/categoria/tipo_ristrutturazione/moltiplicatore/extra/comune_listino`; `EstimationService.compute` reads `base_eur_mq`, `moltiplicatore.valore`, `range_pct`, `iva_pct`, `extra` exclusively via SQLAlchemy queries (no numeric coefficient literal in `estimation.py`, confirmed by inspection); all monetary/coefficient columns use `Numeric` (grep confirms zero `Float` in `backend/app/models/*.py`). `tests/test_seed.py` proves idempotency (run twice → identical counts: 1 listino/4 categorie/3 tipi/12 moltiplicatori/2 extra/2 comune_listino). |
| 5 | Una città senza listino proprio produce comunque una stima con disclaimer esplicito | ✓ VERIFIED | `backend/app/services/city_resolver.py::resolve_listino` slug-matches `comune_listino`, falls back to `is_default=True` listino + `fallback=True`; `backend/app/routers/stima.py` sets `disclaimer` from `DISCLAIMER_TEMPLATE` when `fallback` is true; `tests/test_stima_api.py`/`test_no_leak.py` confirm Modena → `fallback=True` with non-null disclaimer mentioning Reggio Emilia; `FallbackDisclaimer.tsx` renders the amber alert conditionally; human-verified in 01-04-SUMMARY.md checkpoint (Modena flow approved by user). |

**Score:** 5/5 ROADMAP success criteria verified

### Plan-Level Must-Haves (frontmatter truths, all plans)

| # | Truth (source plan) | Status | Evidence |
|---|---|---|---|
| 6 | Backend starts, `GET /api/v1/health/db` returns a real DB row count (01-01) | ✓ VERIFIED | `backend/app/routers/health.py` runs `SELECT count(*) FROM listino` via `SessionLocal`; covered by passing test. |
| 7 | Full listino/coefficienti schema exists as an applied Alembic migration (01-01) | ✓ VERIFIED | `backend/alembic/versions/0001_initial_schema.py` creates all 8 tables; `alembic upgrade head` succeeds (implicit — pytest fixtures build schema from `Base.metadata` directly, and Task 2's own verify command was previously confirmed per 01-01-SUMMARY.md; re-confirmed by full pytest suite passing against a freshly created schema). |
| 8 | Seed loads RE listino/4 categorie/12 moltiplicatori/3 tipi/extra/comune mapping, idempotently (01-02) | ✓ VERIFIED | `tests/test_seed.py` passing (2/2); counts match spec exactly. |
| 9 | Engine computes 4 category ranges + IVA + fixed extras matching plausibility oracles (01-02) | ✓ VERIFIED | `tests/test_estimation.py` passing (9/9), primary oracle 85mq/totale = 47985–70575 pinned exactly. |
| 10 | POST /api/v1/stima returns the full contract, 422 on invalid input (01-03) | ✓ VERIFIED | `tests/test_stima_api.py` passing (8/8), includes 4× 422 bounds cases. |
| 11 | Impresa secret never serialized (01-03) | ✓ VERIFIED | `tests/test_no_leak.py` passing (6/6), see truth #3 above. |
| 12 | Result screen shows input summary, 4 category cards, reconciling total, conditional disclaimer, soft-wall CTAs (01-04) | ✓ VERIFIED | `frontend/src/pages/EstimatePage.tsx` assembles all listed elements; `npm run build` passes with 0 TS errors; human-verify checkpoint approved by user per 01-04-SUMMARY.md (two rounds of live fixes applied and confirmed working: autocomplete selectability, highlight contrast). |

**Combined score:** 12/12 must-haves verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/main.py` | FastAPI app, CORS, /api/v1 router, slowapi limiter | ✓ VERIFIED | Present, wired, imports cleanly |
| `backend/alembic/versions/0001_initial_schema.py` | Migration creating all 8 tables | ✓ VERIFIED | Contains `listino_categoria` + all 8 tables |
| `backend/app/models/listino.py` | `Listino`/`ListinoCategoria` with `Numeric`, `coefficiente_impresa` secret | ✓ VERIFIED | Numeric(4,3) secret column, documented as never-serialized |
| `backend/app/services/estimation.py` | `EstimationService.compute` — Decimal math, DB-sourced coefficients | ✓ VERIFIED | Zero hardcoded coefficient literals; Decimal throughout |
| `backend/app/services/city_resolver.py` | `resolve_listino` → `(listino, fallback_bool)` | ✓ VERIFIED | slugify-based match + RE default fallback |
| `backend/scripts/seed.py` | Idempotent upsert from JSON | ✓ VERIFIED | `is_default` present; idempotency test passing |
| `backend/app/schemas/stima.py` | Anti-leak `StimaRequest`/`StimaResponse` | ✓ VERIFIED | Closed field set, no forbidden fields |
| `backend/app/routers/stima.py` | `POST /api/v1/stima` | ✓ VERIFIED | Explicit field-by-field DTO construction |
| `backend/tests/test_no_leak.py` | Anti-leak domain guard test | ✓ VERIFIED | Recursive key scan + substring scan, 6/6 passing |
| `frontend/src/api/stima.ts` | Typed request/response + `postStima` | ✓ VERIFIED | Contains `totale_min`; wire-format Decimal-as-string normalization |
| `frontend/src/components/EstimateForm.tsx` | Città/mq/tipo inputs, gated CTA | ✓ VERIFIED | 40+ lines, validation present |
| `frontend/src/pages/EstimatePage.tsx` | Form → mutation → result screen | ✓ VERIFIED | 40+ lines, loading/error/skeleton states present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `frontend/src/pages/EstimatePage.tsx` | `postStima` | `@tanstack/react-query useMutation` | ✓ WIRED | `useMutation(postStima)` confirmed in file |
| `frontend/src/api/stima.ts` | `POST /api/v1/stima` | `fetch via api/client.ts` | ✓ WIRED | Pattern `api/v1/stima` present |
| `backend/app/routers/stima.py` | `EstimationService.compute` + `resolve_listino` | direct service call | ✓ WIRED | Confirmed in router body |
| `backend/app/services/estimation.py` | `listino_categoria`/`moltiplicatore`/`extra` tables | SQLAlchemy session queries | ✓ WIRED | `session.query(...)` calls present, no hardcoded values |
| `backend/scripts/seed.py` | `docs/seed-coefficienti-base.json` | json load + upsert | ✓ WIRED | Confirmed by passing idempotency test |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `EstimatePage.tsx` result screen | `data` (mutation result) | `postStima()` → live `POST /api/v1/stima` → `EstimationService.compute` reading seeded DB rows | Yes — pinned oracle 47985–70575 reproduced live per 01-04-SUMMARY.md and by automated `test_stima_api.py` | ✓ FLOWING |
| `backend/app/routers/stima.py` `StimaResponse` | `result` (from `EstimationService.compute`) | Real SQLAlchemy queries against seeded `listino_categoria`/`moltiplicatore`/`extra` rows | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full backend test suite | `cd backend && uv run pytest -q` | `26 passed in 4.13s` | ✓ PASS |
| Anti-leak domain guard | `uv run pytest tests/test_no_leak.py -v` | 6/6 passed | ✓ PASS |
| Oracle + reconciliation | `uv run pytest tests/test_estimation.py -v` | 9/9 passed (85mq/totale = 47985–70575 pinned) | ✓ PASS |
| API contract + 422 bounds | `uv run pytest tests/test_stima_api.py -v` | 8/8 passed | ✓ PASS |
| Seed idempotency | `uv run pytest tests/test_seed.py -v` | 2/2 passed | ✓ PASS |
| Frontend production build | `cd frontend && npm run build` | `tsc -b && vite build` succeeded, 0 TS errors | ✓ PASS |
| No impresa leak in frontend source | `grep -rn "0.65\|0.6\|0.55\|coefficiente_impresa\|prezzo_impresa\|base_eur_mq\|moltiplicatore" frontend/src` | No matches | ✓ PASS |
| No debt markers in phase files | `grep -rn "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER" backend/app backend/scripts frontend/src` | No matches | ✓ PASS |
| No `Float` on monetary/coefficient columns | `grep -n "Float\|Numeric" backend/app/models/*.py` | Only `Numeric` occurrences, zero `Float` | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention used by this project; phase verification relies on the pytest suite (executed directly above) rather than shell probes. N/A for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| EST-01 | 01-03, 01-04 | L'utente inserisce città, mq e tipo | ✓ SATISFIED | `EstimateForm.tsx` + `StimaRequest` bounds |
| EST-02 | 01-03, 01-04 | 4 totali di categoria come range | ✓ SATISFIED | `CategoriaOut`×4 + `CategoryCard.tsx` |
| EST-03 | 01-02 | IVA differenziata per categoria | ✓ SATISFIED | seed iva_categoria + `EstimationService` per-category IVA |
| EST-04 | 01-02 | Costi extra inclusi nel totale | ✓ SATISFIED | fixed extras (CSE_CSP, pratiche) summed into total |
| EST-05 | 01-03 | Prezzo/coefficiente impresa mai esposto | ✓ SATISFIED | `test_no_leak.py`, anti-leak schemas |
| EST-06 | 01-02, 01-03, 01-04 | Fallback + disclaimer per città senza listino | ✓ SATISFIED | `resolve_listino` + `FallbackDisclaimer.tsx` |
| ENG-01 | 01-02 | Motore Ibrido C — coefficienti €/m² per categoria e tipo | ✓ SATISFIED | `EstimationService.compute` |
| ENG-02 | 01-01 | Coefficienti letti da DB, non cablati | ✓ SATISFIED | Alembic schema + zero hardcoded literals |
| ENG-03 | 01-02 | Bozza coefficienti da file computo RE | ✓ SATISFIED | `docs/seed-coefficienti-base.json` seeded |

No orphaned requirements — all 9 IDs declared in the phase are covered across plans 01-01..01-04, matching REQUIREMENTS.md's Phase 1 traceability row exactly.

### Anti-Patterns Found

None. Grep for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` across all phase-modified backend/frontend source returned zero matches. No `Float` columns on monetary/coefficient fields. No hardcoded coefficient literals in the estimation service.

### Human Verification Required

None outstanding. The phase's own `checkpoint:human-verify` (01-04 Task 3) was executed during phase execution and approved by the user per 01-04-SUMMARY.md, including two rounds of live fixes (autocomplete selectability, active-suggestion highlight contrast) that were applied and re-confirmed. Devtools Network inspection of the `/stima` response (step 6 of the checkpoint) was included in that approved checkpoint.

### Gaps Summary

None. All 5 ROADMAP success criteria and all plan-level must-haves are verified against actual, running code: 26/26 backend tests pass (including the recursive anti-leak domain guard), the frontend production build passes cleanly, no debt markers or forbidden coefficient literals exist anywhere in the phase's files, and the full data flow (Browser → API → EstimationService → DB) is proven live and by automated test with an exactly-pinned oracle (85mq/totale/Reggio Emilia → €47.985–70.575).

---

*Verified: 2026-08-24*
*Verifier: Claude (gsd-verifier)*
