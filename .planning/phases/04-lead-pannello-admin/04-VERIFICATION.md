---
phase: 04-lead-pannello-admin
verified: 2026-08-28T12:21:34Z
status: human_needed
score: 5/5 must-haves verified at code level (12/12 requirement-level truths); 5 checkpoints require live human/browser verification
overrides_applied: 0
human_verification:
  - test: "04-06 — Flusso contatto lead end-to-end in browser"
    expected: "Anonimo -> redirect /registrati?intent=contatta con stima preservata; loggato -> dialog LeadContactDialog precompilato; invio -> conferma a schermo + toast + email (dev-log) al referente e all'utente, snapshot mostrato solo a range"
    why_human: "Richiede backend+frontend live, sessione browser reale, ispezione dei log SMTP dev-fallback — checkpoint dichiarato aperto in 04-06-SUMMARY.md, mai eseguito"
  - test: "04-07 — Guard area /admin in browser"
    expected: "Utente admin loggato: redirect /admin -> /admin/lead, sidebar 5 sezioni, badge Admin. Utente non-admin/anonimo: blocco 'Accesso negato' senza flash di dati admin"
    why_human: "Richiede login reale con account ADMIN_EMAIL e ispezione visiva — checkpoint dichiarato aperto in 04-07-SUMMARY.md, mai eseguito"
  - test: "04-08 — CRUD listini/coefficienti/upload Excel in browser con effetto immediato"
    expected: "Creazione listino/città, categoria, voce funzionano da UI; modifica coefficiente si riflette su una nuova stima Free calcolata subito dopo (D-11); upload .xlsx con preview diff e conferma import, blocco file non-.xlsx/>10MB"
    why_human: "Richiede backend/DB live e sessione admin reale — checkpoint dichiarato aperto in 04-08-SUMMARY.md, mai eseguito (D-11 è comunque già coperto da test automatico backend, vedi sotto)"
  - test: "04-09 — CRUD città/mappature/tipi/testi in browser"
    expected: "Aggiungere mappatura città->listino elimina il fallback per una stima in quella città; eliminare mappatura mostra il disclaimer corretto nell'alert-dialog; modificare disclaimer_fallback_citta cambia il testo mostrato nella stima fallback"
    why_human: "Richiede backend/DB live e sessione admin reale — checkpoint dichiarato aperto in 04-09-SUMMARY.md, mai eseguito"
  - test: "04-11 — Dashboard lead e CRUD referenti in browser"
    expected: "Creare/modificare/eliminare un referente attivo per città; generare un lead reale (flusso 04-06) e vederlo comparire nella dashboard filtrabile per città/stato, con dettaglio a range (nessun prezzo impresa) e aggiornamento stato/nota persistito"
    why_human: "Richiede backend/DB live e sessione admin reale — checkpoint dichiarato aperto in 04-11-SUMMARY.md, mai eseguito"
---

# Phase 4: Lead & pannello admin Verification Report

**Phase Goal:** Da ogni livello l'utente contatta un professionista (lead via email + dashboard); l'admin gestisce listini, coefficienti, città, referenti e testi senza toccare codice.
**Verified:** 2026-08-28T12:21:34Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Da Free e da Pro l'utente invia una richiesta di contatto con i dati della stima | ✓ VERIFIED (codice) — ? UNCERTAIN (UX live) | `frontend/src/components/SoftWallCta.tsx` apre `LeadContactDialog` per utente loggato, redirect `/registrati?intent=contatta` per anonimo preservando `pendingStima`; `backend/app/routers/lead.py` `POST /api/v1/lead` (guard `get_current_user`, non `require_admin`) persiste sempre il record prima di ogni tentativo SMTP. Non ancora osservato in browser end-to-end (checkpoint 04-06 aperto) |
| 2 | Il lead arriva via email e compare nella dashboard admin | ✓ VERIFIED (codice) — ? UNCERTAIN (UX live) | `lead.py::_invia_email_lead` invia notifica al referente + conferma utente via `email_service.send_email` (dev-fallback logga); `backend/app/routers/admin/lead.py` GET/PATCH `/admin/lead` dietro `require_admin`; `frontend/src/pages/admin/LeadDashboardPage.tsx` consuma `getAdminLeads`/`getAdminLead`/`updateAdminLead` reali (non stub). Non ancora osservato in browser (checkpoint 04-06 e 04-11 aperti) |
| 3 | L'admin crea/modifica listini prezzi per città e coefficienti del modello, e le stime ne risentono subito | ✓ VERIFIED | `backend/app/routers/admin/listini.py` (CRUD Listino/ListinoCategoria/Voce) e `backend/app/routers/admin/coefficienti.py` (moltiplicatori/IVA/extra/coeff-pro/base) tutti dietro `Depends(require_admin)`. **Effetto immediato provato da test automatico**: `backend/tests/test_admin_coefficienti.py::TestEffettoImmediato::test_patch_moltiplicatore_riflesso_su_nuova_stima` esegue POST /api/v1/stima, PATCH moltiplicatore, POST /api/v1/stima di nuovo, e asserisce `totale_min_dopo != totale_min_prima` — PASS. `frontend/src/pages/admin/ListiniPage.tsx`/`CoefficientiPage.tsx` cablate su API reali (04-08) |
| 4 | L'admin configura i referenti per città (modello multi-referente, un referente attivo in v1) | ✓ VERIFIED (codice) — ? UNCERTAIN (UX live) | `backend/app/routers/admin/referenti.py` CRUD completo (`GET/POST/PATCH/DELETE`) su `Referente` (attivo/priorità), dietro `require_admin`; `lead_service.resolve_referente` (04-01) integra: referente attivo per priorità sul listino della città, fallback sul referente del listino `is_default`; `frontend/src/pages/admin/ReferentiPage.tsx` cablata su API reali (04-11). Non ancora osservato in browser (checkpoint 04-11 aperto) |
| 5 | L'admin modifica città, mappature e testi/disclaimer dall'interfaccia | ✓ VERIFIED (codice) — ? UNCERTAIN (UX live) | `backend/app/routers/admin/citta.py` CRUD `ComuneListino` (upsert per `comune_slug`) + list/patch `TipoRistrutturazione`; `backend/app/routers/admin/testi.py` GET/PATCH tabella `Testo`; disclaimer EST-06 migrato da costante a `testo_service.get_testo()` in `routers/stima.py`; `frontend/src/pages/admin/CittaTestiPage.tsx` cablata su API reali (04-09). Non ancora osservato in browser (checkpoint 04-09 aperto) |

**Score:** 5/5 truths verificate a livello di codice; tutte e 5 hanno una componente UX/browser non ancora osservata da un umano (checkpoint aperti).

### Requirements Coverage

| Requisito | Descrizione | Status | Evidenza |
|-----------|-------------|--------|----------|
| LEAD-01 | Da ogni livello l'utente può richiedere il contatto di un professionista | ✓ SATISFIED (codice) | `SoftWallCta.tsx` + `LeadContactDialog.tsx` + `POST /api/v1/lead`; usato sia da schermata Free sia Pro (stesso componente `SoftWallCta`) |
| LEAD-02 | Il lead arriva via email e viene salvato nella dashboard admin | ✓ SATISFIED (codice) | persist-then-email in `lead.py`; `admin/lead.py` GET/PATCH; `LeadDashboardPage.tsx` |
| LEAD-03 | Modello dati multi-referente per città (v1 un referente configurato) | ✓ SATISFIED | `models/catalogo.py::Referente` (listino_id, attivo, priorita) preesistente, CRUD completo in 04-04, nessuna unicità DB forzata (per design, "un referente attivo" resta convenzione applicativa come da D-15/D-16) |
| ADM-01 | L'admin gestisce i listini prezzi per città (voci, prezzi unitari, coefficiente impresa) | ✓ SATISFIED | CRUD granulare (04-02) + upload Excel due-passi con preview/diff/idempotenza (04-05) + UI (04-08) |
| ADM-02 | L'admin gestisce i coefficienti parametrici del modello di stima | ✓ SATISFIED | CRUD 4 famiglie (moltiplicatori/IVA/extra/coeff-pro) + base_eur_mq sola lettura (04-10) + UI (04-08), effetto immediato testato |
| ADM-03 | L'admin gestisce città, mappatura città->listino, tipi di ristrutturazione e testi/disclaimer | ✓ SATISFIED | CRUD città/tipi/testi (04-03) + UI (04-09); disclaimer EST-06 letto da DB |
| ADM-04 | L'admin consulta i lead ricevuti e configura i referenti per città | ✓ SATISFIED | Dashboard lead + CRUD referenti (04-04) + UI (04-11) |

Nota: `.planning/REQUIREMENTS.md` mostra ancora le checkbox LEAD-01..03/ADM-01..04 come `[ ]` (non spuntate) — documento di tracking non aggiornato dagli executor, non riflette lo stato reale del codice. Segnalato come discrepanza documentale, non un gap funzionale.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/lead.py` | Modello Lead, snapshot immutabile, no colonne impresa | ✓ VERIFIED | Nessuna colonna `coefficiente_impresa`/`base_eur_mq`; grep conferma |
| `backend/alembic/versions/0006_lead.py`, `0007_testo.py` | Migrazioni additive reversibili | ✓ VERIFIED | Presenti, catena 0005->0006->0007 |
| `backend/app/routers/lead.py` | POST /api/v1/lead pubblico-loggato | ✓ VERIFIED, WIRED | Registrato in `main.py:41`; guard `get_current_user` |
| `backend/app/routers/admin/*.py` (8 subrouter) | CRUD listini/coefficienti/citta/testi/referenti/lead/upload dietro require_admin | ✓ VERIFIED, WIRED | Ogni route ha `Depends(require_admin)` (verificato per tutte, vedi grep sopra); aggregati in `routers/admin/__init__.py`, registrato in `main.py:37` |
| `backend/app/models/testo.py` + `testo_service.py` | Tabella key/value testi, read-through | ✓ VERIFIED, WIRED | `routers/stima.py` legge il disclaimer da `get_testo()`, non più da costante |
| `backend/app/services/listino_upload_service.py` | Upload Excel due-passi idempotente | ✓ VERIFIED | 18 test dedicati (`test_upload_listino.py`), preview non scrive, confirm upsert idempotente |
| `frontend/src/pages/admin/*.tsx` (5 pagine) | UI reale (non stub) per ogni sezione admin | ✓ VERIFIED, WIRED | Tutte importano/usano `AdminLayout` + client API reali (`api/admin/*.ts`), nessun dato hardcoded rilevato |
| `frontend/src/components/LeadContactDialog.tsx`, `SoftWallCta.tsx` | Form contatto reale | ✓ VERIFIED, WIRED | `postLead` chiamato via `useMutation`; snapshot costruito solo da campi a range già a schermo |

### Anti-Leak Guardrail (CLAUDE.md, non negoziabile)

| Check | Result |
|-------|--------|
| `coefficiente_impresa`/`base_eur_mq` in schemi/risposte non-admin (`backend/app/schemas/*.py`, `backend/app/routers/stima.py`, `backend/app/routers/lead.py`) | Nessun match reale — solo riferimenti in commenti/docstring che *vietano* l'esposizione (`schemas/__init__.py`, `schemas/lead.py`, `schemas/stima.py`, `routers/stima.py`) |
| `coefficiente_impresa`/`base_eur_mq` nel frontend fuori da `frontend/src/**/admin/**` | Nessun match |
| Test automatico dedicato | `backend/tests/test_no_leak_admin.py`: `test_endpoint_pubblico_non_espone_coefficiente_impresa` (PASS) e `test_endpoint_admin_espone_deliberatamente_coefficiente_impresa` (PASS) — entrambe le direzioni coperte |
| Output sempre a range | `LeadCreate`/`LeadOut` usano solo `totale_min`/`totale_max`; email al referente e conferma utente costruite solo da questi campi (`lead.py::_riepilogo_html`) |

**Esito guardrail: PASS — nessun leak rilevato staticamente, invariante verificato anche a runtime dai test.**

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Suite backend completa | `cd backend && uv run pytest -q` | 234 passed, 4 skipped (GTK3, invariati), 0 failed | ✓ PASS |
| Build frontend (typecheck + bundle) | `cd frontend && npm run build` (tsc -b + vite build) | Completata senza errori (solo warning non bloccante su chunk size) | ✓ PASS |
| Router lead+admin montati | `grep include_router backend/app/main.py` | `lead.router` e `admin.router` entrambi registrati con prefix `/api/v1` | ✓ PASS |
| Ogni route admin protetta da `require_admin` | Ispezione di tutte le route in `backend/app/routers/admin/*.py` | Tutte le route (listini, coefficienti, citta, testi, referenti, lead, upload, ping) usano `Depends(require_admin)` | ✓ PASS |
| Effetto immediato coefficienti su nuova stima (D-11) | `test_patch_moltiplicatore_riflesso_su_nuova_stima` | `totale_min_dopo != totale_min_prima` dopo PATCH | ✓ PASS |
| Anti-leak bidirezionale | `test_no_leak_admin.py` (2 test) | pubblico non espone, admin espone deliberatamente | ✓ PASS |

### Probe Execution

Nessun probe dedicato (`scripts/*/tests/probe-*.sh`) dichiarato nei PLAN/SUMMARY di questa fase. Step 7c non applicabile — SKIPPED.

### Anti-Patterns Found

Nessun blocker. Grep per `TODO|FIXME|XXX|HACK|PLACEHOLDER|coming soon|not yet implemented` sui file chiave backend/frontend della fase: nessun match reale (solo attributi HTML `placeholder="..."` su input di form, non debito tecnico). Nessuno stub residuo dichiarato dagli executor in nessun SUMMARY della fase.

## Human Verification Required

Cinque checkpoint `human-verify` con `gate="blocking"` sono stati dichiarati **aperti** dagli executor (mai eseguiti, per assenza di un ambiente backend+DB+browser live nel contesto di esecuzione automatica). Il codice a supporto di ciascuno è stato verificato staticamente (vedi tabelle sopra) ed è coerente/non-stub, ma il comportamento end-to-end in un browser reale non è stato osservato da nessuno. Elenco completo in frontmatter `human_verification:`. In sintesi:

1. **04-06** — Flusso contatto lead (anonimo->redirect, loggato->dialog, invio->email+dashboard)
2. **04-07** — Guard visivo area `/admin` (redirect, sidebar, blocco accesso negato)
3. **04-08** — CRUD listini/coefficienti/upload Excel in UI, incluso l'effetto immediato visibile a schermo
4. **04-09** — CRUD città/mappature/tipi/testi in UI, incluso il fallback/disclaimer
5. **04-11** — Dashboard lead e CRUD referenti in UI, incluso il ciclo lead reale end-to-end

## Gaps Summary

Nessun gap di codice: tutte le API, i modelli, le migrazioni e le pagine frontend richieste dai 7 requisiti (LEAD-01..03, ADM-01..04) esistono, sono sostanziali (non stub), sono cablate (router registrati, pagine consumano API reali) e passano 234/234 test backend + build frontend pulita. Il guardrail anti-leak è rispettato sia staticamente sia a runtime.

L'unico elemento mancante per una chiusura "passed" piena è la **verifica umana in browser** dei 5 checkpoint bloccanti lasciati aperti dagli executor (comportamento visivo/UX, invio email reale osservato nei log dev, effetto immediato visto a schermo anziché solo via test automatico). Questi non sono gap di implementazione ma passi di validazione umana esplicitamente deferiti dal workflow di esecuzione. Si raccomanda di eseguirli prima di considerare la Fase 4 definitivamente chiusa.

---

_Verified: 2026-08-28T12:21:34Z_
_Verifier: Claude (gsd-verifier)_
