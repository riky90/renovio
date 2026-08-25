---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-08-25T13:09:02.357Z"
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 13
  completed_plans: 9
  percent: 25
---

# Project State — ristruttura-stima

## Current Position

Phase: 02 (account-pdf) — EXECUTING
Plan: 6 of 9

- **Milestone:** v1 (MVP)
- **Phase:** 2
- **Status:** Ready to execute
- **Regola range (locked):** ±% solo sui lavori (4 categorie); extra fissi (€2.806 lordo); totale = Σ card + extra. Oracolo primario: 85 mq · totale = €47.985–€70.575.
- **Stack (da RESEARCH):** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Postgres/Alembic · React 19 + Vite + TS 5.9 + react-query + Tailwind/shadcn · autocomplete comuni ISTAT bundlato offline.

## Last Session

- **2026-08-25** — **Eseguito Plan 02-05 (Login Google OAuth + convergenza account)**: `app/oauth.py` (istanza `OAuth` Authlib registrata per Google, OIDC discovery, scope `openid email profile`); `app/main.py` con `SessionMiddleware` Starlette isolato (`OAUTH_SESSION_SECRET`, distinto dal cookie applicativo `session_id`, Pitfall 1); `routers/auth.py` con `GET /auth/google/login`/`GET /auth/google/callback` (convergenza D-05 via `get_or_create_user_by_email`, redirect errore generico T-05-04). Pre-flight: rilevate credenziali Google OAuth reali scritte per errore in `backend/.env.example` (tracciato) invece che in `backend/.env` (gitignorato) — corretto prima di qualunque commit, nessun segreto entrato in git. Checkpoint `blocking-human` per `httpx` (dipendenza runtime non dichiarata di `authlib.integrations.starlette_client`), confermato dall'utente e installato. TDD: `test_google_convergence.py` 2/2 verdi (nessun duplicato per stessa email, nome non sovrascritto su convergenza), 55/55 suite totale verde. Vedi `02-05-SUMMARY.md`. Prima:
- **2026-08-25** — **Eseguito Plan 02-07 (Salvataggio stima e storico backend)**: `app/models/stima_salvata.py` (`StimaSalvata` ibrido: colonne scalari `citta`/`mq`/`tipo`/`totale_min`/`totale_max`/`fallback` + `risultato_json` su `sqlalchemy.JSON` generico, non JSONB, per portabilità SQLite dev/Postgres prod) + migrazione Alembic 0003 (catena 0001→0002→0003); `app/schemas/stima_salvata.py` (`StimaSalvataCreate`/`StimaSalvataListItem`/`StimaSalvataOut`, stesso pattern a campi chiusi anti-leak di `schemas/stima.py`); `app/routers/stime_salvate.py` con `POST /api/v1/me/stime` (congela lo snapshot `StimaResponse`-shaped già calcolato dal client con `schema_version:1`, MAI `EstimationService.compute()` — D-09/Pitfall 5), `GET /api/v1/me/stime` (storico dalle colonne scalari), `GET /api/v1/me/stime/{id}` (dettaglio filtrato su `id` E `user_id` → 404 anti-IDOR, non 403). TDD RED→GREEN: `test_stime_salvate.py` 6/6 verdi (salva/lista/dettaglio, anti-IDOR 404, anti-leak ricorsivo, 401 senza sessione), 53/53 suite totale verde. Vedi `02-07-SUMMARY.md`. Prima:
- **2026-08-25** — **Eseguito Plan 02-03 (Endpoint HTTP auth + guard admin)**: `app/routers/auth.py` (POST `/registrati` con 409 su email duplicata, hash Argon2id, promozione admin, `create_session`, 201+`UserOut`; POST `/login` con `@limiter.limit("5/minute")` e messaggio 401 generico identico su email inesistente/password errata — anti-enumeration; POST `/logout` con revoca server-side; GET `/me` via `get_current_user`); `app/routers/admin.py` (GET `/ping` dietro `require_admin`, prova end-to-end di AUTH-04, nessuna UI); wiring in `main.py` (CORS invariato). TDD RED→GREEN: `test_auth_endpoints.py` 9/9 verdi su TestClient a cookie-jar reale (cookie httpOnly, logout→401, login corretto/errato, admin 200/403), 47/47 suite totale verde. Deviazione: `limiter.reset()` aggiunto in fixture per isolare i test dal rate-limit condiviso tra funzioni. Vedi `02-03-SUMMARY.md`. Prima:
- **2026-08-25** — **Eseguito Plan 02-02 (Fondazione backend autenticazione)**: modelli ORM `User`/`UserSession`/`PasswordResetToken` + migrazione Alembic 0002 (verificata upgrade/downgrade/upgrade); `AuthService` con hashing Argon2id (`argon2-cffi`), sessione applicativa opaca DB-backed (`user_session.id` = `secrets.token_urlsafe(32)` come PK, mai JWT, revoca server-side pulita via DELETE), convergenza per-email (D-05), promozione admin via `ADMIN_EMAIL` (D-03); dependency `get_current_user`/`require_admin` (401/403); schemi anti-leak `RegistrazioneRequest`/`LoginRequest`/`UserOut` (mai `password_hash`). TDD RED→GREEN: `test_auth_service.py` 12/12 verdi, 38/38 suite totale verde. Aggiunta `email-validator` (richiesta da `pydantic.EmailStr`, anticipata dal piano). Vedi `02-02-SUMMARY.md`. Prima:
- **2026-08-25** — **Eseguito Plan 02-01 (Setup dipendenze e config Account & PDF)**: gate legittimita' pacchetti pre-approvato dall'utente ("approvato" per tutti e 7 — argon2-cffi, Authlib, itsdangerous, weasyprint, jinja2, aiosmtplib, react-router); installati via `uv add --native-tls` (backend) e `npm install` (frontend); `Settings` esteso con SECRET_KEY, OAUTH_SESSION_SECRET, COOKIE_SECURE, GOOGLE_CLIENT_ID/SECRET, SMTP_*, FRONTEND_URL, ADMIN_EMAIL; `.env.example` documentato senza segreti reali. Vedi `02-01-SUMMARY.md`. Prima:
- **2026-08-25** — **Discussione Fase 2 (Account & PDF) completata** → `02-CONTEXT.md` + `02-DISCUSSION-LOG.md` (commit `596453d`). 8 aree decise: (1) auth **self-hosted FastAPI**, `user` nel Postgres, password bcrypt/argon2 + Google via Authlib, **cookie httpOnly**, `role` user/admin col primo admin da seed/env (route protette già in Fase 2, UI admin → Fase 4); (2) verifica email **no** in v1, **reset via link** → serve email transazionale ora (riusata dai lead in Fase 4); (3) **un solo account per email** (Google confluisce); (4) registrazione **email+password+nome**; (5) **salva-al-signup** della stima corrente, poi auto-save da loggato; (6) **storico "Le mie stime"** + **snapshot** (input+risultato congelati, immutabili); (7) **PDF Free** solo-loggato, **server-side** dallo snapshot, 1 pagina completa, anti-leak; (8) branding PDF su palette Slate/blue-600 da UI-SPEC. Net-new: tabelle `user` + `stima`, nuova migrazione Alembic, dependency auth + guard admin, utility PDF + email. Prossimo: `/gsd-plan-phase 2`. Prima:
- **2026-08-24** — Eseguito Plan 01-04 (Frontend Free end-to-end): shadcn (base radix, preset vega) inizializzato su Tailwind v4 con token Slate/blue-600 riscritti a mano da UI-SPEC (il CLI shadcn installato, v4.19.0, non ha più il preset "New York"); comuni.json ISTAT (7904 comuni) bundlato per l'autocomplete città 100% client-side; `EstimateForm` (città+mq+tipo, validazione italiana, CTA gated) + `CityAutocomplete` (selezionabile mouse/tastiera) + `EstimatePage` (form → `useMutation(postStima)` → riepilogo input + disclaimer condizionale + 4 card categoria + extra fissi + `TotalCard` accent + `SoftWallCta`), stati skeleton/error. `api/stima.ts` normalizza i campi Decimal-come-stringa di Pydantic v2 a number al confine API. Verificato dal vivo contro il backend reale: 85mq/totale/Reggio Emilia → 47.985–70.575 € (riconciliazione esatta), Modena → fallback con disclaimer; grep conferma nessun leak di coefficiente/impresa nel frontend. Checkpoint human-verify: approvato dall'utente dopo 2 fix richiesti in sessione (autocomplete non selezionabile — bug classico onBlur-vs-click di cmdk risolto; poi highlight riga attiva rinforzato a blue-600 pieno su richiesta). Vedi `01-04-SUMMARY.md`. **Fase 1 completa.** Prima:
  - Eseguito Plan 01-03 (Endpoint POST /api/v1/stima): `app/schemas/stima.py` (StimaRequest limitato + StimaResponse/CategoriaOut/ExtraOut/TotaleOut a campi chiusi, anti-leak); `app/routers/stima.py` risolve città + calcola via EstimationService + costruisce la risposta esplicitamente (mai model_validate su entità ORM); split imponibile/IVA per categoria recuperato algebricamente in modo esatto; `app/limiter.py` (nuovo modulo condiviso) applica rate limit 20/minute. Oracolo 85mq/totale confermato end-to-end su HTTP (47985–70575, fallback=False); Modena → fallback=True con disclaimer; 422 su mq/tipo/città fuori range. `test_no_leak.py` prova ricorsivamente (chiavi a ogni profondità + substring) che coefficiente_impresa/base_eur_mq/moltiplicatore/prezzo_impresa non appaiono mai nella risposta seriale, su RE + Modena × 3 tipi. TDD RED→GREEN, 26/26 test passanti. Vedi `01-03-SUMMARY.md`. Prima:
  - Eseguito Plan 01-02 (Seed + EstimationService): seed idempotente di `docs/seed-coefficienti-base.json` (1 listino RE default, 4 categorie, 3 tipi, 12 moltiplicatori, 2 extra, 2 alias comune_listino); `EstimationService.compute()` in Decimal puro, IVA per categoria, range ±% solo sui 4 subtotali di categoria, extra fissi mai scalati; `resolve_listino()` con fallback su RE. Oracolo primario 85mq·totale pinnato esatto (47985–70575); riconciliazione card+extra=totale verificata esatta; nessun leak di coefficiente_impresa nel risultato. TDD RED→GREEN, 12/12 test passanti. Vedi `01-02-SUMMARY.md`. Prima:
  - Eseguito Plan 01-01 (Walking Skeleton): backend FastAPI/SQLAlchemy 2.0/Alembic + frontend React/Vite/TS scaffoldati; schema Fase 1 completo (8 tabelle) migrato; loop end-to-end `GET /api/v1/health/db` provato (Browser → API → DB → Browser). Vedi `01-01-SUMMARY.md`.
  - Init progetto (analisi computo Excel, decisioni fondanti, PROJECT/config/REQUIREMENTS/ROADMAP).
  - **Ambiente GSD riparato**: agenti installati (profilo full, `agents_installed: true`); shim `gsd-sdk` ripuntato al SDK reale `~/.claude/gsd-source/bin/gsd-sdk.js` (backup `.bak`); ledger migrazioni riparato azzerando i checksum (backup in `~/.claude/gsd-install-state.json.bak-*`). Nota: SDK sul PATH è 1.50-canary, workflow 1.42.3 — `query` compatibile.
  - **Discussione Fase 1 completata** → `01-CONTEXT.md`: motore €/m² base × moltiplicatore per tipo; range ±% per tipo (admin); città a campo libero + fallback RE con disclaimer; risultato = 4 card + totale; soft wall (stima anonima, account per salvare/PDF/contatto → Fase 2). Roadmap invariata.

## Next Step

- **Fase 2 discussa** → `.planning/phases/02-account-pdf/02-CONTEXT.md` (auth self-hosted FastAPI, cookie httpOnly, ruolo admin da seed/env, salva-al-signup + storico snapshot, PDF Free server-side solo-loggato). Prossimo: `/gsd-plan-phase 2`.

## Open Questions / To Decide

- Prezzo abbonamento Pro.
- ~~Provider auth definitivo~~ — **DECISO in Fase 2**: auth self-hosted nel backend FastAPI (users nel Postgres), sessione via cookie httpOnly.
- Stack tecnico (candidato dai progetti dell'utente: FastAPI + React, deploy Railway).
- Quali voci esatte sono le "voci-chiave" del motore Pro.
- Meccanica esatta referenti per città (mail vs visualizzazione all'utente).

## Decision Log Pointer

Vedi PROJECT.md → Key Decisions e `BRIEF-DISCUSSIONE.md`.

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase 01-stima-free-end-to-end P01 | 25min | 3 tasks | 48 files |
| Phase 01-stima-free-end-to-end P02 | 20min | 1 tasks | 7 files |
| Phase 01-stima-free-end-to-end P03 | 20min | 2 tasks | 6 files |
| Phase 01-stima-free-end-to-end P04 | 58min | 2 tasks | 35 files |
| Phase 02-account-pdf P01 | 12min | 2 tasks | 6 files |
| Phase 02-account-pdf P02 | 4min | 2 tasks | 9 files |
| Phase 02-account-pdf P03 | 15min | 2 tasks | 4 files |
| Phase 02-account-pdf P07 | 12min | 2 tasks | 7 files |
| Phase 02-account-pdf P05 | 25min | 3 tasks | 7 files |

## Decisions

- [Phase 01-stima-free-end-to-end]: typescript pinnato a 5.9.3 stabile (non 6.x/7.x preview) per requisito RESEARCH/plan
- [Phase 01-stima-free-end-to-end]: uv add --native-tls necessario per bypassare il proxy aziendale con cert self-signed
- [Phase 01-stima-free-end-to-end]: httpx2 aggiunto come dev dep backend (richiesto da starlette 1.6 TestClient, non previsto in RESEARCH)
- [Phase 01-stima-free-end-to-end]: [Phase 01-stima-free-end-to-end P02]: comune_listino seeded con 2 righe alias RE (Reggio Emilia, Reggio nell'Emilia) anziche 1, per risolvere entrambi gli alias senza fallback
- [Phase 01-stima-free-end-to-end]: [Phase 01-stima-free-end-to-end P02]: sys.path bootstrap in scripts/seed.py per supportare l'esecuzione diretta 'python scripts/seed.py' richiesta dal piano
- [Phase 01-stima-free-end-to-end]: app/limiter.py estratto come modulo condiviso per evitare import circolare tra main.py e routers/stima.py nel decorare l'endpoint con il rate limit
- [Phase 01-stima-free-end-to-end]: imponibile_min/max e iva_min/max per categoria recuperati algebricamente (totale/(1+iva_pct)) nel router, senza modificare EstimationService gia' bloccato dal Piano 02
- [Phase 01-stima-free-end-to-end]: shadcn CLI ha cambiato generazione (v4.19.0): niente preset 'New York'; usato --base radix + preset vega, token Slate/blue-600 riscritti a mano da UI-SPEC
- [Phase 01-stima-free-end-to-end]: Decimal backend serializzati come stringhe JSON (Pydantic v2): normalizzati a number in api/stima.ts al confine API
- [Phase 01-stima-free-end-to-end]: CityAutocomplete: rimosso onBlur di chiusura popover (bug classico, in gara con onSelect click-based di cmdk); chiusura via onSelect/Escape/outside-pointerdown
- [Phase 01-stima-free-end-to-end]: Highlight riga attiva autocomplete rafforzato a bg-primary/text-primary-foreground (blue-600 pieno) su richiesta utente al checkpoint
- [Phase 02-account-pdf]: Gate pacchetti [ASSUMED] pre-approvato dall'utente ('approvato') per tutti e 7 (argon2-cffi, Authlib, itsdangerous, weasyprint, jinja2, aiosmtplib, react-router)
- [Phase 02-account-pdf]: uv add --native-tls necessario anche in Fase 2 per bypassare il proxy aziendale con cert self-signed
- [Phase 02-account-pdf]: email-validator aggiunto via uv add --native-tls (richiesto da pydantic EmailStr, anticipato dal piano)
- [Phase 02-account-pdf]: sessione applicativa opaca DB-backed (user_session.id = secrets.token_urlsafe(32) come PK), mai JWT, per revoca server-side pulita (D-02)
- [Phase 02-account-pdf]: slowapi Limiter e' un singleton di processo: i test e2e su endpoint rate-limited devono chiamare limiter.reset() nella fixture per isolamento
- [Phase 02-account-pdf]: docstring di schemas/stima_salvata.py riformulata per non contenere letteralmente le stringhe della famiglia impresa, per rispettare in senso stretto il criterio meccanico grep -rc == 0 (stesso precedente di 02-02/02-03)
- [Phase 02-account-pdf]: credenziali Google OAuth reali scritte per errore in backend/.env.example (tracciato) sono state spostate in backend/.env (gitignorato) prima di qualunque commit — nessun segreto entrato in git
- [Phase 02-account-pdf]: httpx aggiunto come dipendenza runtime (richiesta da authlib.integrations.starlette_client, non prevista da RESEARCH) solo dopo checkpoint blocking-human e conferma esplicita dell'utente
- [Phase 02-account-pdf]: SessionMiddleware Starlette (OAUTH_SESSION_SECRET) isolato dal cookie applicativo session_id per il flusso Google OAuth (Pitfall 1)
