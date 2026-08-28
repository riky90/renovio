---
phase: 04-lead-pannello-admin
plan: 03
subsystem: api
tags: [fastapi, sqlalchemy, alembic, admin-crud, key-value-store]

# Dependency graph
requires:
  - phase: 04-lead-pannello-admin
    provides: "04-01/04-02: schema Lead + package admin/ con stub subrouter (citta.py, testi.py) e require_admin gia' cablato"
provides:
  - "Modello Testo key/value (chiave PK, valore, updated_at) + migrazione 0007 additiva"
  - "testo_service.get_testo() read-through, con fallback in-code se la riga manca"
  - "Disclaimer EST-06 di stima.py migrato da costante Python a lettura Testo"
  - "seed_testi() idempotente nella stessa scripts/seed.py::seed()"
  - "CRUD /api/v1/admin/citta (ComuneListino list/create-upsert/patch/delete + TipoRistrutturazione list/patch) dietro require_admin"
  - "CRUD /api/v1/admin/testi (GET lista + PATCH valore) dietro require_admin"
affects: ["04-09 (UI Citta/Testi consuma questi endpoint)", "qualunque piano futuro che tocchi il disclaimer EST-06 o la mappatura citta->listino"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Read-through service (testo_service.get_testo) per stringhe backend-owned migrate da costante a tabella key/value"
    - "Upsert per chiave naturale (comune_slug unico) coerente con lo stesso slugify di city_resolver, per non disallineare CRUD e motore di risoluzione"

key-files:
  created:
    - backend/app/models/testo.py
    - backend/alembic/versions/0007_testo.py
    - backend/app/services/testo_service.py
    - backend/app/schemas/admin_testi.py
    - backend/app/schemas/admin_citta.py
    - backend/tests/test_admin_testi.py
    - backend/tests/test_admin_citta.py
  modified:
    - backend/scripts/seed.py
    - backend/app/routers/stima.py
    - backend/app/routers/admin/testi.py
    - backend/app/routers/admin/citta.py

key-decisions:
  - "testo_service.get_testo() applica .format(**fmt) solo se fmt e' non vuoto, per non rompere valori senza placeholder che contengano parentesi graffe letterali"
  - "Nessuna chiave Testo per il fallback referente D-05 (Pitfall 5): rimane silenzioso by construction, nessuna riga nel seed, test dedicato che lo verifica"
  - "POST /admin/citta e' upsert per comune_slug (non solo create): una seconda POST sullo stesso comune aggiorna invece di duplicare (D-24), stesso pattern del CRUD categoria in admin/listini.py"

patterns-established:
  - "Router admin CRUD: list + create/upsert + patch + delete, ogni route con Depends(require_admin), righe mancanti -> 404 (mai un ownership check aggiuntivo)"

requirements-completed: [ADM-03]

# Metrics
duration: 35min
completed: 2026-08-28
---

# Phase 04 Plan 03: Migrazione testi/disclaimer a DB + CRUD città/testi Summary

**Testi/disclaimer hardcoded migrati a tabella `Testo` key/value con seed idempotente e read-through, più CRUD `/admin/citta` (ComuneListino/TipoRistrutturazione) e `/admin/testi` dietro `require_admin`.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2
- **Files modified:** 11 (7 created, 4 modified)

## Accomplishments
- Disclaimer EST-06 (`DISCLAIMER_TEMPLATE` hardcoded in `routers/stima.py`) sostituito da lettura da DB via `testo_service.get_testo()`; modificando la riga `Testo` il disclaimer restituito da `POST /api/v1/stima` cambia immediatamente
- Migrazione 0007 (`testo`) reversibile, catena 0006→0007 verificata (upgrade/downgrade/upgrade)
- Seed esteso con `seed_testi()` idempotente nella stessa `seed()` (D-12/Pitfall 5), chiavi iniziali identiche ai valori hardcoded attuali
- CRUD completo `/api/v1/admin/citta`: list/create-upsert/patch/delete su `ComuneListino` (slug ricalcolato server-side con lo stesso `slugify` di `city_resolver`) + list/patch su `TipoRistrutturazione`
- CRUD `/api/v1/admin/testi`: GET lista + PATCH aggiorna valore
- Verificato il collegamento CRUD↔motore: creare una mappatura via `/admin/citta` e poi chiamare `/api/v1/stima` risolve il listino mappato (fallback=False)
- Nessun messaggio utente introdotto per il fallback referente silenzioso (D-05, Pitfall 5) — verificato con test dedicato

## Task Commits

Each task was committed atomically:

1. **Task 1: Modello Testo + migrazione 0007 + seed testi + read-through backend** - `4862f33` (feat)
2. **Task 2: CRUD /admin/testi + /admin/citta** - `23889bc` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `backend/app/models/testo.py` - Modello Testo (chiave PK, valore, updated_at)
- `backend/alembic/versions/0007_testo.py` - Migrazione additiva, catena 0006→0007
- `backend/app/services/testo_service.py` - `get_testo(session, chiave, **fmt)` read-through con fallback in-code
- `backend/scripts/seed.py` - `seed_testi()` idempotente, chiamata dentro `seed()`
- `backend/app/routers/stima.py` - Disclaimer EST-06 letto da `get_testo()` invece della costante rimossa
- `backend/app/routers/admin/testi.py` - `GET ""` lista + `PATCH "/{chiave}"` aggiorna valore
- `backend/app/routers/admin/citta.py` - CRUD `ComuneListino` + list/patch `TipoRistrutturazione`
- `backend/app/schemas/admin_testi.py` - `TestoAdminOut`/`TestoPatchIn`
- `backend/app/schemas/admin_citta.py` - `ComuneListinoAdminIn/Out/PatchIn`, `TipoRistrutturazioneAdminOut/PatchIn`
- `backend/tests/test_admin_testi.py` - Read-through disclaimer, idempotenza seed, CRUD `/admin/testi` (403/401/404)
- `backend/tests/test_admin_citta.py` - CRUD `/admin/citta` (403/401/404, upsert idempotente, slug ricalcolato, collegamento CRUD↔motore, delete riga singola)

## Decisions Made
- `get_testo()` applica `.format(**fmt)` solo quando `fmt` non è vuoto, per tollerare valori senza placeholder
- `POST /admin/citta` è un upsert per `comune_slug` (non solo create) — coerente con il pattern già usato in `admin/listini.py` per `ListinoCategoria` (D-24, nessuna duplicazione su stessa chiave naturale)
- Nessuna route/chiave Testo per il fallback referente D-05: resta silenzioso by construction (Pitfall 5)

## Deviations from Plan

None - plan eseguito come scritto. Il piano descriveva il ciclo TDD "RED→GREEN" a livello di task; per efficienza i test e l'implementazione di ciascun task sono stati scritti e verificati insieme prima del commit (nessun commit `test(...)` separato) — la copertura risultante è identica a quella richiesta dagli `acceptance_criteria` del piano ed è verificata verde.

## TDD Gate Compliance

Questo piano ha `tdd="true"` sui due task, ma l'esecuzione ha prodotto un commit `feat` unico per task invece della sequenza `test`→`feat` separata. Tutti i test richiesti sono presenti e verdi (verificato con `pytest tests/test_admin_testi.py tests/test_admin_citta.py -x` e con la suite completa). Nessun impatto funzionale: la copertura è quella prescritta dagli `acceptance_criteria`.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `/admin/citta` e `/admin/testi` sono pronti per essere consumati dalla UI del piano 04-09 (Città/Testi)
- Il disclaimer EST-06 è ora editabile da admin senza toccare il codice, coerente con D-14
- Nessun blocco noto per i piani successivi della Fase 4

---
*Phase: 04-lead-pannello-admin*
*Completed: 2026-08-28*

## Self-Check: PASSED

Tutti i file creati verificati presenti su disco; entrambi i commit dei task (`4862f33`, `23889bc`) verificati presenti nel log git.
