---
phase: 03-pro-dettaglio-sottocategorie
verified: 2026-08-27T00:00:00Z
status: human_needed
score: 9/9 must-haves verified (code) — 1 human checkpoint outstanding
overrides_applied: 0
overrides: []
human_verification:
  - test: "Flusso Pro end-to-end in browser (03-06-PLAN.md Task 3, checkpoint blocking-human)"
    expected: "Attivazione Pro -> dettaglio a range su /dettaglio-pro (e ora anche inline su home e su 'Le mie stime') -> domande mirate ricalcolano -> 'Scarica PDF dettagliato' -> Free/anonimo riceve 403/401 e nessun dato impresa in nessuna risposta"
    why_human: "Nessun commit 'docs: close human-verify gate (approved)' trovato dopo 03-06 (a differenza del precedente di Fase 2, commit d6aad86); il checkpoint blocking-human dichiarato nel piano 03-06 non risulta formalmente chiuso in STATE.md/git, anche se le 2 commit di rifinitura successive (146cdcb, 31c1371) sono coerenti con feedback raccolto da un uso live dell'app (5 fix puntuali: dettaglio inline home, apertura dettaglio da 'Le mie stime', totali a range, AccountMenu, fix teaser)"
  - test: "Generazione byte-level del PDF Pro (GET /me/stime/{id}/pdf-pro) su questa macchina Windows"
    expected: "Il PDF viene generato e scaricato correttamente (branding Slate/blue-600, badge PRO, sezioni per categoria/sottocategoria/voce a range, totali)"
    why_human: "WeasyPrint richiede il runtime nativo GTK3, assente su Windows dev (stesso limite ambientale accettato in Fase 2 con override utente su PDF-01); i 2 test byte-generating in test_pdf_pro.py restano SKIPPED (probe runtime OSError), la logica e i guard statici (anti-EstimationService, anti-leak, content-type/filename) sono invece verificati e verdi"
---

# Phase 3: Pro & dettaglio sottocategorie Verification Report

**Phase Goal:** L'utente Pro sblocca l'apertura per sottocategorie (a.1/a.2) con voci e quantità stimate dal motore parametrico, dietro paywall, con PDF dettagliato. Requirements: PRO-01, PRO-02, PRO-03, PDF-02.

**Verified:** 2026-08-27
**Status:** human_needed (tutta la logica di codice verificata; 1 checkpoint umano di Fase 3 non risulta formalmente chiuso, più il limite ambientale GTK3 già noto)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | L'utente Pro vede le sottocategorie con voci e quantità stimate; l'utente Free no | ✓ VERIFIED | Backend: `DettaglioProService.compute()` (`backend/app/services/dettaglio_pro.py:84-162`) itera Categoria→Sottocategoria→Voce con quantità stimata da coefficiente-per-mq/domanda-mirata/default-conteggio (`_quantita()` righe 164-181), sempre a range (`prezzo_min`/`prezzo_max` righe 119-120). Endpoint `GET /me/stime/{id}/dettaglio-pro` dietro `require_pro` (`backend/app/routers/dettaglio_pro.py:114-124`). Frontend: `DettaglioProView`/`SottocategoriaAccordion` rendono l'accordion per sottocategoria con righe-voce (descrizione · quantità+UM · `€ min – € max`); `CategoryCard` mostra la striscia teaser bloccata per Free (`isPro=false`, righe 34-47) e nessun teaser per Pro (Fix rifiniture, commit `31c1371`). Test: `test_oracolo_per_voce_coefficiente_qta_per_mq`, `test_domanda_mirata_*`, `test_sottocategoria_senza_voci_stimate_compare_comunque` in `test_dettaglio_pro.py`. |
| 2 | Il dettaglio Pro è ricostruito bottom-up ed è indipendente dal Free (non deve riconciliare) | ✓ VERIFIED | `dettaglio_pro.py` docstring esplicita: "questo modulo non importa alcuna classe del servizio di stima Fase 1". `test_service_non_importa_il_motore_free` (guard statico via `inspect.getsource`) e `test_render_pro_non_richiama_direttamente_estimation_service` (test_pdf_pro.py:230) confermano l'assenza di import incrociati. |
| 3 | Il dettaglio è correttamente protetto da paywall in base allo stato Pro dell'account | ✓ VERIFIED | `require_pro` (`backend/app/dependencies/auth.py:75-78`): 401 anonimo (via `get_current_user`), 403 Free autenticato. Applicato su tutti e 3 gli endpoint Pro (dettaglio GET/POST, pdf-pro). Ownership-filter `id`+`user_id` → 404 anti-IDOR (`_get_owned_stima`, righe 92-100), mai 403. Test: `test_dettaglio_pro_paywall.py` (matrice 401/403/200/404 su GET/POST), `test_pdf_pro.py` (401/403/404 su pdf-pro). Frontend: `DettaglioProPage`/`EstimatePage` reindirizzano non-Pro/anonimo a `/passa-a-pro`, ma il gate reale resta server-side (commento esplicito T-03-13 nel codice). |
| 4 | L'utente Pro scarica un PDF dettagliato brandizzato con le sottocategorie | ✓ VERIFIED (codice) — byte-render env-deferred | `GET /me/stime/{id}/pdf-pro` (`dettaglio_pro.py:146-167`) chiama lo STESSO `_compute_dettaglio()` del GET JSON (parità by-construction, non testata a posteriori) → `PdfService.render_pro()` → `pdf_stima_pro.html` (badge PRO, iterazione categoria→sottocategoria→voci a range, totali sottocategoria/categoria/generale, paginazione `@page`). `test_compute_dettaglio_usato_dal_pdf_pro_e_identico_al_get_json` prova la parità numerica esplicitamente. Byte-generation SKIPPED su Windows dev (GTK3 assente, stesso limite accettato in Fase 2) — vedi Human Verification. |

**Score:** 4/4 roadmap success criteria verificate a livello di codice (1 con deferral ambientale già precedentato in Fase 2).

### Deferred Items

Nessuno — tutti i truth appartengono alla Fase 3 stessa.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/subscription.py` | Tessera abbonamento (stato/scaduta_il/piano_code) | ✓ VERIFIED | Nessuna colonna prezzo/coefficiente impresa (D-10) |
| `backend/alembic/versions/0004_subscription.py`, `0005_dettaglio_pro.py` | Migrazioni Pro | ✓ VERIFIED | Catena 0001→0005 presente e coerente |
| `backend/app/dependencies/auth.py` | `require_pro`/`subscription_is_active` | ✓ VERIFIED | 401→403 layering, guard naive/aware datetime |
| `backend/app/routers/subscription.py` | `POST /me/pro/attiva` + `POST /admin/pro/attiva` | ✓ VERIFIED | Stub production-shaped, rate-limited, idempotente |
| `backend/app/models/dettaglio_pro.py` | `Sottocategoria`/`Voce`/`CoefficienteQuantitaVoce` | ✓ VERIFIED | Nessuna colonna margine impresa su `Voce` (D-10 strutturale, non solo di schema) |
| `backend/app/services/dettaglio_pro.py` | `DettaglioProService.compute()` | ✓ VERIFIED | Decimal puro, totali bottom-up sottocategoria/categoria/generale (righe 133-162, aggiunte con commit `146cdcb`) |
| `backend/app/schemas/dettaglio_pro.py` | DTO chiusi anti-leak | ✓ VERIFIED | `VoceOut`/`SottocategoriaOut`/`CategoriaDettagliataOut`/`DettaglioProOut` con `totale_min`/`totale_max` a ogni livello |
| `backend/app/routers/dettaglio_pro.py` | GET/POST dettaglio-pro + GET pdf-pro | ✓ VERIFIED | `_compute_dettaglio()` unico punto di calcolo condiviso, `require_pro` su tutte e 3 le rotte |
| `backend/app/services/pdf_service.py` (`render_pro`) + `backend/app/templates/pdf_stima_pro.html` | PDF Pro dettagliato | ✓ VERIFIED | Template multi-pagina con totali a ogni livello, nessuna stringa impresa |
| `frontend/src/api/dettaglio-pro.ts` | Client GET/POST/PDF + normalizzazione Decimal | ✓ VERIFIED | `getDettaglioPro`/`postRisposteDettaglioPro`/`scaricaPdfPro`, `totale_min`/`totale_max` normalizzati a ogni livello |
| `frontend/src/components/SottocategoriaAccordion.tsx` | Accordion righe-voce a range + subtotali | ✓ VERIFIED | Subtotale sottocategoria + totale categoria renderizzati (righe 41-58) |
| `frontend/src/components/DettaglioProView.tsx` | Vista dettaglio Pro condivisa | ✓ VERIFIED | Riusata da home (inline Pro), `/dettaglio-pro`, `/le-mie-stime`; totale generale renderizzato (righe 230-235) |
| `frontend/src/pages/DettaglioProPage.tsx` | Schermata dedicata `/dettaglio-pro?stima={id}` | ✓ VERIFIED | Redirect non-Pro/anonimo → `/passa-a-pro`, redirect stima mancante → `/le-mie-stime` |
| `frontend/src/routes/PassaAProPage.tsx` | Upgrade/attivazione stub Pro | ✓ VERIFIED | 3 stati (anonimo/non-Pro/già-Pro), prezzo esplicitamente placeholder (coerente con Out of Scope REQUIREMENTS.md) |
| `frontend/src/components/AccountMenu.tsx` | Badge Pro + voce di menu condizionale | ✓ VERIFIED | Free → "Passa a Pro"; Pro → "Contatta un consulente" (righe 69-77, commit `31c1371`) |
| `frontend/src/components/CategoryCard.tsx`, `SavedEstimateDetail.tsx` | Teaser bloccato solo per Free | ✓ VERIFIED | `isPro` prop propagata, nessun teaser mostrato ai Pro (fix bug esplicito in commento riga 17 di `SavedEstimateDetail.tsx`) |
| `frontend/src/pages/EstimatePage.tsx`, `frontend/src/routes/LeMieStimePage.tsx` | Pro vede dettaglio inline su home / apre dettaglio da storico | ✓ VERIFIED | `EstimatePage.tsx:126-148` (branch `user?.pro` → `DettaglioProView` invece delle CategoryCard); `LeMieStimePage.tsx:80-81` (branch `isPro` → `DettaglioProView` invece di `SavedEstimateDetail`) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `routers/dettaglio_pro.py` | `require_pro` | `Depends(require_pro)` su tutte e 3 le rotte | ✓ WIRED | Confermato da lettura diretta |
| `routers/dettaglio_pro.py` | `DettaglioProService.compute()` | `_compute_dettaglio()` condiviso GET/POST/pdf-pro | ✓ WIRED | Stessa funzione, stessi argomenti (listino/mq/tipo/risposte) — parità by-construction |
| `routers/dettaglio_pro.py` | `PdfService.render_pro()` | `GET pdf-pro` | ✓ WIRED | `result` dal calcolo condiviso passato al renderer |
| `main.py` | `subscription.router`, `dettaglio_pro.router` | `include_router(..., prefix="/api/v1")` | ✓ WIRED | Righe 39-40 `main.py` |
| `frontend/pages/EstimatePage.tsx` | `DettaglioProView` | `user?.pro` branch | ✓ WIRED | Righe 126-148 |
| `frontend/routes/LeMieStimePage.tsx` | `DettaglioProView` | `isPro` branch | ✓ WIRED | Righe 80-81 |
| `frontend/pages/DettaglioProPage.tsx` | `getDettaglioPro`/`scaricaPdfPro` | `DettaglioProView` (componente condiviso) | ✓ WIRED | Stesso componente per i 3 punti d'ingresso, nessuna divergenza possibile |
| `frontend/App.tsx` | `DettaglioProPage`, `PassaAProPage` | rotte `/dettaglio-pro`, `/passa-a-pro` | ✓ WIRED | Confermato in `App.tsx` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `DettaglioProView` | `dettaglioQuery.data` | `getDettaglioPro(stimaId)` → `GET /me/stime/{id}/dettaglio-pro` → `DettaglioProService.compute()` → query DB reali (`Sottocategoria`/`Voce`/`CoefficienteQuantitaVoce`, seed 191 voci/21 sottocategorie) | Sì | ✓ FLOWING |
| `SottocategoriaAccordion` (totali) | `sottocategoria.totale_min/max`, `categoria.totale_min/max` | Calcolati server-side in `DettaglioProService.compute()` come somma bottom-up (non hardcoded, testato con `test_totali_a_range_sommano_bottom_up`) | Sì | ✓ FLOWING |
| `pdf_stima_pro.html` | `dettaglio.*` | Stesso `_compute_dettaglio()` del GET JSON | Sì | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Suite backend completa | `cd backend && uv run pytest -q` (rieseguita da questo verificatore) | `107 passed, 4 skipped in 42.72s` | ✓ PASS |
| Typecheck frontend | `cd frontend && npx tsc --noEmit` (rieseguito da questo verificatore) | Nessun output (pulito) | ✓ PASS |
| Nessun leak impresa nei moduli Pro | `grep -rniE "coefficiente_impresa\|prezzo_impresa\|base_eur_mq" backend/app frontend/src` | 0 occorrenze nei moduli Pro (le uniche occorrenze restano nel motore Free `listino.py`/`estimation.py`/`stima.py`, dove il dato deve restare server-side per design) | ✓ PASS |
| Router Pro registrati | `grep include_router backend/app/main.py` | `subscription.router`, `dettaglio_pro.router` presenti | ✓ PASS |
| Catena migrazioni | `ls backend/alembic/versions/` | `0001..0005` presenti, coerenti col frontmatter dei piani | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|--------------|--------|----------|
| PRO-01 | 03-02, 03-03, 03-06 | Pro vede sottocategorie con voci e quantità stimate | ✓ SATISFIED | Motore bottom-up + accordion frontend, ora anche inline home/Le mie stime |
| PRO-02 | 03-01, 03-03, 03-04 | Dettaglio dietro paywall | ✓ SATISFIED | `require_pro` su tutti gli endpoint Pro, matrice 401/403/404 testata |
| PRO-03 | 03-01, 03-05 | Gestione stato Pro sull'account | ✓ SATISFIED | `Subscription` + stub attivazione production-shaped + `UserOut.pro` + `AccountMenu` badge/menu condizionale |
| PDF-02 | 03-04, 03-06 | PDF Pro dettagliato scaricabile | ✓ SATISFIED (codice) — byte-render env-deferred | `render_pro()`/template/endpoint completi e testati fino al livello parità-numerica; generazione byte reale non verificabile su questa macchina (vedi Human Verification) |

Nessun requisito orfano: tutti i 4 requisiti di Fase 3 sono mappati ai piani 03-01..03-06.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/routes/PassaAProPage.tsx` | 15 | `PRICE_PLACEHOLDER` (stringa copy, non codice non implementato) | ℹ️ Info | Intenzionale e documentato: REQUIREMENTS.md Out of Scope "Prezzo esatto abbonamento Pro — da definire prima del go-live"; D-07 production-shaped stub. Non è debito tecnico. |
| `backend/app/models/subscription.py` | 9 | "placeholder" nella docstring (riferito a `piano_code` nullable) | ℹ️ Info | Nota di design esplicita per un campo futuro, non un TODO/debt marker |

Nessun TBD/FIXME/XXX/HACK non referenziato trovato nei file modificati dalla Fase 3.

### Human Verification Required

1. **Flusso Pro end-to-end in browser** (03-06-PLAN.md, Task 3, checkpoint `blocking-human`)
   - **Test:** Da loggato non-Pro → "Passa a Pro" → attivazione stub → verificare badge Pro → aprire il dettaglio (ora disponibile inline in home, su `/dettaglio-pro` e da "Le mie stime") → rispondere alle domande mirate → verificare che le quantità cambino → "Scarica PDF dettagliato" → da un Free/anonimo verificare 403/401 su `dettaglio-pro`/`pdf-pro`.
   - **Expected:** Tutto il flusso funziona senza errori visivi/di navigazione; nessun dato impresa in nessuna risposta ispezionata da DevTools.
   - **Why human:** Non esiste, a differenza della Fase 2 (commit `d6aad86` "close human-verify gate"), un commit o una nota STATE.md che chiuda formalmente questo checkpoint per la Fase 3. Le 2 commit di rifinitura post-piano (`146cdcb`, `31c1371`) sono pero' fortemente indicative di un uso live effettivo (5 fix puntuali coerenti con problemi osservabili solo a schermo: dettaglio non mostrato inline, teaser mostrato erroneamente ai Pro, ecc.), quindi è probabile che la verifica sia già avvenuta informalmente — ma manca la conferma esplicita richiesta dal protocollo del checkpoint.

2. **Generazione byte-level del PDF Pro** (`GET /me/stime/{id}/pdf-pro`)
   - **Test:** Scaricare realmente il PDF Pro e ispezionarne il contenuto (branding, badge PRO, sezioni, totali, assenza di dati impresa nei byte).
   - **Expected:** PDF valido, ben formattato, coerente coi dati JSON.
   - **Why human:** WeasyPrint richiede GTK3 nativo, assente su Windows dev — stesso limite ambientale già accettato con override esplicito in Fase 2 (PDF-01). I test byte-generating restano SKIPPED (probe runtime), non falliti; la logica di calcolo/parità è invece verificata. Si raccomanda lo stesso trattamento (override utente esplicito) già usato in `02-VERIFICATION.md`, oppure verifica diretta su Railway/Debian.

### Gaps Summary

Nessun gap funzionale nel codice: tutti i 4 success criteria di roadmap e le 5 rifiniture richieste dall'utente post-piano (dettaglio inline home, apertura dettaglio da "Le mie stime", totali a range a ogni livello, AccountMenu Free/Pro, fix teaser) sono implementati, wired e coperti da test automatici (107/107 passed + 4 skip GTK3 invariati) e typecheck pulito. L'unico scostamento dal protocollo è procedurale: il checkpoint `blocking-human` del piano 03-06 (Task 3) non risulta formalmente chiuso con un commit/nota di approvazione, a differenza del precedente di Fase 2. Le commit di rifinitura successive suggeriscono fortemente che l'utente abbia già testato dal vivo e richiesto correzioni puntuali, ma manca la conferma esplicita. Si raccomanda: (a) far confermare esplicitamente all'utente il flusso end-to-end in browser (o registrare a posteriori l'approvazione già data a voce), (b) decidere se applicare alla generazione byte del PDF Pro lo stesso override già concesso in Fase 2 per PDF-01, data l'identica causa ambientale (GTK3 assente su Windows dev).

---

*Verified: 2026-08-27*
*Verifier: Claude (gsd-verifier)*
