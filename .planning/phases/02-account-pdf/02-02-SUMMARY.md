---
phase: 02-account-pdf
plan: 02
subsystem: backend-auth
tags: [argon2id, session-cookie, sqlalchemy, alembic, tdd]

# Dependency graph
requires:
  - phase: 02-account-pdf
    plan: 01
    provides: Settings esteso (SECRET_KEY, COOKIE_SECURE, ADMIN_EMAIL, ecc.), dipendenze installate (argon2-cffi tra le altre)
provides:
  - Modelli ORM User/UserSession/PasswordResetToken + migrazione Alembic 0002
  - AuthService (hash/verify Argon2id, sessione DB-backed create/revoke, convergenza per-email, promozione admin)
  - Dependency get_current_user/require_admin riusabili da ogni router protetto
  - Schemi anti-leak RegistrazioneRequest/LoginRequest/UserOut
affects: [02-03, 02-04, 02-05, 02-06, 02-07]

# Tech tracking
tech-stack:
  added: [email-validator 2.3.0]
  patterns:
    - "Sessione applicativa opaca DB-backed (user_session.id = secrets.token_urlsafe(32) come PK), mai JWT — revoca server-side pulita via DELETE"
    - "password_hash marcato CAMPO SEGRETO nel docstring di modulo, stessa convenzione di coefficiente_impresa; mai in nessuno schema Pydantic"
    - "get_or_create_user_by_email per la convergenza D-05 (un solo account per email)"

key-files:
  created:
    - backend/app/models/user.py
    - backend/alembic/versions/0002_auth_tables.py
    - backend/app/schemas/auth.py
    - backend/app/services/auth_service.py
    - backend/app/dependencies/__init__.py
    - backend/app/dependencies/auth.py
    - backend/tests/test_auth_service.py
  modified:
    - backend/app/models/__init__.py
    - backend/pyproject.toml
    - backend/uv.lock

key-decisions:
  - "email-validator aggiunto via uv add --native-tls (richiesto da pydantic EmailStr, anticipato esplicitamente dal piano)"
  - "get_current_user/require_admin testati per chiamata diretta (non tramite TestClient) passando session_id/db/user come argomenti — coerente con la firma FastAPI Depends ma verificabile in isolamento"

requirements-completed: [AUTH-01, AUTH-03, AUTH-04]

# Metrics
duration: 4min
completed: 2026-08-25
---

# Phase 2 Plan 2: Fondazione backend autenticazione Summary

**Nucleo auth self-hosted: modelli User/UserSession/PasswordResetToken, migrazione Alembic 0002, AuthService con hashing Argon2id e sessione opaca DB-backed, dependency get_current_user/require_admin — TDD RED→GREEN, 12/12 test nuovi verdi, 38/38 suite totale verde.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-25T11:54:34Z
- **Completed:** 2026-08-25
- **Tasks:** 2 (Task 1 RED, Task 2 GREEN)
- **Files modified:** 9 (7 creati, 3 modificati — incluso pyproject.toml/uv.lock per email-validator)

## Accomplishments

- `backend/app/models/user.py`: `User` (email unique+index, `password_hash` nullable e marcato CAMPO SEGRETO, `role` default "user"), `UserSession` (PK = session_id opaco `secrets.token_urlsafe(32)`, `expires_at`, relationship a `User`), `PasswordResetToken` (tabella minima predisposta per il Plan 06). Registrati in `models/__init__.py`.
- `backend/alembic/versions/0002_auth_tables.py`: migrazione con `down_revision="0001"`, `op.create_table` esplicito per `user`/`user_session`/`password_reset_token` (UniqueConstraint su email, ForeignKeyConstraint su user_id, indici su email/user_id), `downgrade()` in ordine FK inverso. Verificata upgrade/downgrade/upgrade su SQLite dev.
- `backend/app/schemas/auth.py`: `RegistrazioneRequest` (email/password min 8/nome), `LoginRequest`, `UserOut` (id/email/nome/role/created_at — MAI il campo password) — stesso pattern a campi chiusi di `schemas/stima.py`.
- `backend/app/services/auth_service.py` (classe `AuthService`, `@staticmethod`): `hash_password`/`verify_password` (Argon2id via `argon2-cffi`, gestione `VerifyMismatchError`), `create_session` (nuovo id ad ogni login — mitigazione session fixation T-02-07 — cookie httponly/samesite=lax/secure=settings.COOKIE_SECURE/max_age 30gg), `revoke_session` (DELETE riga + `delete_cookie`), `get_or_create_user_by_email` (convergenza D-05), `promote_admin_if_configured` (D-03, `ADMIN_EMAIL`).
- `backend/app/dependencies/auth.py`: `get_db` (context manager su `SessionLocal`, import da `app.db` non `app.main` per evitare import circolare — pattern `limiter.py`), `get_current_user` (Cookie `session_id` → lookup `UserSession` con controllo scadenza timezone-safe → `User`, altrimenti 401), `require_admin` (403 se `role != "admin"`).
- `backend/tests/test_auth_service.py`: 12 test unitari (hashing, ciclo di vita sessione incluso scadenza esplicita, revoca/logout, admin guard, convergenza email no-duplicati, anti-leak ricorsivo di `UserOut`) — RED confermato (ModuleNotFoundError) prima dell'implementazione, GREEN dopo.
- Aggiunta dipendenza `email-validator` (richiesta da `pydantic.EmailStr`, anticipata dal piano) via `uv add --native-tls`.

## Task Commits

1. **Task 1: Test RED per auth_service/require_admin** - `0b1ae24` (test)
2. **Task 2: Modelli/migrazione/schemi/servizio/dependency (GREEN)** - `f5578e2` (feat)

**Plan metadata:** (commit successivo con SUMMARY.md/STATE.md/ROADMAP.md)

## TDD Gate Compliance

RED gate: commit `0b1ae24` (`test(...)`), confermato fallire per `ModuleNotFoundError: No module named 'app.services.auth_service'` prima di scrivere qualunque implementazione.
GREEN gate: commit `f5578e2` (`feat(...)`), 12/12 test del file verdi al primo tentativo di implementazione, nessun REFACTOR necessario (nessun commit `refactor(...)`).

## Files Created/Modified

- `backend/app/models/user.py` - ORM `User`/`UserSession`/`PasswordResetToken`
- `backend/app/models/__init__.py` - registrazione nuovi modelli su `Base.metadata`
- `backend/alembic/versions/0002_auth_tables.py` - migrazione tabelle auth
- `backend/app/schemas/auth.py` - schemi anti-leak registrazione/login/UserOut
- `backend/app/services/auth_service.py` - hashing, sessione, convergenza, promozione admin
- `backend/app/dependencies/__init__.py` - nuovo package
- `backend/app/dependencies/auth.py` - `get_db`, `get_current_user`, `require_admin`
- `backend/tests/test_auth_service.py` - 12 test unitari TDD
- `backend/pyproject.toml`, `backend/uv.lock` - dipendenza `email-validator` aggiunta

## Decisions Made

- `email-validator` installato con `uv add --native-tls` (proxy aziendale, stesso pattern gia' noto da Fase 1/Plan 02-01) — necessario perche' `pydantic.EmailStr` lo richiede a runtime; anticipato esplicitamente dal testo del piano ("Se EmailStr richiede email-validator, aggiungilo con uv"), non e' quindi trattato come deviazione ma come esecuzione diretta dell'istruzione del piano.
- Nel test RED/GREEN, `get_current_user`/`require_admin` sono invocate direttamente con argomenti keyword (`session_id=`, `db=`, `user=`) invece che tramite `TestClient` — verifica la logica di dominio in isolamento, coerente con l'ambito "unit test" del Task 1; la verifica end-to-end via cookie HTTP reale e CORS/`credentials:"include"` e' delegata al Plan 03 (wiring router).

## Deviations from Plan

None - plan eseguito esattamente come scritto. L'unica azione non esplicitamente scritta come task ma anticipata nel testo del piano (`email-validator`) e' stata eseguita come indicato.

## Issues Encountered

Nessuno. La docstring iniziale di `schemas/auth.py` conteneva letteralmente la stringa `password_hash` in un commento — corretta con un fraseggio equivalente prima del commit per rispettare rigorosamente il criterio di accettazione automatizzato (`grep -rc "password_hash" app/schemas/` deve restituire 0 in senso stretto, incluso nei commenti, per essere una garanzia meccanica e non solo semantica).

## User Setup Required

Nessuna azione utente richiesta per questo plan. `ADMIN_EMAIL`/`SECRET_KEY`/`COOKIE_SECURE` sono gia' in `.env.example` dal Plan 01; verranno effettivamente lette a runtime a partire dal wiring endpoint (Plan 03).

## Next Phase Readiness

- `AuthService` e le dependency `get_current_user`/`require_admin` sono pronte per essere consumate dal router `auth.py` (registrazione/login/logout) nel Plan 03.
- La tabella `user_session` e il cookie `session_id` sono la base anche per il flusso Google OAuth (Plan 05, Pattern 2 RESEARCH) — da tenere ben distinto dal cookie `SessionMiddleware` di Authlib.
- `PasswordResetToken` esiste gia' a livello di schema/migrazione; la logica del flusso reset arriva nel Plan 06.
- Nessun blocco noto per Plan 02-03.

---
*Phase: 02-account-pdf*
*Completed: 2026-08-25*

## Self-Check: PASSED
All claimed files and commits verified present on disk / in git log.
