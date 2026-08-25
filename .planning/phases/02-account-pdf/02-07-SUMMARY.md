---
phase: 02-account-pdf
plan: 07
subsystem: backend-stime-salvate
tags: [snapshot, sqlalchemy, alembic, tdd, anti-idor, anti-leak]

# Dependency graph
requires:
  - phase: 02-account-pdf
    plan: 03
    provides: get_current_user dependency, router HTTP auth completo, sessione cookie httpOnly verificata end-to-end
provides:
  - "Modello StimaSalvata ibrido (colonne scalari + risultato_json JSON generico), migrazione 0003"
  - "Endpoint /api/v1/me/stime: POST (salva snapshot immutabile), GET (storico), GET/{id} (dettaglio)"
  - "Snapshot congelato con schema_version:1, mai ricalcolato (D-09/Pitfall 5)"
affects: [02-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sqlalchemy.JSON generico (non JSONB) per risultato_json — portabilita SQLite dev / Postgres prod (RESEARCH Environment Availability)"
    - "Router /me/stime: with SessionLocal() as session, Depends(get_current_user) su ogni endpoint, risposta costruita field-by-field da risultato_json (mai model_validate)"
    - "Anti-IDOR: query filtrata su id E user_id insieme -> 404 (non 403) se la stima non e' dell'utente corrente, per non rivelare l'esistenza della risorea altrui"
    - "POST /me/stime accetta il payload StimaResponse-shaped gia' calcolato dal client e lo congela as-is; nessuna chiamata a EstimationService in questo percorso"

key-files:
  created:
    - backend/app/models/stima_salvata.py
    - backend/alembic/versions/0003_stima_salvata.py
    - backend/app/schemas/stima_salvata.py
    - backend/app/routers/stime_salvate.py
    - backend/tests/test_stime_salvate.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/main.py

key-decisions:
  - "Docstring di schemas/stima_salvata.py riformulata per non contenere letteralmente le stringhe della famiglia impresa (coefficiente_impresa/base_eur_mq/moltiplicatore/prezzo_impresa), stesso precedente gia' visto in 02-02/02-03 con password_hash/model_validate, per rispettare in senso stretto il criterio di accettazione meccanico grep -rc == 0"

requirements-completed: [AUTH-03]

# Metrics
duration: 12min
completed: 2026-08-25
---

# Phase 2 Plan 7: Salvataggio stima e storico backend Summary

**Modello ibrido `StimaSalvata` (colonne scalari + `risultato_json` congelato con `schema_version`), migrazione 0003, endpoint `/me/stime` (salva/lista/dettaglio) protetti da sessione con ownership per-utente — snapshot immutabile mai ricalcolato, verificato anti-IDOR (404) e anti-leak ricorsivo. TDD RED→GREEN, 6/6 test nuovi verdi, 53/53 suite totale verde.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-25T12:35:00Z (stima)
- **Completed:** 2026-08-25T12:47:00Z
- **Tasks:** 2 (Task 1 RED, Task 2 GREEN)
- **Files modified:** 7 (5 creati, 2 modificati)

## Accomplishments

- `backend/app/models/stima_salvata.py`: `StimaSalvata` (`__tablename__ "stima"`) con `user_id` FK->`user.id` indicizzato, colonne scalari congelate (`citta`, `mq`, `tipo`, `totale_min`/`totale_max` `Numeric(12,2)`, `fallback`), `risultato_json` mappato su `sqlalchemy.JSON` generico (non `JSONB`, per portabilita' SQLite dev / Postgres prod), `created_at` `server_default=func.now()`. Registrato in `models/__init__.py`.
- `backend/alembic/versions/0003_stima_salvata.py`: migrazione con `down_revision="0002"`, `op.create_table("stima")` esplicita (FK a `user.id`, indice su `user_id`), `downgrade()` che droppa indice e tabella. Verificata `alembic upgrade head` sulla catena 0001->0002->0003.
- `backend/app/schemas/stima_salvata.py`: `StimaSalvataCreate` (rispecchia `StimaResponse` — input/fallback/disclaimer/valuta/categorie/extra/totale, riusando i tipi di `schemas/stima.py`); `StimaSalvataListItem` (id/citta/mq/tipo/totale_min/totale_max/created_at, dalle sole colonne scalari); `StimaSalvataOut` (id/created_at + tutti i campi `StimaResponse` ricostruiti da `risultato_json`). Nessun campo impresa (D-13).
- `backend/app/routers/stime_salvate.py`: `APIRouter(prefix="/me", tags=["stime"])`, ogni endpoint dietro `Depends(get_current_user)`:
  - `POST /stime`: congela il payload `StimaSalvataCreate` — colonne scalari da `input`/`totale`, `risultato_json = payload.model_dump(mode="json")` + `schema_version: 1`. Nessuna chiamata a `EstimationService`. Ritorna `{id, created_at}`, 201.
  - `GET /stime`: lista filtrata `user_id == current_user.id`, ordine `created_at desc`, proiezione dalle colonne scalari (no parsing JSON).
  - `GET /stime/{id}`: query filtrata su `id` E `user_id == current_user.id` insieme -> 404 se non trovata (anti-IDOR, non rivela esistenza), ricostruisce `StimaSalvataOut` field-by-field da `risultato_json`.
- `backend/app/main.py`: `include_router(stime_salvate.router, prefix="/api/v1")`.
- `backend/tests/test_stime_salvate.py`: 6 test e2e con `TestClient` a cookie-jar reale — salva (201+id), storico (lista con citta/mq/tipo/created_at/totale), dettaglio (snapshot completo con 4 categorie), anti-leak ricorsivo sul dettaglio salvato (chiavi/substring `coefficiente_impresa`/`base_eur_mq`/`moltiplicatore`/`prezzo_impresa` assenti), anti-IDOR (utente B su stima di utente A -> 404), 401 senza sessione. RED confermato (404, router assente) prima dell'implementazione.
- Suite completa: 53/53 verdi (6 nuovi + 47 preesistenti).

## Task Commits

1. **Task 1: Test e2e RED per salva/lista/dettaglio + anti-IDOR + anti-leak snapshot** - `19e7795` (test)
2. **Task 2: Modello ibrido + migrazione 0003 + schemi + router /me/stime (GREEN)** - `d54e00b` (feat)

**Plan metadata:** (commit successivo con SUMMARY.md/STATE.md/ROADMAP.md)

## TDD Gate Compliance

RED gate: commit `19e7795` (`test(...)`), confermato fallire con `404 == 201` su `POST /api/v1/me/stime` prima di scrivere qualunque implementazione (router non ancora incluso in `main.py`).
GREEN gate: commit `d54e00b` (`feat(...)`), 6/6 test del file verdi al primo tentativo di implementazione, nessun REFACTOR necessario (nessun commit `refactor(...)`).

## Files Created/Modified

- `backend/app/models/stima_salvata.py` - ORM `StimaSalvata` ibrido
- `backend/app/models/__init__.py` - registrazione `StimaSalvata` su `Base.metadata`
- `backend/alembic/versions/0003_stima_salvata.py` - migrazione tabella `stima`
- `backend/app/schemas/stima_salvata.py` - schemi anti-leak create/list/detail
- `backend/app/routers/stime_salvate.py` - endpoint `/me/stime` (POST/GET/GET-id)
- `backend/app/main.py` - `include_router` per `stime_salvate`
- `backend/tests/test_stime_salvate.py` - 6 test e2e TDD (RED→GREEN)

## Decisions Made

- Docstring di `schemas/stima_salvata.py` riscritta per non contenere letteralmente le stringhe della famiglia impresa (`coefficiente_impresa`/`base_eur_mq`/`moltiplicatore`/`prezzo_impresa`), per soddisfare in senso stretto il criterio di accettazione meccanico del piano (`grep -rc ... == 0`) — stesso pattern gia' incontrato in 02-02-SUMMARY.md (`password_hash`) e 02-03-SUMMARY.md (`model_validate`).

## Deviations from Plan

None - plan eseguito esattamente come scritto. L'unico aggiustamento (riformulazione docstring) e' lo stesso pattern gia' documentato come precedente nei piani 02-02/02-03, applicato qui per lo stesso motivo meccanico, non trattato come deviazione sostanziale.

## Issues Encountered

Nessuno oltre al punto sopra.

## User Setup Required

Nessuna azione utente richiesta per questo plan.

## Next Phase Readiness

- `GET /api/v1/me/stime/{id}` restituisce lo snapshot completo (`risultato_json`) pronto per essere la sorgente unica del PDF Free (Plan 08) — nessun ricalcolo, come richiesto da D-11.
- Lo storico "Le mie stime" (colonne scalari) e' pronto per essere consumato dal frontend (fuori scope di questo plan, backend-only).
- Nessun blocco noto per Plan 02-08.

---
*Phase: 02-account-pdf*
*Completed: 2026-08-25*

## Self-Check: PASSED
All claimed files and commits verified present on disk / in git log.
