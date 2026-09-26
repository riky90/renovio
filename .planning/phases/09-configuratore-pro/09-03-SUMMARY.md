---
phase: 09-configuratore-pro
plan: 03
subsystem: api
tags: [sqlalchemy, catalogo-domande, motore-pro, effetti, tdd]

# Dependency graph
requires:
  - phase: 09-configuratore-pro
    provides: "09-02: catalogo Pro (domande finitura/tipo_pavimento con effetti includi, stepper bagni/porte/condizionatori con quantita_per_unita), GRUPPO_CONFIGURATORE_PRO"
provides:
  - "risolvi_effetti_pro(), RisoluzionePro, AssePro in app/services/effetti.py: risoluzione degli assi di scelta Pro (includi/escludi/fattore_quantita/quantita_per_unita) dallo stesso catalogo del Free"
  - "risolvi_scelte(..., tiers=...) generalizzato a piu' tier in una sola chiamata"
  - "DettaglioProService.compute() riscritto: legge gli assi dal catalogo, non piu' voce.livello/domanda_mirata_key"
  - "Guard statico (test_motore_pro_non_legge_livello_ne_chiavi_mirate) che impedisce la reintroduzione del vecchio filtro"
affects: [09-04, 09-05, 09-frontend-pannello-affina-la-stima]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Un asse di scelta Pro e' una domanda del catalogo con almeno un effetto includi: 'governare' una voce/sottocategoria significa esserne bersaglio di QUALSIASI opzione attiva della domanda, 'includerla' significa esserlo di quella SCELTA — la stessa distinzione regge sia il filtro (esclusioni vincono, poi asse per asse) sia l'anteprima admin"
    - "Una risoluzione per valore distinto di finitura (cache dict in compute()): il pannello puo' mandare un valore diverso per categoria via `livelli`, ma il catalogo ha una sola domanda `finitura`"

key-files:
  created:
    - backend/tests/test_effetti_pro.py
    - backend/tests/test_dettaglio_pro_alternative.py
    - .planning/phases/09-configuratore-pro/deferred-items.md
  modified:
    - backend/app/services/effetti.py
    - backend/app/services/dettaglio_pro.py
    - backend/tests/test_dettaglio_pro.py
    - backend/tests/test_dettaglio_pro_livelli.py

key-decisions:
  - "L'identificatore di una voce nei test di conteggio deve includere la sottocategoria: il listino ha righe con descrizione identica in sottocategorie diverse (wrinkle nota dal 09-02), quindi (codice, descrizione) da solo non e' una chiave univoca — trovato durante il GREEN di Task 3, non un bug del motore"
  - "TestFiltroPuro (test unitari di _voce_inclusa) rimossa: la funzione non esiste piu', copertura equivalente in test_effetti_pro.py su RisoluzionePro.voce_inclusa"
  - "test_con_voci_non_curate_il_livello_non_cambia_nulla rimosso: la sua premessa (voci non curate finche' l'admin non le tagga) non vale piu' — il seed 09-02 cura GIA' l'asse finitura su tutte le 21 voci di gres fin dal primo boot (D-07)"
  - "'sottocategoria svuotata dal filtro' testata con una sottocategoria di TEST interamente governata: il GRES reale non ha piu' voci non governate (esattamente 21 voci, tutte bersaglio di finitura), quindi nessuna combinazione di livello lo svuota davvero"

requirements-completed: [CFG-01, CFG-02]

# Metrics
duration: ~2h
completed: 2026-09-26
---

# Phase 09 Plan 03: Il motore Pro legge gli assi dal catalogo Summary

**`DettaglioProService.compute()` non somma piu' le alternative: A.6 mostra una sola posa e ogni sottocategoria-catalogo mostra un solo livello, risolti da una nuova `risolvi_effetti_pro()` che condivide `risolvi_scelte()` col motore Free.**

## Performance

- **Duration:** ~2h
- **Tasks:** 3/3
- **Files modified:** 4 modificati, 3 creati

## Accomplishments

- `risolvi_effetti_pro()` (nuovo, in `effetti.py`) risolve i quattro effetti Pro (`includi`/`escludi`/`fattore_quantita`/`quantita_per_unita`) sugli stessi dati che il Free usa per default/derivazioni/visibilita' (`risolvi_scelte(tiers=(free, pro))`), producendo `RisoluzionePro` con `voce_inclusa()`, `fattore()`, `opzione_asse()`.
- `DettaglioProService.compute()` non legge piu' `voce.livello` ne' `domanda_mirata_key`: il filtro per livello di finitura e la scelta di pavimento vengono dal catalogo, con una risoluzione cache-ata per ogni valore distinto di `finitura` in gioco (il pannello puo' differenziare il livello per categoria via `livelli`).
- Un test di conteggio (`test_dettaglio_pro_alternative.py`) verifica, su tutte le 12 combinazioni finitura × tipo_pavimento e sui 3 livelli per categoria, che nessuna sottocategoria-catalogo e nessun asse di A.6 mostri voci di piu' di un'opzione nello stesso computo — il criterio d'uscita della fase (CFG-02).
- Guard statico: il codice sorgente di `dettaglio_pro.py` non contiene piu' le stringhe `voce.livello` (come attributo), `domanda_mirata_key`, `_voce_inclusa` — verificato da un test dedicato che ignora le righe di prosa/docstring.
- Le tre chiavi mirate (bagni/porte/condizionatori, tier Free) restano nel resolver comune: le loro `quantita_per_unita` continuano a funzionare esattamente come prima (oracolo A.0.3 invariato), ma passano ora dal catalogo invece che da `CoefficienteQuantitaVoce.domanda_mirata_key`.

## Task Commits

1. **Task 1: test di conteggio CFG-02 (RED)** - `3ec4581` (test)
2. **Task 2: risolvi_effetti_pro() nel modulo effetti** - `d37f8ee` (feat)
3. **Task 3: swap del motore Pro (GREEN) + guard statico** - `2bb95f6` (feat)

_TDD dei Task 1/2 come "scrivi test insieme al codice" (stesso schema del 09-02), non commit RED/GREEN separati per Task 2 — il piano lo prevedeva solo per Task 1/3, che infatti hanno un commit `test` isolato e uno `feat` che lo fa passare._

## Files Created/Modified

- `backend/app/services/effetti.py` - `risolvi_scelte(..., tiers=...)`, `AssePro`, `RisoluzionePro`, `risolvi_effetti_pro()`, docstring di modulo estesa con l'ordine di risoluzione Pro
- `backend/app/services/dettaglio_pro.py` - `compute()` riscritto su `risolvi_effetti_pro()`; `_voce_inclusa()` e il ramo `domanda_mirata_key` di `_quantita()` rimossi
- `backend/tests/test_effetti_pro.py` - nuovo: resolver Pro testato caso per caso (includi su voce/sottocategoria, escludi, fattore, quantita_per_unita, tipo_code, opzioni/effetti non attivi, righe malformate, visibilita')
- `backend/tests/test_dettaglio_pro_alternative.py` - nuovo: test di conteggio CFG-02
- `backend/tests/test_dettaglio_pro.py` - rimpiazzato il test del `default_conteggio` cablato con uno che legge l'atteso da `attesa_immobile`; aggiunto il guard statico
- `backend/tests/test_dettaglio_pro_livelli.py` - `TestFiltroPuro` rimossa; i test di selezione per livello leggono i bersagli reali dal catalogo (niente piu' tag manuali su `voce.livello`)
- `.planning/phases/09-configuratore-pro/deferred-items.md` - nuovo: fallimento pre-esistente e fuori scope di `test_health.py`

## Decisions Made

Vedi `key-decisions` in frontmatter. In sintesi: l'identificatore di voce nei test di conteggio deve portare la sottocategoria (collisione di descrizione nota dal 09-02), e due test di `test_dettaglio_pro_livelli.py` la cui premessa non regge piu' con un catalogo gia' curato dal seed sono stati riscritti/sostituiti invece di forzati a passare.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Identificatore di voce non univoco nei test di conteggio**
- **Found during:** Task 3 (verifica di `test_dettaglio_pro_alternative.py` dopo lo swap)
- **Issue:** `_bersagli_per_opzione`/`_identificatori_presenti` usavano `(codice, descrizione)` come chiave; una voce bersaglio di "alto" in GRES aveva la STESSA descrizione di una voce, non governata, nella sottocategoria PAVIMENTI — falso positivo "due opzioni presenti".
- **Fix:** la chiave ora include l'id della sottocategoria (`(sottocategoria_id, codice, descrizione)`).
- **Files modified:** `backend/tests/test_dettaglio_pro_alternative.py`
- **Verification:** le 19 combinazioni parametrizzate passano.
- **Committed in:** `2bb95f6` (Task 3 commit)

**2. [Rule 1 - Bug] Test con premessa invalidata dal catalogo gia' curato**
- **Found during:** Task 3
- **Issue:** `test_con_voci_non_curate_il_livello_non_cambia_nulla` assumeva un catalogo mai curato (tutte le voci a `livello=NULL`); dal 09-02 il seed cura GIA' l'asse `finitura` su tutte le 21 voci di gres al primo boot, quindi scegliere un livello diverso cambia davvero il totale — comportamento corretto (D-07), non un bug.
- **Fix:** test rimosso.
- **Files modified:** `backend/tests/test_dettaglio_pro_livelli.py`
- **Committed in:** `2bb95f6` (Task 3 commit)

**3. [Rule 1 - Bug] "sottocategoria svuotata" non piu' riproducibile sul GRES reale**
- **Found during:** Task 3
- **Issue:** il test taggava a mano `voce.livello="alto"` su TUTTE le voci di gres per svuotarlo scegliendo "base". Con l'asse reale, GRES ha esattamente 21 voci, tutte GOVERNATE da finitura (7 per livello): nessuna combinazione di livello la svuota mai per intero, perche' l'opzione scelta include comunque le sue 7.
- **Fix:** riscritto con una sottocategoria di TEST creata ad hoc, interamente governata da due sole opzioni (`base`/`alto`) su un totale di 2 voci: sotto "medio" nessuna delle due e' bersaglio, quindi si svuota davvero.
- **Files modified:** `backend/tests/test_dettaglio_pro_livelli.py`
- **Committed in:** `2bb95f6` (Task 3 commit)

**4. [Rule 1 - Bug] `test_le_voci_senza_livello_restano` non aveva piu' fixture (nessuna voce di gres e' "senza livello" nel catalogo reale)**
- **Found during:** Task 3
- **Issue:** stesso motivo del punto 3 — GRES non ha piu' voci non governate da finitura.
- **Fix:** riscritto usando l'asse `tipo_pavimento` su A.6, che ha davvero pose non governate (A.6.7 in poi).
- **Files modified:** `backend/tests/test_dettaglio_pro_livelli.py`
- **Committed in:** `2bb95f6` (Task 3 commit)

---

**Total deviations:** 4 auto-fixed (Rule 1)
**Impact on plan:** Nessuno scope creep. Tutti i fix sono correzioni a test la cui premessa non regge piu' (dati gia' curati dal 09-02) o a un bug di identificazione nel test di conteggio stesso — il motore di produzione non e' stato toccato da nessuna di queste correzioni.

## Issues Encountered

- Suite completa (`pytest -q`, non richiesta dal piano) lanciata per prudenza dopo lo swap: 1 fallimento pre-esistente e fuori scope, `test_health.py::test_health_db_returns_live_count` (colpisce `dev.db`, assente in questo worktree). Documentato in `deferred-items.md`, non toccato.

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta.

## Next Phase Readiness

- Il bug della fase (somma delle alternative Pro) e' chiuso: CFG-01 e CFG-02 verificati da test.
- `voce.livello` e `coefficiente_qta_voce.domanda_mirata_key` restano a DB (nessuna migrazione distruttiva, D-41) ma nessun modulo di produzione li legge piu'.
- L'API di `DettaglioProService.compute()` e i router non sono cambiati (`git diff backend/app/routers/` vuoto): il piano 09-04/09-05 (pannello "Affina la stima") puo' procedere senza toccare il contratto.
- `RisoluzionePro`/`AssePro` sono pronti per essere riusati da un'eventuale anteprima admin sugli assi Pro (stessa disciplina di `EffettoApplicato` gia' usata dal Free).

---
*Phase: 09-configuratore-pro*
*Completed: 2026-09-26*
