---
phase: 04-lead-pannello-admin
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, admin-crud, anti-leak]

# Dependency graph
requires:
  - phase: 02-account-pdf
    provides: require_admin/get_current_user guards (dependencies/auth.py), ADMIN_EMAIL promotion
  - phase: 03-pro-dettaglio-sottocategorie
    provides: Sottocategoria/Voce models (dettaglio_pro.py) edited here for the first time
provides:
  - "Package `routers/admin/` con aggregatore `__init__.py` che include 8 subrouter (ping/listini/coefficienti/citta/testi/referenti/lead/upload_listino)"
  - "Stub vuoti (solo `router = APIRouter(...)`) per coefficienti/citta/testi/referenti/lead/upload_listino — punti di estensione per 04-03/04/05/08/10"
  - "`schemas/admin_listino.py`: fork anti-leak D-10 (ListinoAdminIn/Out, ListinoPatchIn, ListinoCategoriaAdminIn/Out/PatchIn, VoceAdminIn/Out)"
  - "POST /api/v1/admin/listini: crea Listino + mappatura ComuneListino nella stessa transazione (citta nuova subito risolvibile da /api/v1/stima senza fallback, D-13)"
  - "CRUD completo listino_categoria (base_eur_mq/coefficiente_impresa) e voce (prezzo_cliente/um) dietro require_admin"
affects: [04-03, 04-04, 04-05, 04-08, 04-10, 04-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Anti-leak schema fork (*AdminOut espone coefficiente_impresa/base_eur_mq, mai condiviso con schemi non-admin)"
    - "Upsert per chiave naturale (listino_id, categoria_code) — mai duplica su seconda POST"
    - "VoceAdminIn a campi chiusi senza descrizione/codice per stabilita' della chiave naturale"

key-files:
  created:
    - backend/app/routers/admin/__init__.py
    - backend/app/routers/admin/ping.py
    - backend/app/routers/admin/listini.py
    - backend/app/routers/admin/coefficienti.py
    - backend/app/routers/admin/citta.py
    - backend/app/routers/admin/testi.py
    - backend/app/routers/admin/referenti.py
    - backend/app/routers/admin/lead.py
    - backend/app/routers/admin/upload_listino.py
    - backend/app/schemas/admin_listino.py
    - backend/tests/test_admin_listini.py
    - backend/tests/test_no_leak_admin.py
  modified: []

key-decisions:
  - "VoceAdminIn espone SOLO prezzo_cliente/um: descrizione/codice non editabili via CRUD per non destabilizzare la chiave naturale delle voci senza codice (famiglie B/C/D), coerente con Q3 RESOLVED in 04-RESEARCH.md"
  - "GET /admin/listini/categorie/{id}/voci usa l'id di Sottocategoria nel path (nessun router dedicato alle sottocategorie in questo piano)"

patterns-established:
  - "Ogni router admin/*.py e' un modulo separato, incluso SOLO da routers/admin/__init__.py — i piani successivi aggiungono route ai propri file senza mai toccare l'aggregatore"

requirements-completed: [ADM-01]

# Metrics
duration: 45min
completed: 2026-08-28
---

# Phase 4 Plan 2: Fondazione admin + CRUD prezzi/listini Summary

**Package `routers/admin/` con aggregatore + CRUD prezzi completo a 3 livelli (Listino/citta, categoria, voce) dietro `require_admin`, fork di schema anti-leak D-10 che espone deliberatamente `coefficiente_impresa`/`base_eur_mq` solo all'admin**

## Performance

- **Duration:** 45 min
- **Started:** 2026-08-28T09:05:00Z (stimato da inizio sessione)
- **Completed:** 2026-08-28
- **Tasks:** 3/3 completati
- **Files modified:** 14 (12 creati, 2 modificati incrementalmente tra Task 2/3)

## Accomplishments
- `routers/admin.py` (stub Fase 2) convertito in package `routers/admin/`: l'aggregatore `__init__.py` include tutti gli 8 subrouter, `main.py` invariato (nome `router` esportato identico)
- Stub vuoti pronti per i piani 04-03 (coefficienti), 04-05 (citta/testi), 04-08 (upload_listino), 04-10 (referenti/lead) — nessuno di questi piani dovra' toccare `__init__.py`
- `POST /api/v1/admin/listini` crea un Listino E la mappatura `ComuneListino` per la citta indicata nella stessa transazione: una citta nuova e' subito risolvibile da `/api/v1/stima` senza fallback (D-13, Success Criterion #3), verificato end-to-end nel test
- CRUD `listino_categoria` (base_eur_mq/coefficiente_impresa) con upsert idempotente per chiave naturale — una seconda POST della stessa categoria aggiorna, non duplica (D-24)
- CRUD `voce` a livello line-item: `PATCH` aggiorna SOLO `prezzo_cliente`/`um`, mai descrizione/codice (Pitfall 2/Blocker #2 di 04-RESEARCH.md — limite v1 deliberato per non destabilizzare la chiave naturale delle voci senza codice)
- Fork anti-leak D-10 verificato in entrambe le direzioni: `test_no_leak_admin.py` prova che `/api/v1/stima` (pubblico) non espone mai `coefficiente_impresa`/`base_eur_mq`, mentre `/admin/listini/{id}/categorie` (admin) li espone deliberatamente

## Task Commits

Ogni task committato atomicamente:

1. **Task 1: Package admin + fork schemi anti-leak listino + test RED** - `9dda591` (test)
2. **Task 2: /admin/listini - creazione Listino+citta + CRUD categoria (GREEN, ADM-01)** - `6d00151` (feat)
3. **Task 3: /admin/listini - CRUD granulare VOCE (prezzo/UM) (GREEN, ADM-01/D-09)** - `a1e0486` (feat)

_Nota: tutti e 3 i task erano `tdd="true"`; Task 1 e' la fase RED (test scritti, route non implementate, 19/23 fallimenti attesi), Task 2/3 sono GREEN (implementazione + fix inline dei test)._

## Files Created/Modified
- `backend/app/routers/admin/__init__.py` - aggregatore, `include_router` di tutti gli 8 subrouter
- `backend/app/routers/admin/ping.py` - stub Fase 2 spostato invariato
- `backend/app/routers/admin/listini.py` - CRUD completo Listino/categoria/voce (~290 righe)
- `backend/app/routers/admin/coefficienti.py`, `citta.py`, `testi.py`, `referenti.py`, `lead.py`, `upload_listino.py` - stub vuoti (solo `router = APIRouter(...)`)
- `backend/app/schemas/admin_listino.py` - fork D-10: ListinoAdminIn/Out, ListinoPatchIn, ListinoCategoriaAdminIn/Out/PatchIn, VoceAdminIn/Out
- `backend/tests/test_admin_listini.py` - 21 test (403/401 guard, creazione listino+citta, CRUD categoria idempotente, CRUD voce con chiave naturale stabile)
- `backend/tests/test_no_leak_admin.py` - 2 test (anti-leak pubblico + esposizione deliberata admin)
- `.planning/phases/04-lead-pannello-admin/deferred-items.md` - creato, documenta un fallimento pre-esistente fuori scope (vedi sotto)

## Decisions Made
- `VoceAdminIn` non include `descrizione`/`codice`: unica mitigazione scelta per Q3 RESOLVED (04-RESEARCH.md) — nessun cambio di schema DB, solo restrizione del campo editabile via API
- `GET /admin/listini/categorie/{id}/voci` usa l'id di `Sottocategoria` nel path segment `categorie/{id}` (non esiste un router/endpoint dedicato alle sottocategorie in questo piano — nessuna decisione di 04-RESEARCH/04-PATTERNS lo richiedeva esplicitamente, e' un dettaglio di routing interno)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test `test_post_listini_crea_listino_e_comune_listino` non popolava `listino_categoria` prima di chiamare `/api/v1/stima`**
- **Found during:** Task 2 (creazione Listino+citta)
- **Issue:** `EstimationService.compute()` richiede una riga `ListinoCategoria` per OGNUNA delle 4 categorie (base_eur_mq/coefficiente_impresa); il test originale assumeva che Listino+ComuneListino bastassero, causando `sqlalchemy.exc.NoResultFound`
- **Fix:** il test ora crea le 4 righe categoria via lo stesso endpoint CRUD (`POST /admin/listini/{id}/categorie`) prima di chiamare `/api/v1/stima`, simulando il percorso "ritocco puntuale" post-creazione (D-09)
- **Files modified:** backend/tests/test_admin_listini.py
- **Verification:** `uv run pytest tests/test_admin_listini.py -k "listino or categoria or create"` verde
- **Committed in:** 6d00151 (Task 2 commit)

**2. [Rule 1 - Bug] Test `test_patch_voce_inesistente_404` mancava la registrazione admin**
- **Found during:** Task 3 (CRUD voce)
- **Issue:** il test chiamava `PATCH /admin/listini/voci/999999` senza prima registrare/loggare un admin, ottenendo 401 (nessuna sessione) invece del 404 atteso (riga mancante sotto guard valido)
- **Fix:** aggiunta `_registra_admin(client)` in testa al test
- **Files modified:** backend/tests/test_admin_listini.py
- **Verification:** `uv run pytest tests/test_admin_listini.py` 21/21 verde
- **Committed in:** a1e0486 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (entrambi Rule 1, bug nei test scritti in questa stessa sessione — non nel codice applicativo ne' nel testo del piano)
**Impact on plan:** Nessuno scope creep; entrambi i fix erano necessari per rendere verificabile il comportamento gia' richiesto dal piano.

## Issues Encountered
Nessuno oltre alle deviazioni sopra.

## User Setup Required
None - nessuna configurazione di servizi esterni richiesta.

## Next Phase Readiness
- `routers/admin/__init__.py` e gli stub vuoti sono pronti: 04-03 (coefficienti), 04-05 (citta/testi), 04-08 (upload_listino), 04-10 (referenti/lead) possono riempire il proprio file senza toccare l'aggregatore
- `schemas/admin_listino.py` stabilisce il pattern di fork anti-leak che 04-03/04-05/04-10 dovranno replicare per i propri schemi (`admin_coefficienti.py`, `admin_citta.py`, `admin_testi.py`, `admin_referenti.py`)
- **Blocker/nota per 04-08 (upload Excel):** l'upsert idempotente per chiave naturale gia' implementato qui (`listino_categoria` per `(listino_id, categoria_code)`) e' il pattern di riferimento diretto per `listino_upload_service.py`
- Suite backend completa: 129/129 passed + 4 skip invariati (GTK3). Unico fallimento pre-esistente e fuori scope: `tests/test_health.py::test_health_db_returns_live_count` (`backend/dev.db` vuoto in questo worktree — nessun file toccato da questo piano; vedi `deferred-items.md`)

## Self-Check: PASSED

Verificati con esito positivo:
- File creati: tutti i 12 file elencati in `key-files.created` esistono su disco
- Commit: `9dda591`, `6d00151`, `a1e0486` presenti in `git log --oneline`
- Suite: `uv run pytest tests/test_admin_listini.py tests/test_no_leak_admin.py` -> 23/23 passed
- Suite completa: `uv run pytest` -> 129 passed, 4 skipped, 1 failed (fuori scope, vedi sopra)

---
*Phase: 04-lead-pannello-admin*
*Completed: 2026-08-28*
