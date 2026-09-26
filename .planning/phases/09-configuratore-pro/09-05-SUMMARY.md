---
phase: 09-configuratore-pro
plan: 05
subsystem: api
tags: [fastapi, pydantic, react, catalogo-domande, motore-pro, weasyprint]

# Dependency graph
requires:
  - phase: 09-configuratore-pro plan 03
    provides: "risolvi_effetti_pro()/RisoluzionePro in effetti.py, DettaglioProService.compute() che legge gli assi dal catalogo (non piu' voce.livello/domanda_mirata_key)"
  - phase: 09-configuratore-pro plan 04
    provides: "migrazione 0021 (asse finitura + stepper mirati da curatela esistente), catalogo Pro popolato su qualunque ambiente esistente"
provides:
  - "domande_configuratore()/valida_risposte_pro() in services/dettaglio_pro.py: le domande del pannello con valore GIA' risolto (D-07), validazione generica contro il catalogo"
  - "DettaglioProResult.domande / DomandaProOut / OpzioneProOut: DTO chiuso per il pannello, nessun effetto/coefficiente esposto"
  - "RisposteDomandeRequest generico ({risposte: {codice: valore}, livelli}, extra=forbid) al posto di bagni/porte/condizionatori cablati"
  - "PDF Pro: riga di riepilogo per ogni domanda a scelta del configuratore, letta da dettaglio.domande"
  - "DettaglioProView.tsx: pannello 'Qualche dettaglio in piu'' su DomandaField (pavimento + tre stepper), DomandaField.tsx con prop griglia opzionale"
affects: [09-06, 09-07, 09-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Il pannello 'Qualche dettaglio in piu'' legge le sue domande dallo stesso catalogo del wizard (query su EffettoOpzione.tipo_effetto IN TIPI_EFFETTO_PRO), non da un elenco cablato: una domanda futura col giusto effetto compare da sola"
    - "Contratto POST generico ({risposte: dict, livelli}) validato in due stadi: il tipo Risposte condiviso col wizard limita la FORMA (ge/le/max_length), valida_risposte_pro valida il CONTENUTO contro il catalogo (quali codici, quali opzioni) — stesso schema, due responsabilita' distinte"

key-files:
  created: []
  modified:
    - backend/app/services/dettaglio_pro.py
    - backend/app/schemas/dettaglio_pro.py
    - backend/app/routers/dettaglio_pro.py
    - backend/app/templates/pdf_stima_pro.html
    - backend/tests/test_dettaglio_pro.py
    - backend/tests/test_dettaglio_pro_livelli.py
    - backend/tests/test_dettaglio_pro_paywall.py
    - backend/tests/test_no_leak.py
    - backend/tests/test_pdf_pro.py
    - frontend/src/api/dettaglio-pro.ts
    - frontend/src/components/DettaglioProView.tsx
    - frontend/src/components/DomandaField.tsx

key-decisions:
  - "domande_configuratore() risolve il valore SEMPRE (risposta salvata se valida, altrimenti default di catalogo): il client non deve mai interpretare un campo vuoto, coerente con D-07"
  - "L'eco di risposte nel DTO resta SOLO row.risposte_pro_json (mai le risposte del wizard): _compute_dettaglio le combina per il MOTORE (vince il Pro sulle stesse chiavi) ma il pannello mostra solo cio' che l'utente ha risposto nel pannello stesso"
  - "-1 su una domanda numerica esce 422 (bound ge=0 del tipo Risposte condiviso col wizard) invece di 400: il catalogo valida il CONTENUTO, lo schema condiviso gia' vieta la FORMA negativa prima ancora di arrivarci — stesso esito pratico (rifiutato)"
  - "bool su una domanda numerica (es. bagni: true) puo' essere accettato con coercizione a 1 dal tipo Risposte condiviso (bool e' int in Python): debolezza pre-esistente del tipo riusato dal wizard, non introdotta da questo piano — non corretta qui per restare nello scope del piano"
  - "Test del PDF Pro renderizzano il template Jinja2 direttamente (pdf_service._env), mai render_pro()/WeasyPrint: verificano la riga del pavimento senza il runtime GTK3 nativo, che su questa macchina Windows non c'e'"

requirements-completed: [CFG-01, QST-05]

# Metrics
duration: ~1h40m
completed: 2026-09-26
---

# Phase 09 Plan 05: Configuratore Pro sul pannello "Qualche dettaglio in piu'" Summary

**Il pannello "Qualche dettaglio in piu'" diventa il configuratore Pro: le domande (pavimento + tre stepper) arrivano dal catalogo con i valori gia' risolti sui default, il payload POST e' generico e validato contro il catalogo, e il PDF Pro riporta il pavimento scelto dalla stessa fonte della schermata.**

## Performance

- **Duration:** ~1h40m
- **Tasks:** 3/3
- **Files modified:** 12

## Accomplishments

- `domande_configuratore()` (nuovo, in `dettaglio_pro.py`) trova le domande con almeno un effetto Pro attivo (`TIPI_EFFETTO_PRO`) su un'opzione attiva — esclusa `finitura` — e risolve il valore di ognuna: la risposta salvata se valida, altrimenti il default di catalogo (opzione `is_default` o l'atteso di `attesa_immobile` per gli stepper). `DettaglioProResult.domande` e' popolato da `compute()` a ogni chiamata.
- `valida_risposte_pro()` valida il payload generico contro lo stesso elenco: chiave non prevista -> 400 col nome della domanda, numero fuori 0..99 -> 400, opzione inesistente -> 400.
- `RisposteDomandeRequest` diventa `{risposte: dict[codice, valore], livelli}` con `extra="forbid"` — i tre campi cablati bagni/porte/condizionatori sono spariti dal contratto HTTP; il salvataggio del wizard (`PreferenzeProIn`) resta invariato, scrive le stesse chiavi.
- `_compute_dettaglio()` combina le risposte del wizard (dallo snapshot, `risultato_json["input"]["risposte"]`) con quelle del pannello Pro per il MOTORE (vince il Pro sulle chiavi in comune), ma l'eco che il client vede resta solo `risposte_pro_json` — il pannello e il wizard hanno ciascuno il proprio contratto, senza confonderli.
- Il PDF Pro aggiunge una riga di riepilogo per ogni domanda a scelta del configuratore (oggi: il pavimento), letta da `dettaglio.domande` — zero calcolo nel template, `pdf_service.py` invariato (`git diff` vuoto).
- Il pannello frontend disegna il pavimento (griglia 2x2 fissa, UI-SPEC A.2) e i tre stepper con `DomandaField`, niente piu' `FIELD_LABELS`/`<Input>`/validazione testuale: `NumberStepper` rende uno stato non valido strutturalmente impossibile. Il riepilogo collassato usa una mappa di sola presentazione (`ETICHETTE_RIEPILOGO`) con fallback a `domanda.testo`.
- Anti-leak esteso: `test_no_leak.py` verifica ora che nessuna CHIAVE del GET/POST dettaglio-pro contenga `effett`/`coefficiente`/`impresa`/`tipo_effetto`/`target_` (controllo sulle chiavi, non sul testo libero delle descrizioni voce, che contengono legittimamente parole come "effettuato").

## Task Commits

1. **Task 1: contratto API generico e domande del configuratore** - `5dbfdf7` (feat)
2. **Task 2: pavimento scelto nel PDF Pro** - `75835ed` (feat)
3. **Task 3: pannello "Qualche dettaglio in piu'" su DomandaField** - `9b17979` (feat)

## Files Created/Modified

- `backend/app/services/dettaglio_pro.py` - `OpzioneConfiguratore`/`DomandaConfiguratore`, `domande_configuratore()`, `valida_risposte_pro()`, `RisposteNonValide`; `DettaglioProResult.domande` popolato in `compute()`
- `backend/app/schemas/dettaglio_pro.py` - `DomandaProOut`/`OpzioneProOut`, `RisposteDomandeRequest` generico (`extra="forbid"`), `RisposteDomandeOut` rimossa, `DettaglioProOut.risposte` diventa `dict[str, int | str]`
- `backend/app/routers/dettaglio_pro.py` - `_compute_dettaglio` combina wizard+pannello per il motore; `_to_out` mappa `domande` campo-per-campo; il POST valida con `valida_risposte_pro`
- `backend/app/templates/pdf_stima_pro.html` - riga di riepilogo per ogni domanda a scelta con `valore_etichetta`, letta da `dettaglio.domande`
- `backend/tests/test_dettaglio_pro.py` - payload aggiornati a `{risposte: {...}}`, nuovi test su ordine/default delle domande e sul payload generico (chiave sconosciuta, opzione inesistente, numero fuori limite)
- `backend/tests/test_dettaglio_pro_livelli.py` / `test_dettaglio_pro_paywall.py` - payload HTTP aggiornati al nuovo contratto
- `backend/tests/test_no_leak.py` - nuovo test anti-leak sul GET/POST dettaglio-pro (controllo su chiavi, non su substring di testo libero)
- `backend/tests/test_pdf_pro.py` - nuovo test che renderizza il template Jinja2 direttamente per verificare "Parquet"/"Gres" senza WeasyPrint
- `frontend/src/api/dettaglio-pro.ts` - `DomandaProOut`/`OpzioneProOut`, `risposte` generico, `postRisposteDettaglioPro` invia `{risposte, livelli}`
- `frontend/src/components/DomandaField.tsx` - tipo `DomandaMinima` (sottoinsieme compatibile wizard/pannello), prop `griglia?: "due-colonne"`
- `frontend/src/components/DettaglioProView.tsx` - pannello riscritto su `DomandaField`, stato inizializzato dall'eco del server, riepilogo via `ETICHETTE_RIEPILOGO`

## Decisions Made

Vedi `key-decisions` in frontmatter. In sintesi: l'eco delle risposte al client resta scoped al pannello (mai le risposte del wizard); `-1`/`true` su una domanda numerica ereditano il comportamento del tipo `Risposte` condiviso col wizard (422 o coercizione), non corretti qui perche' pre-esistenti e fuori dallo scope del piano.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test HTTP esistenti rotti dal nuovo contratto generico**
- **Found during:** Task 1, verifica del comando del piano (`test_dettaglio_pro_livelli.py`/`test_dettaglio_pro_paywall.py` non erano nei `files_modified` del task ma usano il vecchio payload)
- **Issue:** `RisposteDomandeRequest` con `extra="forbid"` rifiuta `{"bagni": 1, ...}` a livello radice — i payload esistenti in `test_dettaglio_pro_livelli.py` (3 POST) e `test_dettaglio_pro_paywall.py` (3 POST) postavano ancora i tre campi cablati in cima al body.
- **Fix:** payload riscritti come `{"risposte": {...}, "livelli": {...}}`.
- **Files modified:** `backend/tests/test_dettaglio_pro_livelli.py`, `backend/tests/test_dettaglio_pro_paywall.py`
- **Verification:** i 6 test coinvolti passano; suite completa `test_dettaglio_pro*`/`test_no_leak`/`test_pdf*` 297 passed, 5 skipped (GTK3), nessuna regressione.
- **Committed in:** `5dbfdf7` (Task 1 commit)

**2. [Rule 1 - Bug] Scan anti-leak a substring libero produceva un falso positivo**
- **Found during:** Task 1, primo test anti-leak esteso
- **Issue:** il criterio "nessuna sottostringa 'effett' nel testo grezzo" del piano faceva scattare il test sulla parola italiana "effettuato" dentro la descrizione legittima di una voce del listino.
- **Fix:** il controllo e' sulle CHIAVI del JSON (ricorsivo), non sul testo intero — coerente con la formulazione letterale del piano ("Il JSON... non contiene CHIAVI con...").
- **Files modified:** `backend/tests/test_no_leak.py`
- **Committed in:** `5dbfdf7` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (entrambe Rule 1)
**Impact on plan:** Nessuno scope creep. Il primo fix era necessario perche' il piano non elencava tutti i file HTTP impattati dal cambio di contratto; il secondo era un affinamento del test stesso (nessun cambiamento al codice di produzione).

## Issues Encountered

- Il worktree non ha `frontend/node_modules` (ambiente atteso, CLAUDE.md): creato un symlink locale (`ln -s`) alla cartella del checkout principale per `npm run build`/`npm run lint`, rimosso non serve — non e' tracciato (gitignored), nessuna azione di pulizia necessaria.

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta.

## Next Phase Readiness

- D-06/D-07 soddisfatti sulla pagina di dettaglio Pro: il pannello parte dai default, ricalcola col contratto generico, il wizard resta invariato (nessun file del wizard toccato).
- API generica validata contro il catalogo, PDF allineato alla schermata by-construction (stesso `_compute_dettaglio`), nessun leak di effetti/coefficienti verificato sulle chiavi del DTO.
- Nessun blocco noto per il prossimo piano della fase.

---
*Phase: 09-configuratore-pro*
*Completed: 2026-09-26*

## Self-Check: PASSED

- `backend/app/services/dettaglio_pro.py` (domande_configuratore/valida_risposte_pro) — FOUND
- `backend/app/schemas/dettaglio_pro.py` (DomandaProOut/OpzioneProOut, extra=forbid) — FOUND
- `backend/app/templates/pdf_stima_pro.html` (dettaglio.domande) — FOUND
- `frontend/src/components/DomandaField.tsx` (prop griglia) — FOUND
- `frontend/src/components/DettaglioProView.tsx` (DomandaField, copy default estesa) — FOUND
- Commit `5dbfdf7` — FOUND in `git log`
- Commit `75835ed` — FOUND in `git log`
- Commit `9b17979` — FOUND in `git log`
- Backend: `test_dettaglio_pro.py test_pdf_pro.py test_no_leak.py test_dettaglio_pro_paywall.py` — 34 passed, 2 skipped
- Backend (sweep esteso dettaglio_pro/domande/effetti/no_leak/pdf/stime_salvate): 297 passed, 5 skipped, 0 failed
- Frontend: `npm run build` e `npm run lint` — exit 0 (solo warning pre-esistenti, stesso pattern in altri file)
