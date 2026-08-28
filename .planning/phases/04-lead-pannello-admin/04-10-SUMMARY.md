---
phase: 04-lead-pannello-admin
plan: 10
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, admin, coefficienti, tdd]

# Dependency graph
requires:
  - phase: 04-lead-pannello-admin
    provides: "stub routers/admin/coefficienti.py + require_admin (04-02)"
provides:
  - "CRUD /admin/coefficienti per le 4 famiglie D-12: moltiplicatori tipo×categoria, IVA per categoria, extra, coefficienti quantità-per-m² Pro"
  - "GET /admin/coefficienti/base in sola lettura di base_eur_mq per la UI Coefficienti"
  - "Verifica automatizzata dell'effetto immediato (D-11): PATCH moltiplicatore -> nuova POST /api/v1/stima riflette subito il valore"
affects: [04-08-ui-coefficienti]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Upsert per chiave naturale (Extra.code) — stesso pattern di upsert_categoria in 04-02, non duplica su ripetuta POST"
    - "PATCH parziale con campi Optional — nessun campo obbligatorio, D-24 non azzera nulla non inviato"
    - "GET in sola lettura di un campo la cui scrittura resta su un altro router (base_eur_mq -> /admin/listini)"

key-files:
  created:
    - backend/app/schemas/admin_coefficienti.py
    - backend/tests/test_admin_coefficienti.py
  modified:
    - backend/app/routers/admin/coefficienti.py

key-decisions:
  - "GET /coefficienti/base espone SOLO base_eur_mq (mai coefficiente_impresa) e resta sola lettura: la scrittura di base_eur_mq rimane sul CRUD /admin/listini di 04-02, per non duplicare il percorso di editing (D-12 lo cita esplicitamente come 'coerente con listini')"
  - "POST /coefficienti/extra fa upsert per chiave naturale code (non solo create) — stesso pattern D-24 già usato in 04-02 per ListinoCategoria, garantisce idempotenza su retry"
  - "CoeffProAdminIn/Out usano il nome di campo 'valore' (non coefficiente_qta_per_mq) per coerenza con MoltiplicatoreAdminIn — mapping esplicito nel router"

patterns-established: []

requirements-completed: [ADM-02]

# Metrics
duration: 35min
completed: 2026-08-28
---

# Phase 04 Plan 10: CRUD coefficienti admin (moltiplicatori, IVA, extra, coeff-pro) Summary

**CRUD completo delle 4 famiglie di coefficienti D-12 dietro require_admin, con test automatico che prova l'effetto immediato (D-11) su una nuova stima dopo un PATCH.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-28T10:10:00Z (stimato)
- **Completed:** 2026-08-28T10:44:51Z
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments
- Schemi Pydantic (`admin_coefficienti.py`) con bound ASVS V5 per le 4 famiglie: moltiplicatori (`gt=0`), IVA (`ge=0, lt=1`), extra (`importo ge=0`, `iva_pct ge=0 lt=1`), coeff-pro (`ge=0`)
- Router `/admin/coefficienti` completo: GET/PATCH moltiplicatori, GET/PATCH IVA per categoria, GET/POST/PATCH/DELETE extra, GET/PATCH coeff-pro, GET base (sola lettura)
- Test end-to-end (27 casi) che copre 403 non-admin su ogni route, bound Pydantic, non-azzeramento D-24, e l'effetto immediato D-11 verificato via una POST /api/v1/stima prima/dopo il PATCH
- Suite backend completa verde (168 passed, 4 skipped) a parte un fallimento pre-esistente estraneo al piano (vedi Deviazioni)

## Task Commits

Each task was committed atomically:

1. **Task 1: Schemi coefficienti + test RED** - `8863bbd` (test)
2. **Task 2: CRUD /admin/coefficienti + effetto immediato (GREEN)** - `d718a25` (feat)

_Nessun refactor necessario — GREEN al primo tentativo._

## Files Created/Modified
- `backend/app/schemas/admin_coefficienti.py` - DTO In/Out per moltiplicatori, IVA, extra, coeff-pro Pro, base_eur_mq (sola lettura)
- `backend/tests/test_admin_coefficienti.py` - 27 test E2E via TestClient (403, bound, D-24, effetto immediato D-11)
- `backend/app/routers/admin/coefficienti.py` - implementazione completa del router (era uno stub da 04-02)

## Decisions Made
- `GET /coefficienti/base` resta sola lettura; la scrittura di `base_eur_mq` rimane sul CRUD `/admin/listini` esistente (04-02), evitando due percorsi di editing per lo stesso campo.
- `POST /extra` fa upsert per `code` (natural key) anziché create-only, coerente con `upsert_categoria` di 04-02 e con D-24 (nessuna duplicazione su retry).
- Nome campo `valore` scelto per `CoeffProAdminIn/Out` (anziché `coefficiente_qta_per_mq`) per coerenza col naming di `MoltiplicatoreAdminIn`, con mapping esplicito nel router (`_to_coeff_pro_out`).

## Deviations from Plan

None — plan eseguito come scritto. Nessuna deviazione applicando le Regole 1-4.

## Issues Encountered

- `tests/test_health.py::test_health_db_returns_live_count` fallisce in questo worktree (`sqlite3.OperationalError: no such table: listino`) — causa nota e già documentata in `04-02` (deferred-items.md): `backend/dev.db` è un file 0-byte in questo checkout, migrazioni mai eseguite contro di esso. File estraneo a `files_modified` di questo piano; verificato che fallisce anche in isolamento, indipendentemente dalle modifiche di 04-10. Non blocca i criteri di accettazione (`test_admin_coefficienti.py` 27/27 verde). Documentato in `.planning/phases/04-lead-pannello-admin/deferred-items.md`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Il router `/admin/coefficienti` è pronto per essere consumato dalla UI Coefficienti di 04-08 (moltiplicatori, IVA, extra, coeff-pro, base in sola lettura).
- Nessun blocco noto.

---
*Phase: 04-lead-pannello-admin*
*Completed: 2026-08-28*

## Self-Check: PASSED

- FOUND: backend/app/schemas/admin_coefficienti.py
- FOUND: backend/tests/test_admin_coefficienti.py
- FOUND: backend/app/routers/admin/coefficienti.py
- FOUND commit: 8863bbd
- FOUND commit: d718a25
