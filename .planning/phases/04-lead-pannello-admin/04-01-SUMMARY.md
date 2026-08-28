---
phase: 04-lead-pannello-admin
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, pydantic, sqlite, aiosmtplib, lead-capture]

# Dependency graph
requires:
  - phase: 01-motore-stima
    provides: Categoria/TipoRistrutturazione/Listino/Referente/ComuneListino schema, city_resolver.resolve_listino
  - phase: 02-auth-account
    provides: get_current_user dependency, session-cookie auth, email_service.send_email (async, never-raises)
  - phase: 02-stime-salvate (StimaSalvata)
    provides: immutable-snapshot ORM pattern (scalar frozen columns) replicato per Lead
provides:
  - Lead model (backend/app/models/lead.py) — snapshot indipendente citta/mq/tipo/totale_min/totale_max
  - migrazione 0006 (tabella lead, additiva, reversibile)
  - POST /api/v1/lead (login-only, persist-then-email, D-07)
  - lead_service.resolve_referente (fallback su listino default, D-04/D-05)
  - schemas/lead.py (LeadCreate/LeadCreatedOut/LeadOut/LeadUpdate) pronti per il consumo admin in 04-04
affects: [04-04-admin-lead-dashboard, 04-06-lead-contact-dialog-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Immutable-snapshot Lead (estende StimaSalvata): colonne scalari congelate al submit, nessuna FK richiesta per il render"
    - "resolve_referente come estensione di resolve_listino: due rami (listino risolto -> referente attivo per priorita; altrimenti fallback su listino is_default)"
    - "Router async con persist-then-email: commit sincrono del Lead PRIMA di qualsiasi await send_email; try/except di difesa in profondità che marca email_inviata=False senza propagare 500"
    - "Anti-leak strutturale: nessuna colonna coefficiente_impresa/base_eur_mq su Lead, corpo email costruito solo da campi contatto + riepilogo a range"

key-files:
  created:
    - backend/app/models/lead.py
    - backend/app/schemas/lead.py
    - backend/app/services/lead_service.py
    - backend/app/routers/lead.py
    - backend/alembic/versions/0006_lead.py
    - backend/tests/test_lead.py
  modified:
    - backend/app/main.py

key-decisions:
  - "Difesa in profondità D-07 implementata direttamente nel Task 2 (try/except attorno a send_email nel router) anziché rimandata al Task 3: il Task 3 ha aggiunto solo la copertura di test esplicita (corpo email anti-leak, 422 su input fuori bound) richiesta dal piano."
  - "resolve_referente riusa resolve_listino as-is (non re-implementato) per restare fedele al pattern city_resolver, come raccomandato da 04-RESEARCH.md Pattern 3."
  - "Snapshot Lead: nessun FK obbligatorio a stima_salvata — colonna stima_salvata_id presente ma nullable e mai popolata in questo piano (il payload del client non porta l'id della stima salvata), coerente con D-03 (leggibile anche se la stima viene cancellata)."

patterns-established:
  - "Pattern immutable-snapshot Lead: riusabile identico per qualunque futura entità che debba congelare un riepilogo economico a range senza dipendere da righe mutabili."
  - "Router POST con guardia get_current_user (non require_admin) + persist-then-email async: template diretto per eventuali futuri endpoint di notifica loggati."

requirements-completed: [LEAD-01, LEAD-02, LEAD-03]

# Metrics
duration: 45min
completed: 2026-08-28
---

# Phase 04 Plan 01: Lead capture end-to-end (backend) Summary

**POST /api/v1/lead persiste sempre il record prima di qualunque tentativo SMTP, risolve il referente per città con fallback sul listino di default, e invia due email (notifica + conferma) a range, senza mai esporre coefficiente_impresa/base_eur_mq.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-08-28T06:05:00Z (stima, primo Read del piano)
- **Completed:** 2026-08-28T06:50:52Z
- **Tasks:** 3 (tutti completati)
- **Files modified:** 7 (6 creati, 1 modificato)

## Accomplishments
- Modello `Lead` con snapshot scalare immutabile (citta/mq/tipo/totale_min/totale_max), nessuna colonna impresa (D-03/D-22)
- Migrazione 0006 additiva e reversibile (`upgrade`/`downgrade`/`upgrade` verificato), seed preservato (D-24)
- `POST /api/v1/lead`: 401 anonimo / 201 loggato, persist-then-email (D-07), notifica referente + conferma utente (D-06/D-08), riepilogo sempre a range (D-23)
- `resolve_referente`: risoluzione per città con fallback sul referente attivo del listino `is_default` (D-04/D-05)
- Resilienza SMTP: il Lead resta salvato con `email_inviata=False` e la risposta resta 201 anche se `send_email` solleva
- Validazione input bounded (mq 1-2000, messaggio max 2000 caratteri, preferenza_contatto enum chiuso) con 422
- Anti-leak verificato ricorsivamente sia sulla risposta JSON sia sul corpo HTML delle due email

## Task Commits

Ogni task è stato committato atomicamente (TDD: RED -> GREEN):

1. **Task 1: Test RED end-to-end del lead** - `eb4729c` (test)
2. **Task 2: Modello Lead + migrazione 0006 + schemi + service + router (GREEN)** - `e900c9d` (feat)
3. **Task 3: Robustezza D-07/D-08 + validazione input + guardia anti-leak email** - `8169f37` (test)

_Nessun commit `refactor` necessario — il router è stato scritto correttamente al primo GREEN._

## Files Created/Modified
- `backend/app/models/lead.py` - Modello `Lead`, snapshot immutabile, nessuna colonna impresa
- `backend/app/schemas/lead.py` - `LeadCreate`/`LeadCreatedOut`/`LeadOut`/`LeadUpdate` (closed-field anti-leak)
- `backend/app/services/lead_service.py` - `resolve_referente` (estende `city_resolver.resolve_listino`)
- `backend/app/routers/lead.py` - `POST /api/v1/lead`, persist-then-email async, corpo email a range
- `backend/alembic/versions/0006_lead.py` - Migrazione additiva (tabella `lead`), reversibile
- `backend/app/main.py` - Registrato `lead.router` con prefix `/api/v1`
- `backend/tests/test_lead.py` - 11 test (RED iniziale a 7, +4 nel Task 3)

## Decisions Made
- La difesa in profondità D-07 (try/except attorno a `send_email`, `email_inviata=False` su fallimento) è stata implementata già nel Task 2 anziché rimandata al Task 3, per avere un router GREEN robusto fin dal primo commit; il Task 3 ha aggiunto solo i test espliciti richiesti dal piano (corpo email anti-leak, 422 su bound).
- `resolve_referente` chiama `resolve_listino` invece di re-implementarne la logica (fedeltà a 04-RESEARCH.md Pattern 3, Assumption A3 confermata).
- `Lead.stima_salvata_id` resta nullable e non popolato in questo piano: il payload `LeadCreate` non porta un id di stima salvata (il client invia solo lo snapshot), coerente con D-03 ("indipendente da stima_salvata... leggibile anche se l'utente cancella la stima").

## Deviations from Plan

None - plan eseguito esattamente come scritto. La resilienza D-07 è stata anticipata dal Task 3 al Task 2 (stesso contenuto, solo il commit dei test è stato posticipato al Task 3 come da piano), non è considerata una deviazione dai criteri di accettazione.

## Issues Encountered
Durante la prima esecuzione della suite completa post-Task 2 è comparso un singolo fallimento intermittente in `tests/test_password_reset.py::TestResetTokenUnit::test_token_manomesso_ritorna_none` (test estraneo, manomissione token reset password). Ri-eseguito isolato: PASS. Ri-eseguita l'intera suite: PASS (114 poi 118 dopo il Task 3, 4 skip GTK3). Fuori scope per questo piano (non causato dalle modifiche di `lead.py`/modello/migrazione); documentato in `.planning/phases/04-lead-pannello-admin/deferred-items.md` per eventuale indagine futura se si ripresenta.

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta (SMTP resta opzionale, `email_service.py` ha già un fallback dev-log documentato).

## Next Phase Readiness
- `schemas/lead.py::LeadOut`/`LeadUpdate` sono già pronti per essere consumati da `04-04-PLAN.md` (dashboard admin lead, GET/PATCH `/admin/lead`).
- `Lead.referente_id`/`stato`/`nota` coprono già i campi richiesti da D-17 (stato nuovo/gestito + nota).
- Nessun blocco noto per 04-06 (UI `LeadContactDialog`): il contratto `POST /api/v1/lead` (payload/risposta) è stabile e testato end-to-end.

---
*Phase: 04-lead-pannello-admin*
*Completed: 2026-08-28*

## Self-Check: PASSED

Tutti i file dichiarati (models/lead.py, schemas/lead.py, services/lead_service.py,
routers/lead.py, alembic/versions/0006_lead.py, tests/test_lead.py, questo SUMMARY.md)
sono presenti sul filesystem. Tutti e 3 gli hash di commit (eb4729c, e900c9d, 8169f37)
sono presenti in `git log --oneline --all`.
