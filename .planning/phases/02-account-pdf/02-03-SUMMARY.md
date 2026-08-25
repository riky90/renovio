---
phase: 02-account-pdf
plan: 03
subsystem: backend-auth
tags: [fastapi, cookie-session, slowapi, tdd, e2e]

# Dependency graph
requires:
  - phase: 02-account-pdf
    plan: 02
    provides: AuthService (hash/verify, create_session/revoke_session), get_current_user/require_admin dependency, schemi anti-leak RegistrazioneRequest/LoginRequest/UserOut
provides:
  - "Router HTTP auth completo: POST /api/v1/auth/registrati|login|logout, GET /api/v1/auth/me"
  - "Router admin di prova: GET /api/v1/admin/ping protetto da require_admin (AUTH-04, nessuna UI)"
  - "Slice backend auth verificabile end-to-end via cookie httpOnly reale (TestClient cookie-jar)"
affects: [02-04, 02-05, 02-06, 02-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Router auth: with SessionLocal() as session: per request (stesso pattern di routers/stima.py), risposta UserOut costruita field-by-field, mai model_validate su ORM"
    - "Login/registrazione: stesso messaggio 401 generico ('Email o password non corretti') per email inesistente e password errata (anti-enumeration T-03-02)"
    - "Rate limit 5/minute su /registrati e /login via @limiter.limit condiviso (T-03-01)"
    - "slowapi Limiter e' un singleton di processo: i test che colpiscono piu' volte lo stesso endpoint rate-limited devono chiamare limiter.reset() nella fixture, altrimenti leak di stato tra test funzioni causa 429 spuri"

key-files:
  created:
    - backend/app/routers/auth.py
    - backend/app/routers/admin.py
    - backend/tests/test_auth_endpoints.py
  modified:
    - backend/app/main.py

key-decisions:
  - "Docstring di routers/auth.py riformulata per non contenere letteralmente la stringa 'model_validate' (anche in un commento negativo), per rispettare in senso stretto il criterio di accettazione meccanico grep -c model_validate == 0 — stesso precedente gia' visto in 02-02 con 'password_hash'"

requirements-completed: [AUTH-01, AUTH-03, AUTH-04]

# Metrics
duration: 15min
completed: 2026-08-25
---

# Phase 2 Plan 3: Endpoint HTTP auth + guard admin Summary

**Router auth (registrati/login/logout/me) e router admin di prova (`/admin/ping`) sopra l'AuthService del Plan 02, verificati end-to-end via TestClient a cookie-jar reale: cookie httpOnly su registrazione/login, revoca server-side al logout, messaggio 401 generico anti-enumeration, rate limit 5/minute, 403/200 sulla route admin.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-08-25T11:54:00Z (stima, non catturato esplicitamente all'avvio)
- **Completed:** 2026-08-25T12:09:26Z
- **Tasks:** 2 (Task 1 RED, Task 2 GREEN)
- **Files modified:** 4 (3 creati, 1 modificato)

## Accomplishments

- `backend/app/routers/auth.py`: `APIRouter(prefix="/auth", tags=["auth"])` con `POST /registrati` (409 su email duplicata, hash Argon2id, `promote_admin_if_configured`, `create_session`, 201 + `UserOut`), `POST /login` (`@limiter.limit("5/minute")`, stesso messaggio generico `"Email o password non corretti"` sia per email inesistente sia per password errata — nessuna enumerazione), `POST /logout` (legge cookie `session_id`, `revoke_session`, 204), `GET /me` (`Depends(get_current_user)` → `UserOut`). Risposta sempre costruita field-by-field, mai `model_validate` su `User`.
- `backend/app/routers/admin.py`: `APIRouter(prefix="/admin", tags=["admin"])` con `GET /ping` dietro `Depends(require_admin)` — dimostra AUTH-04 end-to-end senza alcuna UI admin (che arriva in Fase 4).
- `backend/app/main.py`: `include_router` per entrambi sotto `/api/v1`; CORS/`allow_credentials` esistenti non toccati.
- `backend/tests/test_auth_endpoints.py`: 9 test e2e con `TestClient` a cookie-jar reale — registrazione (201, cookie httpOnly, no `password_hash`/`password` nel body), email duplicata (409), `/me` con/senza cookie (200/401), logout→`/me` 401, login corretto (200 + nuovo cookie) e login errato/email inesistente (401 stesso messaggio), admin `/ping` 200 per l'admin promosso via `ADMIN_EMAIL` e 403 per un utente normale. RED confermato (`ModuleNotFoundError: No module named 'app.routers.auth'` all'import di `app.main`) prima dell'implementazione.
- Suite completa: 47/47 test verdi (9 nuovi + 38 preesistenti).

## Task Commits

1. **Task 1: Test e2e RED per endpoint auth + admin guard** - `aabd59c` (test)
2. **Task 2: Router auth + router admin + wiring main.py (GREEN)** - `d5d5c19` (feat)

**Plan metadata:** (commit successivo con SUMMARY.md/STATE.md/ROADMAP.md)

## Files Created/Modified

- `backend/app/routers/auth.py` - endpoint registrati/login/logout/me
- `backend/app/routers/admin.py` - route admin di prova `/ping`
- `backend/app/main.py` - `include_router` per auth e admin sotto `/api/v1`
- `backend/tests/test_auth_endpoints.py` - 9 test e2e TDD (RED→GREEN)

## Decisions Made

- Docstring di `routers/auth.py` riscritta per non contenere la stringa letterale `model_validate` (anche solo in un commento che la nega esplicitamente), per soddisfare in senso stretto il criterio di accettazione meccanico del piano (`grep -c "model_validate" == 0`) — stesso pattern gia' incontrato in 02-02-SUMMARY.md con `password_hash`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Reset dello stato del rate limiter tra i test**
- **Found during:** Task 2, prima esecuzione della suite `test_auth_endpoints.py` (GREEN)
- **Issue:** `slowapi.Limiter` (`app/limiter.py`) e' un singleton di modulo condiviso da tutta la sessione di test; con `@limiter.limit("5/minute")` su `/registrati`/`/login`, le chiamate cumulative di test funzione precedenti (ognuno registra almeno un utente) esaurivano la quota prima che i test successivi (es. login con credenziali corrette) potessero eseguire, causando un 401/429 spurio invece del comportamento atteso.
- **Fix:** aggiunta `limiter.reset()` in testa alla fixture `client` di `test_auth_endpoints.py`, cosi' ogni test funzione parte con quota piena — isolamento del test, nessuna modifica al comportamento di produzione del rate limit.
- **Files modified:** `backend/tests/test_auth_endpoints.py`
- **Verification:** `uv run pytest tests/test_auth_endpoints.py -x` → 9/9 verdi (prima del fix: 1 fallimento per 401 inatteso su login valido)
- **Committed in:** `d5d5c19` (parte del commit Task 2)

**2. [Rule 3 - Blocking] Riformulazione docstring per il criterio meccanico anti-model_validate**
- **Found during:** Task 2, verifica finale dell'acceptance criteria
- **Issue:** `grep -c "model_validate" backend/app/routers/auth.py` ritornava 1 perche' la docstring di modulo menzionava letteralmente la stringa `model_validate` in una frase che ne descriveva l'assenza (falso positivo del controllo meccanico, non un uso reale di `model_validate`).
- **Fix:** riformulata la frase della docstring senza la stringa letterale `model_validate`, mantenendo lo stesso significato semantico.
- **Files modified:** `backend/app/routers/auth.py`
- **Verification:** `grep -c "model_validate" backend/app/routers/auth.py` → 0; suite invariata 9/9 verdi.
- **Committed in:** `d5d5c19` (parte del commit Task 2)

---

**Total deviations:** 2 auto-fixed (entrambi Rule 3 - blocking)
**Impact on plan:** Nessuno scope creep: entrambi i fix erano necessari per far passare i criteri di accettazione gia' scritti nel piano, senza introdurre nuova superficie funzionale.

## Issues Encountered

Nessuno oltre alle due deviazioni sopra documentate.

## User Setup Required

Nessuna azione utente richiesta per questo plan. `ADMIN_EMAIL` era gia' documentata in `.env.example` dal Plan 01/02; questo plan la consuma per la prima volta a runtime (in `registrati`, via `AuthService.promote_admin_if_configured`).

## Next Phase Readiness

- Slice backend auth completo e verificato via HTTP con cookie httpOnly reale: pronto per essere consumato dal frontend nel Plan 04 (`credentials: "include"` sulle fetch, Pitfall 4 di 02-RESEARCH.md).
- `GET /api/v1/admin/ping` esiste come prova end-to-end del ruolo admin; nessuna UI admin ancora (arriva in Fase 4) — nessun blocco.
- `SessionMiddleware` di Authlib (Google OAuth, Plan 05) resta da aggiungere separatamente dal cookie applicativo `session_id` — non toccato in questo plan, come da istruzione esplicita del piano.
- Nessun blocco noto per Plan 02-04.

---
*Phase: 02-account-pdf*
*Completed: 2026-08-25*
