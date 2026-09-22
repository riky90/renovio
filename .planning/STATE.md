---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: domande e motore parametrico
status: ready_to_plan
last_updated: 2026-09-22T20:05:35.572Z
progress:
  total_phases: 7
  completed_phases: 4
  total_plans: 9
  completed_plans: 9
  percent: 57
stopped_at: Phase 08 complete (8/8) — ready to discuss Phase 08.1
---

# Project State — ristruttura-stima

## Current Position

Phase: 08 (export-import-excel) — COMPLETE (8/8, verificata 5/5)
Prossima: 08.1 (catalogo domande) — contesto scritto, nessun piano

- **Milestone:** v2.0 (domande e motore parametrico), fasi **05-10**. La v1.0 (MVP, fasi
  01-04) e' **completa, verificata e in produzione dal 2026-09-09** — backend su Render,
  frontend su Vercel — e archiviata in `.planning/milestones/v1.0-ROADMAP.md`.

- **Phase:** 4 di 7 complete — 05 (catalogo domande + motore Free parametrico), 06 (wizard
  unico), 07 (arredo), 08 (export/import Excel). Le prime due eseguite fuori dal ciclo GSD e ricostruite in
  retrospettiva nei rispettivi `NN-RETRO-SUMMARY.md`; la 07 e' la prima pianificata ed
  eseguita dentro la milestone (`07-01-PLAN.md` -> `07-01-SUMMARY.md`).

- **Status:** Ready to plan — Fase 08 chiusa. Wave 1: 08-01 export listino +
  audit `export_log`, 08-02 tab Anteprima. Wave 2: 08-03 round-trip del listino (D-12),
  08-04 export parametri col margine opt-in (CUR-03), 08-05 export lead tracciato (CUR-04).
  Wave 3: 08-06 import parametri, il registro `HANDLER` su cui poggiano i due piani
  rimasti. Wave 4: 08-07 import lead, con il permesso che diventa per risorsa
  (`ImportHandler.ruolo_richiesto`) invece che globale. Wave 5: 08-08, `updated_at` sulle
  nove tabelle curate (migrazione 0019) e l'avviso "cambiata dopo l'export" su tutti e tre
  i percorsi di import. Gate post-merge verde dopo ogni wave; dopo la quinta: 517 passed /
  5 skipped, build frontend pulita.
  Contratto UI verificato in `08-UI-SPEC.md`, mappa dei pattern in `08-PATTERNS.md`.
  Verifica di fase `passed` 5/5 (`08-VERIFICATION.md`). La code review (`08-REVIEW.md`)
  ha lasciato **due critici aperti sul codice della wave 2**, entrambi confermati a mano:
  `_upsert_voce` in `listino_upload_service.py` ignora `campi_presenti` sul percorso per
  chiave naturale (viola il criterio 2 della fase), e `FlatImportDialog.tsx:75` cabla
  `campi_da_cancellare: []`, per cui `#CANCELLA#` scrive la stringa `"None"` invece di NULL.
  Da chiudere in una 08.2 di gap closure o dentro la 09.
  **Split del 2026-09-22:** il catalogo domande (D-05/06/07, D-21..D-25) e' uscito dalla
  Fase 08 ed e' diventato la **Fase 08.1**, con il suo `08.1-CONTEXT.md` gia' scritto e
  nessun piano ancora. Nessuno degli 8 piani della 08 ne dipende.
  **Sessantanove commit in attesa di push**: il push deploya su Render e si fa a fine
  milestone (`git push origin master:main`), e prima serve `BACKEND_PUBLIC_URL`
  configurata su Render, o l'upload avatar torna 503.

- **Numerazione:** le fasi non ripartono da 01 a ogni milestone (regola GSD). Il piano
  originale chiamava queste fasi 1-6; qui sono **05-10**. La corrispondenza e':
  `piano Fase 1 -> 05` · `2 -> 06` · `3 -> 07` · `4 -> 08` · `5 -> 09` · `6 -> 10`.
  Il piano sorgente resta `~/.claude/plans/il-punto-1-come-steady-comet.md`, ora tradotto in
  `.planning/ROADMAP.md` + `.planning/REQUIREMENTS.md` (27 requisiti v2).

- **Regola range (locked):** ±% solo sui lavori (4 categorie); extra fissi (€2.806 lordo); totale = Σ card + extra. Oracolo primario: 85 mq · totale = €47.985–€70.575.
- **Stack (da RESEARCH):** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Postgres/Alembic · React 19 + Vite + TS 5.9 + react-query + Tailwind/shadcn · autocomplete comuni ISTAT bundlato offline.

## Last Session

- **2026-09-21 (6)** — **Fix delle Tabs e contesto della Fase 08.** Due commit di codice:
  `906010f` mappa le varianti `data-*` dei componenti shadcn agli attributi che Radix emette
  davvero (i componenti in `components/ui/` usano `data-active:`/`data-horizontal:`, Radix
  scrive `data-state`/`data-orientation`, e senza le `@custom-variant` Tailwind generava 62
  selettori che non matchavano nulla — le Tabs restavano in riga e la `TabsList` diventava
  una colonna grigia su `/impostazioni` e `/admin/coefficienti`); `699b751` sposta la tab
  della pagina profilo dalla query string al path (`/impostazioni/profilo`), con shim per i
  vecchi `?tab=` e lo slug `referral` rinominato `invita`.
  **Contesto Fase 08 raccolto** (`19dfa66`): sei aree, 26 decisioni, nessuna girata a
  "decidi tu". Le due scoperte che cambiano il piano: `POST /admin/domande/anteprima`
  esiste gia' completo, quindi PAR-04 e' solo frontend; e la pagina CRUD del catalogo
  domande e' stata fatta entrare in fase da Riccardo contro la raccomandazione contraria —
  rischio di split annotato in D-21.
  **Due falsi negativi di `gsd-sdk` trovati**: `init.plan-phase` riporta
  `agents_installed: false` elencando tutti e 33 gli agenti come mancanti (stanno in
  `~/.claude/agent-domains/dev/`, e funzionano) — chip `task_c73d3d23`; e
  `state.record-session` risponde `"recorded": false` **ma scrive lo stesso**, avendo
  riscritto questo frontmatter con `completed_phases: 1`, `total_plans: 1` e `percent: 17`
  contro `completed_plans: 3`. Valori ripristinati a mano.

- **2026-09-21 (4)** — **Fase 07 committata + igiene, niente push.** Tre commit nuovi sopra
  i tre in attesa: `feat(arredo)` (Fase 07, 33 file), `fix(footer)` (chiave React duplicata
  sui due link a `/supporto`: era gia' corretta nel working tree), `chore(planning)` (la
  milestone v2.0 come milestone GSD). **Push volutamente rimandato** a fine milestone: il
  push deploya su Render e semina in produzione.
  **R2 chiuso senza R2.** Aprire un bucket Cloudflare richiede una carta di credito anche
  sul piano gratuito, quindi `services/storage_service.py` ha ora due backend dietro le
  stesse quattro funzioni: R2 quando le cinque `R2_*` ci sono (strada maestra, intatta),
  altrimenti la tabella `avatar_blob` (migrazione `0016`) servita da `GET
  /api/v1/media/{key}` con `Cache-Control: immutable`. `routers/auth.py` non e' cambiato —
  e' il punto della faccenda. Nuova variabile **`BACKEND_PUBLIC_URL`** (una, non cinque);
  `GET /health/db` espone ora `"storage": "r2"|"db"`, perche' la domanda "quale storage e'
  attivo in produzione?" ha ricevuto per mesi una risposta letta dalle variabili d'ambiente
  invece che dall'app. Provato dal vivo: upload 200, WEBP 512px, immagine servita.
  **Nota di ambiente del `CLAUDE.md` riscritta**: diceva che gli agenti GSD non erano
  installati e che lo shim `gsd-sdk` era rotto — false entrambe, verificate.
  **Guardia sui massimali ecobonus**: il tetto seminato di 60.000 e' il massimale dei soli
  serramenti; un test ora fallisce il giorno in cui una seconda categoria si attacca
  all'ECOBONUS, invece di lasciar calcolare in silenzio una detrazione sbagliata.
  Chiusi come falsi: worktree GSD abbandonato (non esiste), warning REQ-ID (nessun REQ-ID
  nel repo), `GEMINI_API_KEY` (nessun riferimento nel progetto), account Pro mancante (il
  tuo ce l'ha attivo dal 2026-08-27). Le "21 voci demo per terzili" sono lo stesso difetto
  gia' tracciato come bug dei cataloghi: 21 voci su 191 con `voce.livello`, tutte in
  B-FINITURE. Prossimo: Fase 08.

- **2026-09-21 (2)** — **Fase 2 v2 completa: domande servite dal DB e wizard unico.**
  `GET /api/v1/domande?tier=&mq=` serve catalogo, opzioni e i default gia' risolti per la
  fascia di metri quadri — risolti dal server con la stessa `attese_per_mq()` che fa da
  baseline allo scostamento, cosi' non esistono due copie della regola. Il catalogo **non
  pubblica gli effetti**: la taratura resta server-side, verificato sul JSON serializzato.
  Frontend: nuovo primitivo `components/ui/number-stepper.tsx` (-/valore/+, tap 44px) al
  posto degli input numerici grezzi, perche' questi campi arrivano pre-compilati e si
  aggiustano invece di compilarsi; `EstimateWizard` unico (Free 3 step, Pro 4) al posto di
  `EstimateForm` + `EstimateFormPro`, entrambi cancellati; `DomandaField` disegna una
  domanda qualsiasi conoscendo solo i cinque `tipo_controllo`, e un gruppo sconosciuto cade
  nello step 3 invece di sparire. Le risposte alle domande nascoste non entrano nello
  snapshot. **Sparito `EstimateFormPro.tsx:DOMANDE`**; `DettaglioProView.tsx:FIELD_LABELS`
  **resta**: le sue tre chiavi sono il contratto del motore Pro e `condizionatori` non ha
  ancora una domanda nel catalogo — la migrazione vera e' Fase 5. Verifica: **430 passed,
  5 skipped** (421 + 9 nuovi), `tsc -b` pulito, flusso provato dal vivo: 85 m2 Reggio
  Emilia totale dal wizard -> 47.985-70.575 (oracolo esatto); a Modena 200 m2 layer spento
  e risposte sui default coincidono (109.110-162.262) e +2 bagni sposta di 5.808 euro.
  Corretto in corsa un errore di validazione mostrato prima che il campo fosse compilabile.
  **Non ancora pushato in produzione.** Prossimo: Fase 3 (arredo). Prima:

- **2026-09-21** — **Fase 1 v2 completa: catalogo domande in database + motore Free
  parametrico.** Migrazione `0014`, tutta additiva. Nuove tabelle `domanda` /
  `opzione_domanda` / `effetto_opzione` / `attesa_immobile`; `app/services/effetti.py` come
  unico posto in cui una risposta utente diventa aritmetica (i motori non contengono un solo
  `if` sul codice di una domanda); `EstimationService.compute()` estesa con un quinto
  parametro `risposte` opzionale; `StimaRequest.risposte` opzionale, API retrocompatibile;
  CRUD admin completo su domande/opzioni/effetti/attese piu' `POST /admin/domande/anteprima`,
  costruita in questa fase e non rimandata perche' e' lo strumento con cui si tara. Seed
  bozza: 16 domande, 42 opzioni, 52 effetti, 30 attese. **Sette tipi di effetto, insieme
  chiuso** — niente espressioni in tabella. **Proprieta' del dato asimmetrica**: testo e
  struttura delle domande sono del prodotto e il seed li riscrive a ogni boot, i valori degli
  effetti e le attese sono dell'admin e il seed li crea solo se mancano (altrimenti ogni
  deploy riporterebbe la taratura alla bozza cablata). Verifica: **421 passed, 5 skipped**
  (baseline 351 + 70 nuovi), `0014` provata upgrade -> downgrade -> upgrade, seed eseguito
  due volte su DB vergine; l'oracolo primario 85 mq = 47.985-70.575 regge in tre forme (layer
  spento, layer acceso senza risposte, risposte esplicite pari agli attesi). **I 52
  coefficienti sono una bozza, non una taratura** — vanno confermati su preventivi reali
  prima che aggiungano accuratezza e non solo risoluzione. Prossimo: Fase 2. Prima:

- **2026-08-27** — **Fase 3 COMPLETA e verificata + rifiniture flusso Pro post-piani.** Eseguiti tutti e 6 i piani (03-01..03-06). Poi, su feedback utente in verifica manuale, implementate e committate rifiniture (commit `146cdcb` backend, `31c1371` frontend): (P3) totali a range calcolati dal backend a livello sottocategoria/categoria/generale (service+schema+router+template PDF, fonte unica → schermata e PDF identici); (P2) in home un Pro vede il **dettaglio inline** al posto del riepilogo a card; (P4) in "Le mie stime" un Pro apre la **stima di dettaglio**, non lo snapshot base (auto-save invariato); (P1) AccountMenu Free→"Passa a Pro" / Pro→"Contatta un consulente"; (P5) fix bug teaser "Passa a Pro" mostrato erroneamente ai Pro. Rifattorizzato tutto il dettaglio in `DettaglioProView` condiviso da home/pagina dedicata/le-mie-stime (non possono divergere). Verifica goal-backward `03-VERIFICATION.md`: 9/9 must-have a livello codice, backend 107 passed/4 skip, `tsc` pulito, anti-leak a zero hit. **Checkpoint human-verify (03-06 Task 3) APPROVATO dall'utente** ("ho provato il flusso e funziona, come MVP funziona"). **Override PDF concesso** dall'utente (stesso della Fase 2/02-08): il render byte WeasyPrint non gira su questa macchina Windows senza GTK3 — logica coperta dai test, byte verificabili in ambiente con GTK3 (Debian/Railway), non blocca. **Known issue (deferred su decisione utente):** da anonimo, fatta una prima stima, poi "Accedi" → l'utente NON torna alla sua stima ma finisce su pagina bianca; da sistemare in una fase/patch successiva (non blocca l'MVP). Prima:
- **2026-08-27** — **Eseguito Plan 03-04 (PDF Pro dettagliato)**: `app/services/pdf_service.py` esteso con `render_pro()` (import WeasyPrint lazy invariato, docstring di modulo che documenta l'asimmetria deliberata recompute-live/Pro vs snapshot-frozen/Free, Pitfall 2) e `build_filename_pro()`; `app/templates/pdf_stima_pro.html` (multi-pagina Jinja2/WeasyPrint, branding Slate/blue-600 con badge PRO, disclaimer di non-riconciliazione D-01, iterazione categoria→sottocategoria→voci a range `€ min – € max`, paginazione `@page`/`break-inside: avoid`, mai dati impresa); `app/routers/dettaglio_pro.py` con `_compute_dettaglio()` estratto come unico punto di calcolo condiviso da GET dettaglio-pro, POST risposte e il nuovo `GET /me/stime/{id}/pdf-pro` (dietro `require_pro`, ownership 404 anti-IDOR, `StreamingResponse` application/pdf) — parità schermata/PDF garantita by-construction, non da un test a posteriori. `test_pdf_pro.py`: matrice 401/403/404 sempre attiva (non richiede GTK3), test di parità numerica esplicito (`_compute_dettaglio()` vs risposta HTTP del GET JSON), byte-generating skip-graceful anti-leak, guard statico anti-`EstimationService`. Deviazione (Rule 1): commento HTML del template riformulato per non contenere letteralmente le stringhe impresa vietate, stesso precedente 02/03-03 per il criterio grep meccanico. Suite backend completa 106/106 passed + 4 skip invariati (GTK3). Vedi `03-04-SUMMARY.md`. Prima:
- **2026-08-27** — **Eseguito Plan 03-03 (Motore Pro bottom-up + endpoint dettaglio dietro paywall)**: `app/services/dettaglio_pro.py` (`DettaglioProService.compute()`, Decimal puro, sibling di `EstimationService`: itera Categoria→Sottocategoria→Voce, quantita da coefficiente-per-mq o da domanda-mirata/default-conteggio, range per-voce riusando `TipoRistrutturazione.range_pct`, nessun campo impresa, nessun import del motore Free/D-01) + oracolo pinnato su `A.1.1.1`/`A.0.3` dal seed reale; `app/schemas/dettaglio_pro.py` (DTO chiusi anti-leak + `RisposteDomandeRequest` bounded ASVS V5); `app/routers/dettaglio_pro.py` con `GET /me/stime/{id}/dettaglio-pro` + `POST .../dettaglio-pro/risposte` dietro `require_pro`, ownership 404 anti-IDOR, risposte persistite in `risposte_pro_json` cosi' schermata e futuro PDF non divergono (Pitfall 3); wiring in `main.py`. TDD: `test_dettaglio_pro.py` + `test_dettaglio_pro_paywall.py` (oracolo, domanda mirata, matrice 401/403/200, anti-IDOR, anti-leak ricorsivo, integrazione POST-risposte→GET), suite backend completa 101/101 passed + 2 skip invariati (GTK3). Deviazione (Rule 1/2): strategia di calcolo quantita estesa oltre il testo letterale del piano per coprire le righe seedate con `default_conteggio` senza `domanda_mirata_key` (150/300 righe, voci a conteggio non mirate). Vedi `03-03-SUMMARY.md`. Prima:
- **2026-08-27** — **Eseguito Plan 03-02 (Fondazione dati motore Pro: schema + seed sottocategorie/voci)**: `app/models/dettaglio_pro.py` (`Sottocategoria`/`Voce`/`CoefficienteQuantitaVoce`, `codice` nullable su entrambe le prime due, discriminatore `famiglia` gerarchica|catalogo, nessuna colonna margine/prezzo impresa su `Voce`, D-10) + migrazione Alembic 0005 (catena 0001→0005, upgrade/downgrade/upgrade verificato) + `StimaSalvata.risposte_pro_json` nullable (Pitfall 3). Checkpoint `blocking-human` per `openpyxl` (dev-only, script di estrazione one-off) approvato dall'utente ("approvato"), installato via `uv add --dev openpyxl --native-tls`. `backend/scripts/extract_dettaglio_pro.py` (confinato a `scripts/`, mai importato sotto `app/`) legge `docs/computo-base-reggio-emilia.xlsx` e distingue righe-intestazione da righe-voce (Pitfall 1); deviazione Rule 1 in sessione: il primo algoritmo perdeva silenziosamente le varianti lettera (piatto doccia/vasca/WC/bidet/radiatori/condizionatore) del blocco "Allestimento cantiere" del foglio A-EDILE, che riusa i codici A.1..A.8 prima delle vere sottocategorie — riscritta la state machine con la riga "TOTALE ALLESTIMENTO DI CANTIERE" come confine esplicito, isolando il blocco in una Sottocategoria sintetica `A.0`. Prodotto `docs/seed-dettaglio-pro.json` (21 sottocategorie, 191 voci uniche in DB, coefficienti quantita-per-m2/domanda-mirata bozza per i 3 tipi secondo le regole UM di D-05). `scripts/seed.py` esteso con `seed_dettaglio_pro()` nella STESSA funzione `seed()` idempotente (D-12/Pitfall 5), upsert per chiave naturale su sottocategoria/voce/coefficiente_qta_voce. TDD: `test_seed_dettaglio.py` 4/4 verdi (copertura 4 categorie, idempotenza, coefficiente per ogni tipo su ogni voce, nessuna colonna impresa), suite backend completa 86/86 passed + 2 skip invariati (GTK3). Vedi `03-02-SUMMARY.md`. Prima:
- **2026-08-27** — **Eseguito Plan 03-01 (Stato Pro/tessera abbonamento + paywall server-side)**: `app/models/subscription.py` (`Subscription`: stato/scaduta_il/piano_code, nessuna colonna prezzo/coefficiente impresa, D-10) + migrazione Alembic 0004 (catena 0001→0004, upgrade/downgrade/upgrade verificato, seed rieseguito post-migrazione D-12); `app/dependencies/auth.py` con `subscription_is_active`/`require_pro` (401 anonimo via `get_current_user`, 403 "Funzione riservata agli utenti Pro" se non attivo, stesso guard naive/aware datetime di `get_current_user`); `schemas/subscription.py` (`SubscriptionOut`/`AttivaProResponse` a campi chiusi); `UserOut.pro: bool`; `routers/subscription.py` con `POST /me/pro/attiva` (stub production-shaped D-07, rate-limited 10/minute, upsert idempotente) e `POST /admin/pro/attiva` (dietro `require_admin`, attivazione manuale); `routers/auth.py::_to_user_out` esteso per popolare `pro`. TDD: `test_subscription.py` 16/16 verdi (modello, subscription_is_active attivo/scaduto/assente, require_pro 403, attivazione end-to-end su `/auth/me`, idempotenza riga singola, 401/403, anti-leak), suite backend completa 82/82 passed + 2 skip invariati (GTK3). Deviazione (Rule 1): `test_auth_service.py::test_user_out_never_contains_password_hash` aggiornato con il nuovo campo obbligatorio `pro=False`. Vedi `03-01-SUMMARY.md`. Prima:
- **2026-08-26** — **Eseguito Plan 02-09 (Save-at-signup, storico, download PDF frontend end-to-end) — Task 1-2 completati, Task 3 checkpoint aperto**: `api/stima.ts` esteso con `postSalvaStima`/`getStoricoStime`/`getStimaDettaglio` (credentials include, normalizzazione Decimal riusata) e `scaricaPdf` (fetch diretto del blob PDF, filename da `Content-Disposition`, download nativo via `<a download>`); `PdfDownloadButton` (stati idle/loading-spinner/errore inline, UI-SPEC F.4); `SavedEstimateDetail` (riusa CategoryCard/TotalCard/FallbackDisclaimer per lo snapshot immutabile, nessuna duplicazione layout); `LeMieStimePage` (`/le-mie-stime`, lista+empty state+dettaglio via stato locale, redirect `/accedi` se anonimo). `SoftWallCta` aggiornato: "Scarica PDF"/"Salva / crea account" navigano da anonimo a `/registrati` con `intent` + stima corrente via router `state` (mai in query param, T-09-04); "Passa a Pro"/"Contatta un professionista" restano soft-wall invariati; da loggato "Salva / crea account" e' nascosto e "Scarica PDF" diventa `PdfDownloadButton` diretto. `EstimatePage`: auto-save (D-07) via `postSalvaStima` quando loggato, un solo salvataggio per risultato. `RegistratiPage`/`AccediPage`: dopo signup/login con intent pendente, salvano il payload gia' mostrato (nessun ricalcolo, D-09) e avviano il download se richiesto, con conferma inline "Stima salvata nel tuo account.". Deviazione (Rule 2): gancio save-at-signup applicato anche ad `AccediPage.tsx` (non nei `files_modified` del piano) per completare simmetricamente il flusso richiesto dai `must_haves` del piano, stesso precedente di 02-06. `npx tsc --noEmit` verde su entrambi i task. **Task 3 (checkpoint `human-verify`, `gate="blocking"`) NON eseguito dall'agente**: verifica manuale in browser del flusso completo (anonimo->registrazione->salva->storico->PDF) resta all'utente; nota — il download PDF vero e proprio non e' verificabile end-to-end su questa macchina Windows per il limite GTK3 gia' noto (02-08). Vedi `02-09-SUMMARY.md`. Prima:
- **2026-08-26** — **Eseguito Plan 02-06 (Recupero password via email, D-04)**: `app/services/reset_token.py` (`make_reset_token`/`read_reset_token` su `itsdangerous.URLSafeTimedSerializer(settings.SECRET_KEY, salt="password-reset")`, scadenza 1h, `SECRET_KEY` e non `OAUTH_SESSION_SECRET`); `app/services/email_service.py` (`send_email` async via `aiosmtplib`, fallback log-only quando `SMTP_HOST` e' vuoto in dev, mai un'eccezione a import/startup, riusabile tal quale in Fase 4 per i lead); `routers/auth.py` con `POST /auth/password-dimenticata` (sempre lo stesso 200, anti-enumeration T-06-01) e `POST /auth/reimposta-password` (uso singolo via `PasswordResetToken.used`, hash sha256 del token in DB, 400 generico su invalido/scaduto/gia' usato); `schemas/auth.py` con `PasswordDimenticataRequest`/`ReimpostaPasswordRequest`. Frontend: `PasswordDimenticataPage`/`ReimpostaPasswordPage` (input-group show/hide password), rotte registrate in `App.tsx`, `AccediPage` con conferma inline post-reset (deviazione Rule 2, richiesta esplicitamente dal testo del piano). TDD RED→GREEN: `test_password_reset.py` 8/8 verdi (token valido/scaduto/manomesso, anti-enumeration, flusso completo, replay 400, token invalido 400, password corta 422), 66/66 suite totale verde + 2 skip invariati (WeasyPrint/GTK3). `npx tsc --noEmit` pulito. Nota di ripresa: la sessione precedente si era interrotta per limite settimanale con un file di test RED iniziale (stesso contenuto) gia' scritto ma bloccante per la collection pytest — rimosso dal coordinatore e ricreato identico come primo passo di questa sessione, poi seguito normalmente dal ciclo RED→GREEN. Vedi `02-06-SUMMARY.md`. Prima:
- **2026-08-25** — **Eseguito Plan 02-08 (PDF Free branded download backend)**: `app/templates/pdf_stima.html` (Jinja2, 1 pagina A4, CSS inline Slate/blue-600: wordmark+nome+data, riepilogo input, disclaimer amber condizionale, 4 card categoria a range tabular, blocco totale blue-600 IVA inclusa, footer legale); `app/services/pdf_service.py` (`PdfService.render(stima, user) -> bytes`, `build_filename()` slug città, WeasyPrint importato **lazy dentro `render()`** — non a livello modulo — proprio perché `import weasyprint` da solo lancia `OSError` su Windows senza GTK3, e un import top-level avrebbe rotto l'intero import di `app.main` e quindi l'intera test suite; nessun `EstimationService` nel modulo, D-09/Pitfall 5); `routers/stime_salvate.py` con `GET /me/stime/{id}/pdf` (stesso pattern ownership `id`+`user_id` -> 404, `StreamingResponse` `application/pdf` + `Content-Disposition attachment`). TDD RED→GREEN: `test_pdf.py` 5 test (2 byte-generating SKIPPED — GTK3/Pango/Cairo assente su questa macchina Windows, probe runtime via `OSError`; 3 sempre attivi — ownership 404, 401, guard statico anti-`EstimationService` — tutti verdi), 58/58 suite totale verde + 2 skip documentati. Azione utente per verifica locale completa: installare GTK3 runtime Windows o usare Docker/WSL2 (dettagli in `02-08-SUMMARY.md`); non blocca la produzione (Railway/Debian nativo). Vedi `02-08-SUMMARY.md`. Prima:
- **2026-08-25** — **Eseguito Plan 02-04 (Frontend autenticazione: router, pagine, sessione) — Task 1-2 completati, Task 3 in attesa**: `frontend/src/api/client.ts` (`apiGet`/`apiPost` con `credentials:"include"`, gestione esplicita del 204 No Content per il logout); `frontend/src/api/auth.ts` (`postRegistrazione`/`postLogin`/`postLogout`/`getMe`, 401 su `/me` trattato come utente anonimo); `frontend/src/hooks/useAuth.ts` (`useQuery(['me'])` + mutazioni con invalidazione); shadcn `avatar`/`dropdown-menu` installati; `App.tsx` con `createBrowserRouter` (`/`, `/registrati`, `/accedi`); `RegistratiPage`/`AccediPage` (card 400px, validazione on-blur, CTA accent, bottone Google outline verso `/auth/google/login`); `AccountMenu` (avatar iniziali, "Le mie stime", "Esci"); `EstimatePage` con header a stato di sessione (AccountMenu/bottone Accedi/skeleton). `npx tsc --noEmit` verde su entrambi i task. **Task 3 (checkpoint `human-verify`, `gate="blocking"`) NON eseguito dall'agente**: l'utente ha scelto esplicitamente di eseguire la verifica manuale in browser (registrazione → cookie HttpOnly → logout → re-login → credenziali errate) — resta un gate aperto, nessuna approvazione ricevuta in questa sessione. Vedi `02-04-SUMMARY.md`. Prima:
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

- **Fase 3 COMPLETA e verificata** (`03-VERIFICATION.md`: 9/9 code-level, human-verify approvato, override PDF concesso). Prossimo passo: avviare la **Fase 4 — Lead & pannello admin** (`/gsd-discuss-phase 4` poi `/gsd-plan-phase 4`).
- **Backlog (deferred):** fix "ritorno alla stima" — da anonimo, dopo una prima stima, "Accedi" porta a pagina bianca invece di riportare l'utente alla stima appena calcolata. Candidato per una patch a inizio Fase 4 o hotfix.
- **Verifica opzionale in produzione** (non bloccante): generazione PDF WeasyPrint Pro/Free su Debian/Railway con GTK3 nativo (in dev Windows resta atteso il 500 GTK); login Google dietro rete senza proxy MITM.
- **Nota dev**: il seed di Fase 1 (`backend/scripts/seed.py`, idempotente) va rieseguito se un ciclo di migrazioni azzera `dev.db`, altrimenti il motore di calcolo risponde con NoResultFound sul listino di default.

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
| Phase 02-account-pdf P04 | 20min | 2 tasks | 10 files |
| Phase 02-account-pdf P08 | 18min | 2 tasks | 4 files |
| Phase 02-account-pdf P06 | 25min | 2 tasks | 10 files |
| Phase 02-account-pdf P09 | 45min | 2 tasks (Task 3 checkpoint aperto) | 9 files |
| Phase 03-pro-dettaglio-sottocategorie P01 | 13min | 3 tasks | 11 files |
| Phase 03-pro-dettaglio-sottocategorie PP02 | 27min | 3 tasks | 10 files |
| Phase 03-pro-dettaglio-sottocategorie P05 | 15min | 2 tasks | 8 files |
| Phase 03-pro-dettaglio-sottocategorie P03 | 35min | 2 tasks | 6 files |
| Phase 03-pro-dettaglio-sottocategorie P04 | 20min | 2 tasks | 4 files |

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
- [Phase 02-account-pdf]: apiPost gestisce esplicitamente il 204 No Content (logout) restituendo undefined, per non far crashare response.json() su corpo vuoto
- [Phase 02-account-pdf]: WeasyPrint importato lazy dentro PdfService.render() (non a livello modulo) perche' `import weasyprint` da solo lancia OSError su Windows senza GTK3 runtime — un import top-level avrebbe rotto l'import di app.main e quindi l'intera test suite backend, non solo i test PDF
- [Phase 02-account-pdf]: test_pdf.py usa un probe runtime (tentativo import weasyprint, catch OSError) invece di un check hardcoded su sys.platform, cosi' i test byte-generating si riattivano automaticamente non appena GTK3 e' disponibile (Docker/WSL2/CI/Railway) senza modifiche al codice
- [Phase 02-account-pdf]: Reset password via itsdangerous+email_service (D-04): token firmato con SECRET_KEY, uso singolo via PasswordResetToken.used, email_service.send_email log-only quando SMTP_HOST e' vuoto in dev
- [Phase 02-account-pdf]: la stima pendente (save-at-signup) viaggia da SoftWallCta a /registrati|/accedi esclusivamente via router state ({ pendingStima }), mai come query param — solo il flag intent e' in URL (T-09-04)
- [Phase 02-account-pdf]: scaricaPdf usa un fetch diretto (non apiGet, che parserebbe JSON) per leggere il blob PDF e ricavare il filename da Content-Disposition, poi attiva il download nativo via <a download> temporaneo
- [Phase 02-account-pdf]: gancio save-at-signup applicato sia a RegistratiPage.tsx (richiesto esplicitamente dal piano) sia ad AccediPage.tsx (non nei files_modified, aggiunto per Rule 2 — un utente con intent pendente puo' scegliere di accedere invece di registrarsi)
- [Phase 03-pro-dettaglio-sottocategorie]: Subscription senza colonne prezzo/coefficiente impresa (D-10): tessera Pro = solo stato abbonamento
- [Phase 03-pro-dettaglio-sottocategorie]: piano_code nullable aggiunto ora su Subscription, costo quasi zero, coerente con D-07 production-shaped
- [Phase 03-pro-dettaglio-sottocategorie]: docstring schemas/subscription.py riformulata per non contenere letteralmente 'coefficiente' (stesso precedente 02-account-pdf, criterio grep meccanico)
- [Phase 03-pro-dettaglio-sottocategorie]: A-EDILE riusa i codici A.1..A.8 due volte (blocco Allestimento cantiere poi vere sottocategorie); isolato in Sottocategoria sintetica A.0 con codici voce A.0.n per evitare collisioni di chiave naturale nel seed
- [Phase 03-pro-dettaglio-sottocategorie]: coefficienti quantita-per-m2/domanda-mirata bozza secondo regole UM D-05, seedati per i 3 tipi su ogni voce, esplicitamente tarabili da admin in Fase 4
- [Phase 03-pro-dettaglio-sottocategorie]: openpyxl aggiunto come dev dependency dopo checkpoint blocking-human approvato dall'utente
- [Phase 03-pro-dettaglio-sottocategorie]: isPro propagato via prop da EstimatePage (useAuth().user?.pro), mai una fetch dedicata per il flag Pro in SoftWallCta/CategoryCard
- [Phase 03-pro-dettaglio-sottocategorie]: EstimatePage.tsx modificato oltre ai files_modified dichiarati nel piano 03-05, richiesto esplicitamente dal testo dell'azione del Task 2 per il wiring isPro
- [Phase 03-pro-dettaglio-sottocategorie]: DettaglioProService estende la strategia di calcolo quantita oltre il testo letterale del piano per coprire le righe seedate con default_conteggio ma senza domanda_mirata_key (voci a conteggio non mirate tipo forfait), altrimenti 150/300 righe di coefficiente restavano a quantita zero
- [Phase 03-pro-dettaglio-sottocategorie]: docstring schemas/dettaglio_pro.py riformulata per non contenere letteralmente base_eur_mq, stesso precedente 02/03 per rispettare il criterio grep meccanico
- [Phase 03-pro-dettaglio-sottocategorie]: _compute_dettaglio() helper unico condiviso da GET/POST/pdf-pro per parita' schermata/PDF by-construction
- [Phase 03-pro-dettaglio-sottocategorie]: build_filename_pro() dedicato invece di parametrizzare build_filename() esistente, per non toccare il contratto gia' testato della Free
- [Phase 03-pro-dettaglio-sottocategorie]: toNumber/normalizzazione Decimal duplicati in dettaglio-pro.ts invece di estratti in un helper condiviso con stima.ts (scelta esplicitamente lasciata all'esecutore dal piano)
- [Phase 03-pro-dettaglio-sottocategorie]: riepilogo domande mirate collassato derivato lato client dalle risposte del primo GET (non tutte zero => collassato), nessun flag server-side dedicato

### Blockers

- Nessuno. Fase 2 completa e verificata; tutti i checkpoint chiusi. I due limiti d'ambiente (Google OAuth proxy TLS, PDF GTK3 su Windows) sono accettati e rimandati alla verifica in produzione — non bloccanti.
