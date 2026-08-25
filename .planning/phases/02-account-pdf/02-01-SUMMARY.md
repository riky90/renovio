---
phase: 02-account-pdf
plan: 01
subsystem: infra
tags: [pydantic-settings, uv, argon2-cffi, authlib, itsdangerous, weasyprint, jinja2, aiosmtplib, react-router, config]

# Dependency graph
requires:
  - phase: 01-stima-free-end-to-end
    provides: backend FastAPI/SQLAlchemy scaffold con Settings esistente (DATABASE_URL, CORS_ORIGINS)
provides:
  - Dipendenze backend installate (argon2-cffi, authlib, itsdangerous, weasyprint, jinja2, aiosmtplib)
  - Dipendenza frontend installata (react-router)
  - Settings esteso con campi auth/sessione/OAuth/email/PDF/admin
  - backend/.env.example documentato con le nuove chiavi
affects: [02-02, 02-03, 02-04, 02-05, 02-06, 02-07]

# Tech tracking
tech-stack:
  added: [argon2-cffi 25.1.0, authlib 1.7.2, itsdangerous 2.2.0, weasyprint 69.0, jinja2 3.1.6, aiosmtplib 5.1.2, react-router]
  patterns: ["Settings pydantic-settings: default vuoto per segreti reali, mai hardcoded"]

key-files:
  created: []
  modified:
    - backend/app/config.py
    - backend/.env.example
    - backend/pyproject.toml
    - backend/uv.lock
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "Tutti i pacchetti [ASSUMED] da 02-RESEARCH.md approvati esplicitamente dall'utente ('approvato') prima dell'installazione"
  - "uv add --native-tls necessario per bypassare il proxy aziendale con certificato self-signed (stesso pattern gia' noto da Fase 1)"

patterns-established:
  - "Segreti (SECRET_KEY, OAUTH_SESSION_SECRET, SMTP_PASSWORD, GOOGLE_CLIENT_SECRET) sempre default vuoto in Settings, mai valori reali in .env.example"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, PDF-01]

# Metrics
duration: 12min
completed: 2026-08-25
---

# Phase 2 Plan 1: Setup dipendenze e configurazione Account & PDF Summary

**Installate le 6 dipendenze backend (argon2-cffi, authlib, itsdangerous, weasyprint, jinja2, aiosmtplib) + react-router frontend dopo gate di legittimita' pacchetti; `Settings` esteso con 11 nuovi campi (auth, sessione, OAuth Google, SMTP, frontend URL, admin) e `.env.example` documentato.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-25T11:41:24Z
- **Completed:** 2026-08-25T11:47:40Z
- **Tasks:** 2 (Task 1 gate pre-approvato dall'utente, Task 2 eseguito)
- **Files modified:** 6

## Accomplishments
- Gate di legittimita' pacchetti (Task 1, `checkpoint:human-verify` bloccante) risolto: utente ha approvato esplicitamente tutti e 7 i pacchetti [ASSUMED] (argon2-cffi, Authlib, itsdangerous, weasyprint, jinja2, aiosmtplib, react-router) prima dell'esecuzione di questo plan
- Dipendenze backend installate via `uv add --native-tls` (proxy aziendale bypassato)
- Dipendenza frontend `react-router` installata via `npm install`
- `Settings` (pydantic-settings) esteso con `SECRET_KEY`, `OAUTH_SESSION_SECRET`, `COOKIE_SECURE`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `FRONTEND_URL`, `ADMIN_EMAIL` — tutti i segreti con default vuoto
- `backend/.env.example` aggiornato con tutte le nuove chiavi commentate, nessun segreto reale

## Task Commits

Il gate (Task 1) e' stato pre-approvato dall'utente prima dello spawn di questo esecutore (non genera un commit di codice, solo l'approvazione registrata nel prompt di esecuzione).

1. **Task 2: Installazione dipendenze + estensione configurazione** - `7fabe8b` (feat)

**Plan metadata:** (commit successivo con SUMMARY.md/STATE.md/ROADMAP.md)

## Files Created/Modified
- `backend/app/config.py` - Settings esteso con campi auth/sessione/OAuth/email/PDF/admin
- `backend/.env.example` - documentazione delle nuove env var, nessun valore reale
- `backend/pyproject.toml` - aggiunte le 6 dipendenze backend
- `backend/uv.lock` - lockfile aggiornato
- `frontend/package.json` - aggiunta dipendenza react-router
- `frontend/package-lock.json` - lockfile aggiornato

## Decisions Made
- Gate pacchetti gia' pre-approvato dall'utente ("approvato") in sessione precedente allo spawn dell'esecutore per tutti e 7 i pacchetti [ASSUMED]; nessun ri-blocco eseguito, come da istruzione esplicita del chiamante
- `uv add --native-tls` usato fin da subito (stesso pattern gia' documentato in STATE.md da Fase 1) dopo il primo tentativo senza `--native-tls` fallito per certificato self-signed del proxy aziendale

## Deviations from Plan

None - plan eseguito esattamente come scritto (Task 1 gia' soddisfatto dall'approvazione utente pregressa, Task 2 eseguito senza scostamenti).

## Issues Encountered
- Primo tentativo `uv add` (senza `--native-tls`) fallito con `invalid peer certificate: UnknownIssuer` per il proxy aziendale — risolto ripetendo il comando con `--native-tls`, coerente con la nota gia' presente in STATE.md da Fase 1.

## User Setup Required

Nessuna azione utente aggiuntiva richiesta per questo plan (le variabili SMTP/Google OAuth elencate in `user_setup` del frontmatter del piano saranno necessarie nei plan successivi che le useranno effettivamente — es. Plan OAuth Google e Plan email reset password — non in questo plan di solo setup config).

## Next Phase Readiness
- `Settings` pronta per essere consumata dai prossimi plan (modelli `User`/`user_session`, router auth, servizio email, servizio PDF)
- `main.py` NON modificato in questo plan come da istruzione esplicita (il wiring middleware/router e' negli slice successivi)
- Nessun blocco noto per Plan 02-02

---
*Phase: 02-account-pdf*
*Completed: 2026-08-25*
