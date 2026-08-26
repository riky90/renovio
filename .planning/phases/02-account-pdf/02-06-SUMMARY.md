---
phase: 02-account-pdf
plan: 06
subsystem: auth-backend-frontend
tags: [itsdangerous, aiosmtplib, password-reset, tdd, react-router]

# Dependency graph
requires:
  - phase: 02-account-pdf
    plan: 02
    provides: "Modello PasswordResetToken (tabella minima, migrazione 0002), AuthService.hash_password"
  - phase: 02-account-pdf
    plan: 03
    provides: "Router auth.py (registrati/login/logout/me), pattern with SessionLocal per request, limiter condiviso"
  - phase: 02-account-pdf
    plan: 04
    provides: "api/auth.ts, App.tsx (react-router), AccediPage con link 'Password dimenticata?' gia' presente"
provides:
  - "backend/app/services/reset_token.py: make_reset_token/read_reset_token (itsdangerous, firma+scadenza 1h)"
  - "backend/app/services/email_service.py: send_email() astrazione SMTP async, dev log-only fallback"
  - "POST /api/v1/auth/password-dimenticata e POST /api/v1/auth/reimposta-password"
  - "frontend/src/routes/PasswordDimenticataPage.tsx e ReimpostaPasswordPage.tsx"
affects: [04-lead-admin]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "reset_token.py costruisce l'URLSafeTimedSerializer per-call (non a livello modulo) cosi' i test possono esercitare valori diversi di settings.SECRET_KEY senza problemi di caching all'import"
    - "PasswordResetToken.token_hash salva sha256(token), mai il token in chiaro nel DB — stesso principio difensivo di password_hash"
    - "email_service.send_email logga il contenuto invece di fallire quando SMTP_HOST e' vuoto (dev fallback esplicito, mai un'eccezione a import/startup)"

key-files:
  created:
    - backend/app/services/email_service.py
    - backend/app/services/reset_token.py
    - backend/tests/test_password_reset.py
    - frontend/src/routes/PasswordDimenticataPage.tsx
    - frontend/src/routes/ReimpostaPasswordPage.tsx
  modified:
    - backend/app/routers/auth.py
    - backend/app/schemas/auth.py
    - frontend/src/api/auth.ts
    - frontend/src/App.tsx
    - frontend/src/routes/AccediPage.tsx

key-decisions:
  - "reset_token firmato con settings.SECRET_KEY (non OAUTH_SESSION_SECRET), salt dedicato 'password-reset' (02-RESEARCH.md Code Examples)"
  - "PasswordResetToken.token_hash = sha256(token) invece del token in chiaro, per difesa in profondita' su un eventuale leak del DB"
  - "AccediPage.tsx modificata (non nei files_modified del piano) per mostrare la conferma inline richiesta esplicitamente dal testo del task 2 dopo un reset riuscito"

requirements-completed: [AUTH-01]

# Metrics
duration: 25min
completed: 2026-08-26
---

# Phase 2 Plan 6: Recupero password via email Summary

**Reset password end-to-end (D-04): token firmato itsdangerous a scadenza 1h e uso singolo, email transazionale astratta (log-only in dev, aiosmtplib in prod), endpoint anti-enumeration `/auth/password-dimenticata`/`/auth/reimposta-password`, e le due pagine frontend `/password-dimenticata`/`/reimposta-password` — TDD RED→GREEN, 66/66 suite backend verde.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-26 (ripresa dopo interruzione per limite settimanale; file di test RED iniziale gia' scritto in precedenza ma spostato fuori dal path — ricreato da zero come da istruzione del coordinatore)
- **Completed:** 2026-08-26
- **Tasks:** 2 (Task 1 RED+GREEN backend, Task 2 frontend)
- **Files modified:** 10 (7 creati, 3 modificati — esclusi STATE/ROADMAP)

## Accomplishments

- `backend/app/services/reset_token.py`: `make_reset_token(user_id)`/`read_reset_token(token, max_age_seconds=3600)` su `itsdangerous.URLSafeTimedSerializer(settings.SECRET_KEY, salt="password-reset")` — token valido a un `user_id`, scaduto (`SignatureExpired`) o manomesso (`BadSignature`) a `None` senza distinzione osservabile.
- `backend/app/services/email_service.py`: `send_email(to, subject, html_body)` async via `aiosmtplib`, con fallback esplicito (log, non eccezione) quando `SMTP_HOST` e' vuoto — mai un errore a import/startup, riusabile in Fase 4 per i lead senza refactor.
- `backend/app/routers/auth.py`: `POST /password-dimenticata` (`@limiter.limit("5/minute")`, con o senza utente esistente ritorna **sempre** lo stesso 200/`{"detail": ...}` — T-06-01) e `POST /reimposta-password` (`read_reset_token` -> user_id, lookup riga `PasswordResetToken` per `token_hash` (sha256 del token) + `used=False` + `expires_at` non scaduto, altrimenti 400 generico "Il link non e' piu' valido"; su successo aggiorna `password_hash` e marca `used=True`, impedendo il replay anche entro la scadenza — T-06-03).
- `backend/app/schemas/auth.py`: `PasswordDimenticataRequest`/`ReimpostaPasswordRequest` (password `Field(min_length=8)`, stesso pattern a campi chiusi del resto del modulo).
- `backend/tests/test_password_reset.py`: 8 test — unit su `reset_token` (valido/scaduto/manomesso, quest'ultimi due senza sleep grazie a `max_age_seconds=-1`), anti-enumeration (stessa risposta byte-per-byte per email esistente/inesistente, verificato anche che l'email parta solo per l'utente reale), flusso completo (token valido -> nuova password -> vecchia password rifiutata al login, nuova accettata), replay (secondo uso -> 400), token invalido (400), password troppo corta (422). `send_email` e' monkeypatchato sul modulo router per catturare il link/token senza mai tentare una consegna SMTP reale.
- `frontend/src/api/auth.ts`: `postPasswordDimenticata`/`postReimpostaPassword` (stesso pattern `apiPost` con `credentials:"include"`).
- `frontend/src/routes/PasswordDimenticataPage.tsx`: form Email -> CTA "Invia link di reset"; su submit il form viene **sempre** sostituito dalla conferma amber, indipendentemente dalla risposta del backend (che e' comunque sempre 200).
- `frontend/src/routes/ReimpostaPasswordPage.tsx`: legge `token` dai query param; se assente mostra subito l'alert destructive "Il link non e' piu' valido..." con link a `/password-dimenticata` (nessun form renderizzato, nessun tentativo di submit su un link gia' morto); altrimenti form "Nuova password" (`input-group` con toggle mostra/nascondi via `lucide-react` Eye/EyeOff) + CTA "Imposta nuova password"; su 400 dal backend (token scaduto/gia' usato) mostra lo stesso messaggio destructive; su successo redirect a `/accedi?password_reimpostata=1`.
- `frontend/src/App.tsx`: rotte `/password-dimenticata` e `/reimposta-password` registrate.
- `frontend/src/routes/AccediPage.tsx`: nuovo alert amber "Password reimpostata. Accedi con la nuova password." quando arriva da `?password_reimpostata=1` (vedi Deviazioni).

## Task Commits

1. **Task 1a: Test RED per reset password** - `4f95a61` (test)
2. **Task 1b: email_service/reset_token/endpoint reset (GREEN)** - `d189d6d` (feat)
3. **Task 2: Pagine frontend password-dimenticata/reimposta-password** - `45ed014` (feat)

**Plan metadata:** (commit successivo con SUMMARY.md/STATE.md/ROADMAP.md)

## TDD Gate Compliance

RED gate: commit `4f95a61` (`test(...)`), confermato fallire con `ModuleNotFoundError: No module named 'app.services.reset_token'` prima di scrivere qualunque implementazione (verificato con `uv run pytest tests/test_password_reset.py -x`).
GREEN gate: commit `d189d6d` (`feat(...)`), 8/8 test del file verdi al primo tentativo di implementazione; suite completa 66/66 verde (58 preesistenti + 8 nuovi), 2 skip invariati (WeasyPrint/GTK3, non correlati a questo piano). Nessun REFACTOR necessario (nessun commit `refactor(...)`).

## Files Created/Modified

- `backend/app/services/reset_token.py` - make/read token itsdangerous
- `backend/app/services/email_service.py` - invio email transazionale astratto
- `backend/app/routers/auth.py` - endpoint password-dimenticata/reimposta-password
- `backend/app/schemas/auth.py` - PasswordDimenticataRequest/ReimpostaPasswordRequest
- `backend/tests/test_password_reset.py` - 8 test TDD (unit token + e2e endpoint)
- `frontend/src/api/auth.ts` - client API reset password
- `frontend/src/routes/PasswordDimenticataPage.tsx` - schermata richiesta reset
- `frontend/src/routes/ReimpostaPasswordPage.tsx` - schermata conferma reset
- `frontend/src/App.tsx` - rotte registrate
- `frontend/src/routes/AccediPage.tsx` - conferma inline post-reset

## Decisions Made

- Token firmato con `settings.SECRET_KEY` (non `OAUTH_SESSION_SECRET`, riservato al `SessionMiddleware` OAuth — 02-RESEARCH.md Pitfall 1), come esplicitamente richiesto dal piano.
- `PasswordResetToken.token_hash` memorizza `sha256(token)` invece del token in chiaro — difesa in profondita' coerente con la convenzione "CAMPO SEGRETO" gia' usata per `password_hash`.
- `AccediPage.tsx` modificata pur non essendo tra i `files_modified` dichiarati dal piano: il testo del Task 2 richiede esplicitamente "su successo redirect a `/accedi` con messaggio inline di conferma", non implementabile senza toccare la pagina di destinazione (Rule 2 — funzionalita' critica richiesta dal piano stesso, non un'aggiunta arbitraria).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] AccediPage.tsx non elencata nei files_modified ma necessaria per il messaggio inline di conferma richiesto dal piano**
- **Found during:** Task 2, implementazione del redirect post-reset
- **Issue:** Il piano richiede esplicitamente "su successo redirect a `/accedi` con messaggio inline di conferma", ma `AccediPage.tsx` non compare tra i file da modificare in frontmatter — senza toccarla, il redirect non potrebbe mostrare alcuna conferma.
- **Fix:** Aggiunto un flag `?password_reimpostata=1` al redirect e un alert amber condizionale in `AccediPage.tsx`.
- **Files modified:** `frontend/src/routes/ReimpostaPasswordPage.tsx`, `frontend/src/routes/AccediPage.tsx`
- **Verification:** `npx tsc --noEmit` pulito; revisione logica del flusso (redirect -> query param -> alert).
- **Committed in:** `45ed014` (parte del commit Task 2)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical, richiesta esplicitamente dal testo del piano)
**Impact on plan:** Nessuno scope creep: il fix era necessario per soddisfare un requisito gia' scritto nel testo del piano, non un'aggiunta arbitraria.

## Issues Encountered

Il file di test iniziale (`backend/tests/test_password_reset.py`) scritto nella sessione precedente all'interruzione per limite settimanale importava un modulo (`app.services.reset_token`) non ancora esistente, bloccando la collection dell'intera suite pytest (`ERROR collecting`, non un semplice fallimento di un singolo test). E' stato rimosso dal coordinatore prima della ripresa e ricreato identico nel contenuto come primo passo di questa sessione, seguendo normalmente il ciclo RED (confermato fallire con `ModuleNotFoundError`) -> GREEN di questo piano.

## User Setup Required

Nessuna azione utente richiesta. `SMTP_HOST/PORT/USER/PASSWORD/FROM` sono gia' in `.env.example` dal Plan 01; in dev restano vuoti e il fallback log-only di `email_service.py` rende il flusso completamente testabile/usabile senza configurazione SMTP reale. Per verificare l'invio reale in futuro (Fase 4, lead), basta valorizzare le variabili SMTP_* in `.env` — nessuna modifica di codice necessaria.

## Next Phase Readiness

- Il ciclo di gestione credenziali (AUTH-01) e' ora completo: registrazione, login, logout, sessione, **e recupero password**.
- `email_service.send_email` e' pronto per essere riusato tal quale dalla Fase 4 (notifica lead) — stessa firma `(to, subject, html_body)`, nessun refactor previsto.
- Rimane aperto **02-04 Task 3** (checkpoint `human-verify` sul flusso login/logout in browser) come gia' segnalato nelle sessioni precedenti — indipendente da questo piano, non bloccante per il resto della Fase 2.
- Rimane da eseguire **02-09** (ultimo piano dichiarato aperto in Fase 2 su STATE.md prima di questa sessione).

---
*Phase: 02-account-pdf*
*Completed: 2026-08-26*

## Self-Check: PASSED
Tutti i file dichiarati e i commit dichiarati (`4f95a61`, `d189d6d`, `45ed014`) verificati presenti su disco / in git log (vedi self-check successivo).
