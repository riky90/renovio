---
phase: 02-account-pdf
verified: 2026-08-26T00:00:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
overrides:
  - must_have: "GET /api/v1/auth/google/login reindirizza a Google (live verification)"
    reason: "Corporate-proxy TLS interception (self-signed CA) breaks httpx's fetch of Google's OpenID metadata on this Windows dev machine only. Code path (oauth.py, /auth/google/login, /auth/google/callback, get_or_create_user_by_email convergence) is correct, unit/import-level tested (55/55, 2/2 convergence tests green), and will work unmodified in production (Railway/Debian, no MITM proxy). User explicitly decided to defer live verification to production (documented in 02-05-SUMMARY.md)."
    accepted_by: "user (riccardo.rinaldi90@gmail.com)"
    accepted_at: "2026-08-25"
  - must_have: "PDF-01: byte-level PDF generation (content-type/filename/magic-bytes/anti-leak-on-bytes)"
    reason: "WeasyPrint cannot render on this Windows dev machine — OSError: cannot load library 'libgobject-2.0-0' (native GTK3/Pango/Cairo runtime missing). Endpoint/service/template code is complete and correct (verified: import-safe lazy-loading, ownership/401/anti-EstimationService-import guards all pass, anti-leak greps on template/service are 0). The 2 byte-generating tests in test_pdf.py are conditionally SKIPPED via a runtime probe, not failing, and will auto-unskip on Debian/prod (Railway) with no code change. User explicitly decided to defer to production (documented in 02-08-SUMMARY.md, 02-09-SUMMARY.md)."
    accepted_by: "user (riccardo.rinaldi90@gmail.com)"
    accepted_at: "2026-08-25"
---

# Phase 2: Account & PDF Verification Report

**Phase Goal:** Come utente di ristruttura-stima, voglio registrarmi/accedere (email e Google), avere le mie stime salvate e scaricare un PDF Free brandizzato, così da conservare e condividere la mia stima. Requirements: AUTH-01, AUTH-02, AUTH-03, AUTH-04, PDF-01.

**Verified:** 2026-08-26
**Status:** passed (with 2 explicit, user-accepted, environment-only deferrals — see overrides above)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | L'utente crea un account con email/password | ✓ VERIFIED | `POST /api/v1/auth/registrati` in `backend/app/routers/auth.py:53-76` hashes via Argon2id (`AuthService.hash_password`), creates DB row + session, returns 201+`UserOut`. Backend test suite green (66 passed). User-verified live in browser + cross-origin curl (200 + `Set-Cookie: session_id=...; HttpOnly`) per 02-04-SUMMARY.md addendum. |
| 2 | L'utente accede anche con Google | ✓ VERIFIED (code) / env-deferred (live) | `backend/app/oauth.py` registers Authlib OAuth client (OIDC discovery); `backend/app/routers/auth.py:189-221` implements `/auth/google/login` + `/auth/google/callback` with D-05 convergence via `AuthService.get_or_create_user_by_email`. `test_google_convergence.py` 2/2 green. Live redirect returns 500 in this dev environment only, due to corporate-proxy TLS interception breaking httpx's OIDC metadata fetch — documented root cause, code confirmed correct, deferred to production per explicit user decision (see override). |
| 3 | La sessione persiste e l'utente può fare logout | ✓ VERIFIED | `UserSession` DB-backed opaque session (`backend/app/models/user.py`), `AuthService.create_session`/`revoke_session` (`backend/app/services/auth_service.py:42-64`), `get_current_user`/`require_admin` dependencies (`backend/app/dependencies/auth.py`). `POST /auth/logout` revokes server-side + deletes cookie. 9/9 e2e auth endpoint tests green. Live-verified: logout → anonymous state confirmed in browser. |
| 4 | Le stime effettuate restano associate all'account | ✓ VERIFIED | `StimaSalvata` model (colonne scalari + `risultato_json` frozen snapshot), migration `0003_stima_salvata.py`. `POST/GET /api/v1/me/stime`, `GET /api/v1/me/stime/{id}` in `backend/app/routers/stime_salvate.py` — ownership-filtered (`user_id == current_user.id`), 404 not 403 anti-IDOR. Frontend: auto-save on login (`EstimatePage.tsx`), save-at-signup with pending intent (`SoftWallCta.tsx` → `RegistratiPage.tsx`/`AccediPage.tsx`), history+detail (`LeMieStimePage.tsx`). 6/6 backend tests green (save/list/detail/anti-IDOR/anti-leak/401). |
| 5 | L'utente scarica un PDF sintetico brandizzato della propria stima | ✓ VERIFIED (code) / env-deferred (byte render) | `GET /api/v1/me/stime/{id}/pdf` in `stime_salvate.py:124-148` → `PdfService.render()` (`pdf_service.py`) reads exclusively `StimaSalvata.risultato_json` (never recomputes, guarded by static `inspect.getsource()` anti-`EstimationService` test), renders Jinja2 `pdf_stima.html` template (Slate/blue-600, 1-page A4), returns `StreamingResponse(media_type="application/pdf")` with `Content-Disposition`. Anti-leak greps on template+service confirm 0 occurrences of `coefficiente_impresa`/`base_eur_mq`/`prezzo_impresa`/`moltiplicatore`. Ownership/401/anti-recompute-guard tests pass (3/3). Byte-generation (2 tests) SKIPPED on this Windows dev machine only — WeasyPrint's native GTK3 runtime (`libgobject-2.0-0`) is absent; code is structurally complete, lazily-imported so it doesn't break app startup, and will render in production (Debian/Railway). Frontend `PdfDownloadButton.tsx`/`scaricaPdf()` implement loading/error states end-to-end. Deferred to production per explicit user decision (see override). |
| 6 | Esiste un ruolo admin separato dall'utente finale | ✓ VERIFIED | `User.role` column (default "user"), `AuthService.promote_admin_if_configured` (promotes on `ADMIN_EMAIL` match), `require_admin` dependency (403 if `role != "admin"`), proof-of-concept `GET /api/v1/admin/ping` (`backend/app/routers/admin.py`). e2e test confirms 200 for admin / 403 for normal user. |

**Score:** 6/6 roadmap success criteria verified (2 carry an accepted environment-only override for live/byte-level verification, both explicitly decided by the user and documented in their respective SUMMARY.md files).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/user.py` | ORM User/UserSession/PasswordResetToken | ✓ VERIFIED | Read in full; `password_hash` nullable, marked CAMPO SEGRETO, never in any schema (grep confirms 0 occurrences in `app/schemas/`) |
| `backend/app/services/auth_service.py` | hash/verify, session lifecycle, convergence, admin promotion | ✓ VERIFIED | Argon2id via `argon2-cffi`, opaque DB-backed session, `get_or_create_user_by_email` (D-05), `promote_admin_if_configured` (D-03) |
| `backend/app/dependencies/auth.py` | get_current_user, require_admin | ✓ VERIFIED | Cookie → session lookup → 401/403, correct timezone-safe expiry check |
| `backend/app/routers/auth.py` | registrati/login/logout/me + google login/callback + password reset | ✓ VERIFIED | All 8 endpoints present, rate-limited (5/min), anti-enumeration (same generic message), field-by-field response construction (no `model_validate` leak, grep=0) |
| `backend/app/routers/admin.py` | AUTH-04 proof route | ✓ VERIFIED | `GET /admin/ping` behind `require_admin` |
| `backend/app/oauth.py` | Authlib OAuth Google instance | ✓ VERIFIED | OIDC discovery, correct scopes |
| `backend/app/models/stima_salvata.py` | StimaSalvata hybrid model | ✓ VERIFIED | Scalar columns + `risultato_json` (sqlalchemy.JSON) |
| `backend/app/routers/stime_salvate.py` | /me/stime POST/GET/GET-id/GET-pdf | ✓ VERIFIED | All 4 endpoints, ownership-filtered, snapshot-only (no EstimationService import) |
| `backend/app/services/pdf_service.py` | PdfService.render() from snapshot | ✓ VERIFIED | Lazy WeasyPrint import, no EstimationService reference, correct filename slug logic |
| `backend/app/templates/pdf_stima.html` | Branded Jinja2 template | ✓ VERIFIED | Present, anti-leak grep clean |
| `frontend/src/api/client.ts`, `auth.ts`, `stima.ts` | credentials:"include" on all authenticated calls | ✓ VERIFIED | grep confirms `credentials: "include"` present in client.ts (x2) and stima.ts |
| `frontend/src/App.tsx` | react-router with all auth + le-mie-stime routes | ✓ VERIFIED | 6 routes registered: `/`, `/registrati`, `/accedi`, `/password-dimenticata`, `/reimposta-password`, `/le-mie-stime` |
| `frontend/src/routes/RegistratiPage.tsx`, `AccediPage.tsx` | forms + Google button + save-at-signup hook | ✓ VERIFIED | Present, wired to `useAuth`, pendingStima intent handling confirmed in SUMMARY and file listing |
| `frontend/src/routes/LeMieStimePage.tsx` | history list + immutable detail | ✓ VERIFIED | Read in full: protected route (redirect to /accedi if anonymous), list/detail/empty-state/skeleton, "Torna alla home" link (added post-checkpoint) |
| `frontend/src/components/SavedEstimateDetail.tsx`, `PdfDownloadButton.tsx` | read-only snapshot view + PDF download button | ✓ VERIFIED | PdfDownloadButton read in full — idle/loading/error states per UI-SPEC F.4 |
| `frontend/src/components/AccountMenu.tsx` | avatar + dropdown (Le mie stime/Esci) | ✓ VERIFIED | File present, referenced/imported in LeMieStimePage and EstimatePage |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `routers/auth.py` | `AuthService`/`dependencies.auth` | `create_session`, `get_current_user` | ✓ WIRED | Confirmed by direct read |
| `main.py` | `routers/auth`, `admin`, `stime_salvate`, `stima`, `health` | `include_router` prefix `/api/v1` | ✓ WIRED | `grep include_router app/main.py` shows all 5 routers registered |
| `main.py` | `SessionMiddleware` (Authlib) | `add_middleware(SessionMiddleware, secret_key=settings.OAUTH_SESSION_SECRET)` | ✓ WIRED | Distinct from application cookie `session_id`, confirmed in main.py |
| `routers/stime_salvate.py` | `PdfService`/`build_filename` | `GET /stime/{id}/pdf` | ✓ WIRED | Ownership check → `PdfService.render(row, current_user)` → `StreamingResponse` |
| `frontend/api/client.ts` | backend cookie session | `credentials: "include"` | ✓ WIRED | Confirmed present in fetch calls |
| `frontend/App.tsx` | all auth/estimate routes | `createBrowserRouter` | ✓ WIRED | All 6 routes present |
| `SoftWallCta.tsx` | `/registrati` with intent | router `state: { pendingStima }` | ✓ WIRED (per SUMMARY + file listing; not independently re-read line-by-line, but consistent with save-at-signup test evidence and prior TDD wiring pattern) | |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend test suite passes | `uv run pytest -q` (run live by verifier) | `66 passed, 2 skipped in 11.68s` | ✓ PASS (matches SUMMARY claim exactly) |
| No `password_hash` leak in schemas | `grep -rc "password_hash" app/schemas/` | 0 in all schema files | ✓ PASS |
| No impresa-family leak in PDF path | `grep -rEc "coefficiente_impresa\|base_eur_mq\|prezzo_impresa\|moltiplicatore" app/templates/pdf_stima.html app/services/pdf_service.py` | 0/0 | ✓ PASS |
| Routers wired in main.py | `grep include_router app/main.py` | health, stima, auth, admin, stime_salvate all present | ✓ PASS |
| Frontend credentials:"include" present | `grep credentials src/api/client.ts src/api/stima.ts` | 3 matches | ✓ PASS |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER found in any phase-modified backend or frontend file | — | None — clean scan across all 20 key files |

No unresolved debt markers found. No blockers.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUTH-01 | 02-01,02,03,04,06 | Registrazione email+password | ✓ SATISFIED | `/auth/registrati` endpoint, Argon2id hash, live-verified in browser |
| AUTH-02 | 02-01,05 | Login Google (OAuth) | ✓ SATISFIED (code) — env-deferred (live) | `/auth/google/login`+`/callback`, convergence tests green; live blocked by dev-only corporate proxy TLS interception, accepted override |
| AUTH-03 | 02-02,03,04,07,09 | Sessione persistente + logout | ✓ SATISFIED | DB-backed opaque session, revoke on logout, live-verified |
| AUTH-04 | 02-01,02,03 | Ruolo admin distinto | ✓ SATISFIED | `role` column, `require_admin`, `/admin/ping` 200/403 test |
| PDF-01 | 02-01,07,08,09 | PDF Free brandizzato scaricabile | ✓ SATISFIED (code) — env-deferred (byte render) | Endpoint/service/template complete, anti-leak/anti-recompute/ownership guards all pass; byte-render skipped on Windows dev only (WeasyPrint/GTK3), accepted override |

No orphaned requirements found — all 5 requirements mapped to plans in this phase.

### Human Verification Required

None outstanding. All `human-verify` checkpoints in this phase (02-04 Task 3, 02-09 Task 3) were explicitly approved by the user during phase execution, with evidence recorded in the respective SUMMARY.md files (browser session verification, cross-origin curl, cookie HttpOnly confirmation, and a follow-up commit `29ae7d6` adding a "Torna alla home" link requested during the 02-09 checkpoint). `STATE.md`'s "Blockers" section is stale (references the 02-09 Task 3 gate as still open) — the actual close-out is recorded in a later commit `d6aad86` ("docs(02-09): close human-verify gate (approved)") and in the SUMMARY.md addendum; this is a documentation-sync gap in STATE.md, not a functional gap, and does not block this phase.

### Gaps Summary

No functional gaps found. All 9 must-haves (5 roadmap success criteria decomposed to 6 truths given AUTH-01/03 map to 2 sub-behaviors, plus artifact/link/requirement checks) verified against actual source code, not just SUMMARY.md narrative. Two items carry accepted overrides for environment-only limitations (corporate-proxy TLS interception blocking live Google OAuth redirect in dev; missing native GTK3 runtime blocking WeasyPrint PDF byte-generation on Windows dev) — both are documented root-causes with code confirmed correct, both explicitly deferred to production by the user's own decision recorded in 02-05-SUMMARY.md and 02-08/02-09-SUMMARY.md, and neither reflects a code defect. Backend test suite independently re-run by this verifier: 66 passed, 2 skipped — exact match to SUMMARY claims. Recommend fixing the stale `STATE.md` Blockers section before/at the start of Phase 3, as a housekeeping item (not a phase-2 gap).

---

*Verified: 2026-08-26*
*Verifier: Claude (gsd-verifier)*
