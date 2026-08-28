---
phase: 04-lead-pannello-admin
plan: 04
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, admin-crud, anti-leak, lead-dashboard]

# Dependency graph
requires:
  - phase: 04-01
    provides: "models/lead.py (Lead), schemas/lead.py (LeadOut/LeadUpdate), services/lead_service.py (resolve_referente)"
  - phase: 04-02
    provides: "routers/admin/__init__.py aggregatore, stub vuoti lead.py/referenti.py, require_admin/get_current_user"
provides:
  - "GET/PATCH /api/v1/admin/lead: dashboard lead con filtri citta/stato, detail, aggiornamento stato/nota (D-17)"
  - "GET/POST/PATCH/DELETE /api/v1/admin/referenti: CRUD referenti attivo/priorita per listino (D-15/D-16)"
  - "schemas/admin_referenti.py: ReferenteAdminIn/ReferenteAdminUpdate/ReferenteAdminOut (chiuso, nessun campo impresa)"
affects: [04-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Riuso diretto di LeadOut/LeadUpdate (04-01) senza fork: gia' chiusi a campi, nessun dato impresa possibile per costruzione (D-22)"
    - "PATCH parziale via model_dump(exclude_unset=True) per ReferenteAdminUpdate (solo campi presenti nel payload sovrascrivono la riga)"

key-files:
  created:
    - backend/app/schemas/admin_referenti.py
    - backend/tests/test_admin_lead.py
    - backend/tests/test_admin_referenti.py
  modified:
    - backend/app/routers/admin/lead.py
    - backend/app/routers/admin/referenti.py

key-decisions:
  - "ReferenteAdminUpdate separato da ReferenteAdminIn (create): PATCH accetta campi opzionali (es. solo attivo/priorita), create richiede il set completo — evita che un PATCH parziale forzi un listino_id/nome/email a None"
  - "Nessun vincolo di unicita sul referente attivo per citta a livello schema (v1, come da piano): la risoluzione lead (resolve_referente, 04-01) prende gia' il primo attivo per priorita, quindi il CRUD e' coerente senza bisogno di enforcement DB"

requirements-completed: [ADM-04]

# Metrics
duration: 35min
completed: 2026-08-28
---

# Phase 4 Plan 4: Dashboard lead admin + CRUD referenti Summary

**Dashboard lead lato server (list con filtri citta/stato, detail, PATCH stato/nota) e CRUD referenti completo (attivo/priorita), entrambi dietro `require_admin`, riusando `LeadOut`/`LeadUpdate` da 04-01 senza alcun fork di schema**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-08-28
- **Tasks:** 3/3 completati
- **Files modified:** 5 (3 creati, 2 riempiti da stub)

## Accomplishments
- `GET /api/v1/admin/lead` lista i lead con filtri opzionali `citta`/`stato` (query-param), ordinati per `created_at desc`; risponde con `list[LeadOut]` gia' chiuso a campi da 04-01 (nessun fork necessario)
- `GET /api/v1/admin/lead/{id}` restituisce lo snapshot completo a range del lead (404, non leak, se assente)
- `PATCH /api/v1/admin/lead/{id}` aggiorna `stato`/`nota` via `LeadUpdate`, 404 se assente; ri-GET riflette immediatamente le modifiche
- `schemas/admin_referenti.py` introduce `ReferenteAdminIn` (create, campi obbligatori), `ReferenteAdminUpdate` (PATCH parziale) e `ReferenteAdminOut`, nessuno dei quali referenzia dati impresa (struttura invariata da `models/catalogo.py::Referente`, che non ha colonne del genere)
- `routers/admin/referenti.py` implementa il CRUD completo (`GET`/`POST`/`PATCH`/`DELETE`) dietro `require_admin`, con 404 su id inesistente per PATCH/DELETE
- Verificata l'integrazione end-to-end: un `Referente` creato via `POST /admin/referenti` viene risolto correttamente da `resolve_referente` (04-01) per la citta del suo listino — stesso comportamento gia' testato in `test_lead.py`, ri-eseguito verde

## Task Commits

Ogni task committato atomicamente:

1. **Task 1: Test RED dashboard lead + referenti** - `415be61` (test)
2. **Task 2: /admin/lead dashboard (GREEN)** - `755cbd0` (feat)
3. **Task 3: /admin/referenti CRUD (GREEN)** - `bb4e2ae` (feat)

_Nota: tutti e 3 i task erano `tdd="true"`; Task 1 e' la fase RED (test scritti, route inesistenti -> 404, 16/21 fallimenti attesi sui due file), Task 2/3 sono GREEN senza necessita' di fix inline._

## Files Created/Modified
- `backend/app/routers/admin/lead.py` - riempito da stub: `GET ""`, `GET "/{id}"`, `PATCH "/{id}"`, tutte `Depends(require_admin)`
- `backend/app/routers/admin/referenti.py` - riempito da stub: `GET ""`, `POST ""`, `PATCH "/{id}"`, `DELETE "/{id}"`, tutte `Depends(require_admin)`
- `backend/app/schemas/admin_referenti.py` - `ReferenteAdminIn`/`ReferenteAdminUpdate`/`ReferenteAdminOut`
- `backend/tests/test_admin_lead.py` - 11 test (guard 403/401, list, filtri citta/stato, detail 404, patch, anti-leak)
- `backend/tests/test_admin_referenti.py` - 10 test (guard 403/401, CRUD completo, 404, anti-leak, integrazione resolve_referente)

## Decisions Made
- `ReferenteAdminUpdate` separato da `ReferenteAdminIn`: tutti i campi opzionali per non forzare un reset involontario dei campi non passati nel PATCH (coerente col comportamento testato: `PATCH {attivo:false, priorita:5}` non tocca nome/email/listino_id)
- Nessun vincolo DB di unicita sul referente attivo per citta in v1 (come esplicitamente previsto dal piano): "un referente attivo per citta" resta convenzione operativa, non enforced a schema; la risoluzione lead gia' prende il primo per priorita

## Deviations from Plan

None - plan eseguito esattamente come scritto. Nessun fix inline necessario nei task GREEN (Task 2/Task 3): i test RED scritti nel Task 1 erano gia' allineati alle firme di `LeadOut`/`LeadUpdate`/`Referente` esistenti.

## Issues Encountered
Nessuno oltre al fallimento pre-esistente e fuori scope documentato sotto.

## Known Stubs
Nessuno stub introdotto da questo piano.

## Threat Flags
Nessuna nuova superficie non coperta dal `<threat_model>` del piano: le mitigazioni T-04-15/T-04-16/T-04-17/T-04-18 sono tutte implementate come previsto (require_admin su ogni route, LeadOut/ReferenteAdminOut chiusi, LeadUpdate valida solo stato/nota di lunghezza limitata, fallback listino default gia' presente da 04-01).

## User Setup Required
None - nessuna configurazione di servizi esterni richiesta.

## Next Phase Readiness
- `routers/admin/lead.py` e `routers/admin/referenti.py` sono ora API complete e testate: 04-07 (UI admin shell + dashboard + referenti) puo' consumarle direttamente senza ulteriori modifiche server-side
- Pattern PATCH parziale (`model_dump(exclude_unset=True)`) disponibile come riferimento per eventuali altri CRUD admin futuri
- Suite backend completa: 161 passed, 4 skipped, 1 failed. Unico fallimento pre-esistente e fuori scope (gia' documentato in 04-02): `tests/test_health.py::test_health_db_returns_live_count` (`backend/dev.db` vuoto in questo worktree, file non toccato da questo piano; vedi `deferred-items.md`)

## Self-Check: PASSED

Verificati con esito positivo:
- File creati: `backend/app/schemas/admin_referenti.py`, `backend/tests/test_admin_lead.py`, `backend/tests/test_admin_referenti.py` esistono su disco
- File modificati: `backend/app/routers/admin/lead.py`, `backend/app/routers/admin/referenti.py` contengono le route implementate (non piu' stub)
- Commit: `415be61`, `755cbd0`, `bb4e2ae` presenti in `git log --oneline`
- Suite mirata: `uv run pytest tests/test_admin_lead.py tests/test_admin_referenti.py` -> 21/21 passed
- Integrazione: `uv run pytest tests/test_lead.py` -> 11/11 passed (risoluzione referente coerente col CRUD admin)
- Suite completa: `uv run pytest` -> 161 passed, 4 skipped, 1 failed (fuori scope, vedi sopra)

---
*Phase: 04-lead-pannello-admin*
*Completed: 2026-08-28*

## Self-Check: PASSED (verified post-write)

- FOUND: backend/app/schemas/admin_referenti.py
- FOUND: backend/tests/test_admin_lead.py
- FOUND: backend/tests/test_admin_referenti.py
- FOUND commits: 415be61, 755cbd0, bb4e2ae
