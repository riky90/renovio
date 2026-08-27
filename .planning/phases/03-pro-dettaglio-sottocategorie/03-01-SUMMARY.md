---
phase: 03-pro-dettaglio-sottocategorie
plan: 01
subsystem: auth
tags: [fastapi, sqlalchemy, alembic, pydantic, paywall, subscription]

# Dependency graph
requires:
  - phase: 02-account-pdf
    provides: get_current_user/require_admin, cookie httpOnly, UserOut a campi chiusi, migrazioni 0001-0003
provides:
  - Modello Subscription (tessera Pro) + migrazione 0004 reversibile
  - require_pro dependency (401 anonimo / 403 non-Pro) + subscription_is_active helper
  - POST /me/pro/attiva (stub utente, rate-limited, idempotente) + POST /admin/pro/attiva (manuale)
  - UserOut.pro popolato su /auth/me
affects: [03-02, 03-03, 03-04, 03-05, 03-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "require_pro mirror di require_admin: stessa dependency chain get_current_user -> role/subscription check"
    - "subscription_is_active centralizza il guard naive/aware datetime, riusato sia da require_pro sia da UserOut.pro"
    - "upsert idempotente per user_id (stesso idioma .filter_by().one_or_none() di scripts/seed.py)"

key-files:
  created:
    - backend/app/models/subscription.py
    - backend/alembic/versions/0004_subscription.py
    - backend/app/schemas/subscription.py
    - backend/app/routers/subscription.py
    - backend/tests/test_subscription.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/dependencies/auth.py
    - backend/app/schemas/auth.py
    - backend/app/routers/auth.py
    - backend/app/main.py
    - backend/tests/test_auth_service.py

key-decisions:
  - "Nessuna colonna prezzo/coefficiente impresa sul modello Subscription (D-10): la tessera riguarda solo stato abbonamento"
  - "piano_code nullable aggiunto ora (Open Question 3 del RESEARCH, D-07 production-shaped) a costo quasi zero"
  - "UserOut.pro esposto tra role e created_at, mai scrivibile dal client, sempre derivato da subscription_is_active"

patterns-established:
  - "Pattern require_pro: 401->403 layering identico a require_admin, riusabile da tutte le rotte Pro delle fasi 03-05/03-06"
  - "Attivazione Pro come upsert idempotente per user_id: stub oggi, stesso endpoint accendera' il pagamento reale in futuro (D-07)"

requirements-completed: [PRO-02, PRO-03]

# Metrics
duration: 13min
completed: 2026-08-27
---

# Phase 3 Plan 1: Stato Pro (tessera abbonamento) + paywall server-side Summary

**Modello Subscription (tessera stato+scadenza), dependency require_pro (401/403) e endpoint di attivazione stub+admin, con UserOut.pro riflesso su /auth/me — fondamenta paywall per tutte le rotte Pro delle fasi successive.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-08-27T06:09:00Z
- **Completed:** 2026-08-27T06:22:16Z
- **Tasks:** 3 completati
- **Files modified:** 11 (5 creati, 6 modificati)

## Accomplishments
- Tabella `subscription` migrabile in entrambe le direzioni (migrazione 0004, catena 0001→0004), nessuna colonna prezzo/margine impresa
- `require_pro` + `subscription_is_active`: gate server-side completo (401 anonimo, 403 Free, attivo se `stato="attivo"` e `scaduta_il` None o futura)
- Flusso attivazione end-to-end: `POST /me/pro/attiva` (stub production-shaped, idempotente, rate-limited 10/minute) + `POST /admin/pro/attiva` (manuale, dietro `require_admin`)
- `UserOut.pro` popolato in `_to_user_out` per registrati/login/me; suite backend completa 82/82 passed + 2 skip (invariati, GTK3)

## Task Commits

Ogni task e' stato committato atomicamente:

1. **Task 1: Modello Subscription + migrazione 0004 + guardrail reseed** - `e18b1db` (feat)
2. **Task 2: require_pro + subscription_is_active + UserOut.pro** - `66ddd59` (feat)
3. **Task 3: Endpoint attivazione (stub utente + admin) + wiring + UserOut.pro popolato** - `d17dc01` (feat)

_Nota: piano `tdd="true"` per task, ma senza gate RED/GREEN separati per commit — ogni task include model/logica + test nello stesso commit, tutti verdi al momento del commit (stesso stile dei piani precedenti di questa fase 02, es. 02-07)._

## Files Created/Modified
- `backend/app/models/subscription.py` - `Subscription` (stato/scaduta_il/piano_code), nessun campo impresa
- `backend/alembic/versions/0004_subscription.py` - migrazione tabella subscription, down_revision 0003
- `backend/app/models/__init__.py` - registrato `Subscription` per il metadata Alembic/create_all
- `backend/app/dependencies/auth.py` - `require_pro` + `subscription_is_active`
- `backend/app/schemas/subscription.py` - `SubscriptionOut`/`AttivaProResponse` a campi chiusi
- `backend/app/schemas/auth.py` - `UserOut.pro: bool`
- `backend/app/routers/subscription.py` - `POST /me/pro/attiva` + `POST /admin/pro/attiva`
- `backend/app/routers/auth.py` - `_to_user_out` ora prende `session` e popola `pro`
- `backend/app/main.py` - router `subscription` registrato
- `backend/tests/test_subscription.py` - 16 test (modello, subscription_is_active, require_pro, endpoint end-to-end, anti-leak)
- `backend/tests/test_auth_service.py` - aggiornato per il nuovo campo obbligatorio `pro` su `UserOut`

## Decisions Made
- Nessuna colonna prezzo/coefficiente impresa sul modello `Subscription` (D-10): la tessera Pro e' puro stato abbonamento, niente da leakare a livello di schema
- `piano_code` nullable aggiunto gia' ora, a costo pressoche' nullo, coerente con la filosofia "production-shaped" (D-07)
- Docstring di `schemas/subscription.py` riformulata per non contenere letteralmente la stringa "coefficiente" (stesso precedente di 02-account-pdf per rispettare in senso stretto il criterio grep meccanico)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Aggiornato test_auth_service.py per il nuovo campo obbligatorio UserOut.pro**
- **Found during:** Task 2 (estensione di `UserOut` con `pro: bool`)
- **Issue:** `test_user_out_never_contains_password_hash` costruiva `UserOut(...)` senza il nuovo campo obbligatorio `pro`, causando un errore di validazione Pydantic
- **Fix:** Aggiunto `pro=False` alla costruzione esplicita del DTO nel test
- **Files modified:** `backend/tests/test_auth_service.py`
- **Verification:** `uv run pytest` — 82/82 passed + 2 skipped
- **Committed in:** `d17dc01` (Task 3 commit, insieme al wiring che rende il campo effettivamente popolato)

---

**Total deviations:** 1 auto-fixed (1 bug fix di compatibilita' test)
**Impact on plan:** Nessuno scope creep; correzione diretta necessaria per non lasciare la suite rotta tra Task 2 e Task 3 dello stesso piano.

## Issues Encountered
None.

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta (nessuna nuova dipendenza, stub payment senza integrazione reale).

## Next Phase Readiness

- `require_pro` e `Subscription` pronti per essere usati dagli endpoint di dettaglio Pro (03-02/03-03) e dal PDF Pro (03-05/03-06)
- Guardrail D-12 rispettato: dopo il ciclo upgrade/downgrade/upgrade della migrazione 0004, `scripts/seed.py` e' stato rieseguito — il listino RE di default resta presente
- Nessun blocco noto per il prossimo plan di questa fase (03-02, motore parametrico Pro)

---
*Phase: 03-pro-dettaglio-sottocategorie*
*Completed: 2026-08-27*

## Self-Check: PASSED

All created files and commit hashes verified present on disk / in git log.
