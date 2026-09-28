---
phase: 09-configuratore-pro
reviewed: 2026-09-28T07:52:14Z
depth: standard
files_reviewed: 36
files_reviewed_list:
  - backend/alembic/versions/0021_assi_pro_da_livello_e_chiavi_mirate.py
  - backend/alembic/versions/0022_taratura_pro_approvata.py
  - backend/app/routers/dettaglio_pro.py
  - backend/app/routers/domande.py
  - backend/app/schemas/dettaglio_pro.py
  - backend/app/services/computo_parsing.py
  - backend/app/services/dettaglio_pro.py
  - backend/app/services/effetti.py
  - backend/app/templates/pdf_stima_pro.html
  - backend/scripts/applica_taratura.py
  - backend/scripts/genera_excel_taratura.py
  - backend/scripts/seed.py
  - backend/seed_data/seed-dettaglio-pro.json
  - backend/seed_data/seed-domande.json
  - backend/seed_data/taratura-classi.json
  - backend/tests/fixtures/famiglie_alternative_pro.json
  - backend/tests/test_applica_taratura.py
  - backend/tests/test_dettaglio_pro.py
  - backend/tests/test_dettaglio_pro_alternative.py
  - backend/tests/test_dettaglio_pro_livelli.py
  - backend/tests/test_dettaglio_pro_paywall.py
  - backend/tests/test_domande_api.py
  - backend/tests/test_domande_free.py
  - backend/tests/test_effetti_pro.py
  - backend/tests/test_migrazioni_sqlite.py
  - backend/tests/test_no_leak.py
  - backend/tests/test_pdf_pro.py
  - backend/tests/test_seed_dettaglio.py
  - backend/tests/test_seed_domande_pro.py
  - backend/tests/test_stima_tier.py
  - backend/tests/test_taratura_pro.py
  - docs/seed-dettaglio-pro.json
  - frontend/src/api/dettaglio-pro.ts
  - frontend/src/components/DettaglioProView.tsx
  - frontend/src/components/DomandaField.tsx
  - frontend/src/pages/admin/DettaglioProPage.tsx
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-09-28T07:52:14Z
**Depth:** standard
**Files Reviewed:** 36
**Status:** issues_found

## Summary

Reviewed the non-`.planning` files touched by plans 09-01..09-08 (commit range
`b92e06e..9661c1f`): the Pro engine rewrite (`effetti.py::risolvi_effetti_pro`,
`dettaglio_pro.py`), the two data migrations (0021/0022), the taratura scripts
(`applica_taratura.py`, `genera_excel_taratura.py`), the generic configurator
API/schemas, the frontend panel (`DettaglioProView`, `DomandaField`,
`dettaglio-pro.ts`), and the full test suite for the phase.

Domain rules checked explicitly:
- **No prezzo/coefficiente impresa leak**: verified by direct grep across all
  touched backend/frontend files (only docstring mentions, never a real
  field), and confirmed by the existing `test_no_leak.py` suite (including the
  09-05 extension covering the generic configurator DTO). No new leak surface
  introduced.
- **Output always min–max range**: `DettaglioProService.compute()` still
  applies `TipoRistrutturazione.range_pct` to every voce; no code path
  producing a single point value was found.
- **Prices/coefficients in DB, never hardcoded**: `coefficiente_qta_voce` and
  `taratura-classi.json` remain the source of truth; `PROPOSTA_PER_CLASSE` is
  explicitly documented and used only as a one-time bootstrap fallback, not
  read at request time by the compute path.
- **Migrations reversible on SQLite**: `backend/tests/test_migrazioni_sqlite.py`
  exercises upgrade/downgrade/upgrade round-trips for both 0021 and 0022
  extensively (idempotency, unknown-value skipping, no-duplicate-on-reseed,
  partial-update-only-if-still-at-base-value). Ran the full targeted suite
  (`test_applica_taratura`, `test_dettaglio_pro*`, `test_domande_*`,
  `test_effetti_pro`, `test_migrazioni_sqlite`, `test_no_leak`, `test_pdf_pro`,
  `test_seed_*`, `test_stima_tier`, `test_taratura_pro`) with
  `backend/.venv/Scripts/python.exe -m pytest`: **277 passed, 3 skipped**, no
  failures. No Postgres instance was available to verify 0021/0022 there;
  this remains unverified against Postgres (see WR-01).

Overall the implementation is careful and heavily self-documented, with test
coverage that specifically targets the two failure modes this phase existed
to close (alternative-summing in the Pro engine, migration idempotency). No
Critical/blocker findings. Two Warnings worth fixing and two minor Info items.

## Warnings

### WR-01: Migrations 0021/0022 not verified against Postgres

**File:** `backend/alembic/versions/0021_assi_pro_da_livello_e_chiavi_mirate.py`,
`backend/alembic/versions/0022_taratura_pro_approvata.py`
**Issue:** CLAUDE.md requires migrations to work on both SQLite (dev.db) and
Postgres (production, via Render). `test_migrazioni_sqlite.py` exercises both
migrations thoroughly on SQLite, but there is no equivalent Postgres-backed
test in this phase, and both migrations use raw `sa.table()`/`sa.column()`
introspection-free DML (inserts/updates/deletes keyed on natural strings) that
is generally portable, but relies on SQLite-permissive behaviors in a couple
of spots worth double-checking on Postgres before the next deploy:
- `_effetto_esiste()` / duplicate-detection queries build `WHERE col = val OR
  col IS NULL` conditions dynamically; the logic is standard SQL and should
  work on Postgres, but has never actually run there.
- Migration 0021's data-only inserts don't set `id` (relying on
  autoincrement/serial) — fine on both backends, but again untested on
  Postgres.
**Fix:** Before deploying phase 09 to Render, run `alembic upgrade head` (and
ideally a downgrade/upgrade round-trip) against a throwaway Postgres database
seeded from a production-like snapshot, or at minimum a fresh `seed()`'d
Postgres DB, to confirm 0021/0022 apply cleanly. Consider adding a CI job or
a documented manual step for this, since SQLite and Postgres diverge on FK
enforcement and case-sensitivity that this migration's natural-key lookups
depend on.

### WR-02: Migration 0021 downgrade can delete a pre-existing `finitura` domanda not created by its own upgrade

**File:** `backend/alembic/versions/0021_assi_pro_da_livello_e_chiavi_mirate.py:139-256` (upgrade), `:328-403` (downgrade)
**Issue:** `upgrade()` only inserts the `domanda` row for `finitura` (and its
options) `if riga_domanda is None` — i.e. it is a no-op when the row already
exists (e.g. seeded by `scripts/seed.py::seed_domande` on a fresh DB, or
pre-existing from a prior manual run). `downgrade()`, however,
unconditionally deletes `domanda.code == 'finitura'` and every
`opzione_domanda` row under it, regardless of whether *this* migration was
the one that created them. On a DB where `finitura` pre-existed before 0021
ran (e.g. a newly-seeded DB that later needs 0021 downgraded for some other
reason), downgrading 0021 would destroy domanda/opzioni that upgrade() never
touched — an asymmetric, non-idempotent downgrade. `test_0021_non_duplica_effetti_gia_seminati`
covers the upgrade-side no-op case but there is no test for downgrading that
same scenario, so the gap is untested as well as unguarded.
**Fix:** Track whether this migration's upgrade actually created the
`domanda`/`opzione_domanda` rows (e.g. only delete rows whose `updated_at`
matches the migration's own timestamp, or check `riga_domanda is None`
before insert and record that fact via a side artifact), or simplify by only
deleting the `effetto_opzione` rows this migration created (already keyed by
natural identity) and leaving `domanda`/`opzione_domanda` untouched on
downgrade — same pattern 0022 uses (its `_INCLUDI_SPOSTATI`/`_EFFETTI_RIMOSSI`
downgrade only reverses effetto rows, never touches domanda/opzione).

## Info

### IN-01: `assert` used for a production invariant in `proponi_coefficiente`

**File:** `backend/app/services/computo_parsing.py:330-334`
**Issue:** `assert "bagn" in motivazione.lower()` is a self-check embedded in
non-test code. If Python is ever run with `-O` (optimizations enabled,
disabling asserts), this silently becomes a no-op, and if it were ever to
fail in production (e.g. `_MOTIVAZIONE_PER_CLASSE["rivestimento"]` edited
without updating the wording) it would raise a bare `AssertionError` deep
inside a request/script path serving admin uploads, rather than a clear,
handled error.
**Fix:** Either move this check into a unit test (it reads like a test
assertion that ended up in production code), or drop it — the invariant is
already guaranteed by construction (the string literal is defined two lines
above) and doesn't need a runtime check.

### IN-02: `DettaglioProService.compute()` issues one `CoefficienteQuantitaVoce` query per included voce

**File:** `backend/app/services/dettaglio_pro.py:417-424`
**Issue:** Inside the per-sottocategoria loop, `compute()` runs a separate
`session.query(CoefficienteQuantitaVoce).filter_by(voce_id=voce.id,
tipo_code=tipo).one_or_none()` for every included voce (N+1 pattern). This is
explicitly out of scope for this review (performance issues are excluded
from v1), but is worth a note since the endpoint recomputes on every GET
(`_compute_dettaglio` is called live, not cached) and the voce count will
grow as more categories get Pro data via Excel import.
**Fix:** Not required for this review; if response times become a concern,
batch-load all `CoefficienteQuantitaVoce` rows for the listino/tipo up front
(single query keyed by `voce_id`) instead of querying per voce.

---

_Reviewed: 2026-09-28T07:52:14Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
