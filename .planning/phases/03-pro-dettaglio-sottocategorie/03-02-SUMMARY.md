---
phase: 03-pro-dettaglio-sottocategorie
plan: 02
subsystem: database
tags: [sqlalchemy, alembic, openpyxl, seed, sqlite, postgres]

requires:
  - phase: 03-pro-dettaglio-sottocategorie
    provides: "Subscription/tessera Pro, require_pro (03-01)"
provides:
  - "Tabelle Sottocategoria/Voce/CoefficienteQuantitaVoce collegate a Listino (predisposte multi-citta)"
  - "Migrazione 0005 (catena 0001..0005 lineare, upgrade/downgrade/upgrade verificato)"
  - "StimaSalvata.risposte_pro_json nullable per le domande mirate"
  - "docs/seed-dettaglio-pro.json: 21 sottocategorie / 191 voci / 573 coefficienti quantita-per-mq per le 4 categorie"
  - "seed() esteso con seed_dettaglio_pro(), idempotente, stessa funzione (D-12)"
  - "backend/scripts/extract_dettaglio_pro.py per rigenerare il JSON dal xlsx"
affects: ["03-03 (motore DettaglioProService)", "03-04 (endpoint dettaglio-pro + PDF Pro)"]

tech-stack:
  added: [openpyxl (dev-only)]
  patterns:
    - "Upsert idempotente per chiave naturale esteso a 3 nuove entita (stesso idioma .filter_by().one_or_none() di seed.py)"
    - "Estrazione one-off Excel confinata a backend/scripts/, mai importata sotto backend/app/"

key-files:
  created:
    - backend/app/models/dettaglio_pro.py
    - backend/alembic/versions/0005_dettaglio_pro.py
    - backend/scripts/extract_dettaglio_pro.py
    - docs/seed-dettaglio-pro.json
    - backend/tests/test_seed_dettaglio.py
  modified:
    - backend/app/models/stima_salvata.py
    - backend/app/models/__init__.py
    - backend/scripts/seed.py
    - backend/pyproject.toml

key-decisions:
  - "openpyxl approvato come dev dependency dopo checkpoint blocking-human (utente: 'approvato')"
  - "Blocco iniziale 'Allestimento cantiere' del foglio A-EDILE (codici A.1..A.8 riusati piu' avanti come vere sottocategorie) isolato in una Sottocategoria sintetica A.0 con codici voce sintetici A.0.n, per evitare collisioni di codice non documentate nel RESEARCH"
  - "Famiglie catalogo B/C/D aggregate a livello di gruppo-intestazione (assunzione A2 del RESEARCH): ogni riga-prodotto diventa una Voce sotto il gruppo, nessuna enumerazione SKU aggiuntiva"
  - "Coefficienti quantita-per-m2/domanda-mirata/default-conteggio bozza secondo le regole UM di D-05 (mq/ml proporzionali ai mq con fattore per tipo 0.4/0.7/1.0; cad su bagni/porte/condizionatori -> domanda_mirata_key; cad generico e ac/percentuale/altre UM -> default_conteggio fisso), esplicitamente tarabili da admin in Fase 4"

requirements-completed: [PRO-01]

duration: 27min
completed: 2026-08-27
---

# Phase 3 Plan 02: Dettaglio Pro — schema e seed RE Summary

**Tabelle Sottocategoria/Voce/CoefficienteQuantitaVoce collegate a Listino + seed idempotente esteso che popola tutte e 4 le categorie (A-EDILE gerarchica, B/C/D cataloghi) dai prezzi reali del computo Reggio Emilia, senza mai persistere margine/prezzo impresa.**

## Performance

- **Duration:** 27 min
- **Started:** 2026-08-27T06:16:00Z
- **Completed:** 2026-08-27T06:43:00Z
- **Tasks:** 3 (1 checkpoint blocking-human + 2 auto)
- **Files modified:** 10

## Accomplishments
- Schema `Sottocategoria`/`Voce`/`CoefficienteQuantitaVoce` che fa convivere le due forme strutturali del computo (A-EDILE gerarchica a codici vs B/C/D cataloghi piatti) senza colonne condizionali per categoria
- Migrazione Alembic 0005 (catena 0001→0005 lineare) verificata upgrade→downgrade→upgrade
- Script di estrazione one-off dal `.xlsx` reale (non dal solo markdown riassuntivo) che gestisce correttamente il blocco "Allestimento cantiere" con codici riusati — problema non documentato nel RESEARCH, scoperto e risolto in questa sessione
- Seed idempotente esteso nella stessa funzione `seed()`: 21 sottocategorie, 191 voci, 573 righe di coefficiente, verificato invariato su doppia esecuzione
- Nessun dato di margine/prezzo impresa persistito su `Voce` (grep meccanico a zero su modello e JSON)

## Task Commits

1. **Task 1: Gate legittimità pacchetto openpyxl** - checkpoint `blocking-human`, approvato dall'utente ("approvato"), nessun commit di codice
2. **Task 2: Modelli dettaglio + migrazione 0005** - `051f41d` (feat)
3. **Task 3: Script estrazione + seed-dettaglio-pro.json + seed() esteso** - `d4e0f27` (feat)

**Plan metadata:** (questo commit)

## Files Created/Modified
- `backend/app/models/dettaglio_pro.py` - `Sottocategoria`, `Voce`, `CoefficienteQuantitaVoce`; codice nullable, famiglia discriminatore, nessuna colonna impresa
- `backend/alembic/versions/0005_dettaglio_pro.py` - crea le 3 tabelle + `stima.risposte_pro_json`, down_revision 0004
- `backend/app/models/stima_salvata.py` - colonna `risposte_pro_json` (JSON nullable) per le risposte alle domande mirate
- `backend/app/models/__init__.py` - registra i nuovi modelli su `Base.metadata`
- `backend/scripts/extract_dettaglio_pro.py` - estrae A-EDILE (gerarchia) + B/C/D (cataloghi) dal `.xlsx`, confinato a `scripts/`
- `docs/seed-dettaglio-pro.json` - dataset RE: 21 sottocategorie, voci con UM/prezzo/coefficienti quantita-per-mq per i 3 tipi
- `backend/scripts/seed.py` - `seed_dettaglio_pro()` + upsert helper, chiamato da `seed()` prima del commit finale
- `backend/tests/test_seed_dettaglio.py` - 4 test: copertura 4 categorie, idempotenza, coefficiente per ogni tipo su ogni voce, nessuna colonna impresa
- `backend/pyproject.toml` / `backend/uv.lock` - `openpyxl` come dev dependency

## Decisions Made
- Vedi `key-decisions` in frontmatter. La più rilevante: il foglio `A-EDILE` riusa i codici `A.1..A.8` due volte (prima come voci dirette del blocco "Allestimento cantiere", poi come vere sottocategorie `A.1 Demolizioni`...`A.12 Sicurezza`) — non descritto nel RESEARCH/CONTEXT. Risolto isolando il primo blocco in una sottocategoria sintetica `A.0` con codici voce sintetici, per non generare collisioni di chiave naturale nel seed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Bug di parsing nel primo tentativo di estrazione A-EDILE**
- **Found during:** Task 3, prima esecuzione dello script di estrazione
- **Issue:** Il primo algoritmo di stato usava un flag booleano semplice (`allestimento_seen`) per distinguere il blocco "Allestimento cantiere" dalla vera gerarchia, ma i codici `A.3`/`A.6`/`A.7` come righe-intestazione (senza UM/prezzo diretti, con varianti lettera a seguire) venivano scambiati per vere sottocategorie premature, e le loro varianti lettera (piatto doccia/vasca/WC/bidet/ecc.) venivano silenziosamente perse (0 voci prodotte per quei gruppi)
- **Fix:** Riscritta la state machine usando la riga "TOTALE ALLESTIMENTO DI CANTIERE" come confine esplicito tra le due fasi, con tracking distinto delle voci pendenti (header con varianti) per fase
- **Files modified:** backend/scripts/extract_dettaglio_pro.py
- **Verification:** Ri-eseguita l'estrazione: `A.0 Allestimento di cantiere` passa da 1 a 18 voci (le varianti recuperate), nessuna sottocategoria spuria A.3/A.6/A.7 duplicata prima della vera gerarchia
- **Committed in:** d4e0f27 (Task 3 commit — il bug non è mai stato committato separatamente, corretto prima del commit)

---

**Total deviations:** 1 auto-fixed (1 bug di parsing)
**Impact on plan:** Necessario per la correttezza dei dati estratti (le voci a conteggio ad alto impatto — piatto doccia/vasca/WC/bidet/radiatori/condizionatore — sono proprio quelle su cui il motore Pro applicherà le domande mirate D-04). Nessuno scope creep: risolto interamente dentro il Task 3 pianificato.

## Issues Encountered
- Il foglio Excel reale diverge dalla mappa riassuntiva `docs/computo-struttura-dettaglio.md` nel dettaglio dei codici (il blocco "Allestimento cantiere" riusa i codici A.1-A.8): non un errore del documento (che segnala genericamente il blocco), ma un dettaglio implementativo scoperto solo leggendo l'xlsx via `openpyxl` in questa sessione. Risolto come da Deviazione 1.
- Il conteggio finale delle `Voce` in DB (191) è leggermente inferiore al totale grezzo emesso dallo script (196): la chiave naturale per i cataloghi piatti B/C/D usa `descrizione` quando `codice` è `None`, quindi alcune righe-prodotto con testo descrittivo pressoché identico (varianti di prezzo dello stesso gres, nel foglio B-FINITURE) collassano sullo stesso upsert. Comportamento accettato: coerente con l'assunzione A2 del RESEARCH ("voci quasi-identiche possono essere accorpate"), non blocca PRO-01, e la lista completa per-prodotto resta comunque disponibile per un affinamento futuro via upload admin (Fase 4).

## Known Stubs

Nessuno stub bloccante: i dati sono reali (prezzi RE dal `.xlsx`), ma i **coefficienti quantita-per-m2/domanda-mirata sono bozza** per esplicita concessione del CONTEXT/RESEARCH ("valori bozza, tarabili da admin in Fase 4") — non un placeholder di sviluppo, ma il design consapevole di D-04/D-05. Nessuna azione richiesta prima di 03-03.

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta. `openpyxl` è una dev dependency locale, non serve a runtime.

## Next Phase Readiness

- Schema e dati pronti per `DettaglioProService.compute()` (03-03): ogni `Voce` ha prezzo cliente + UM + un `CoefficienteQuantitaVoce` per ciascuno dei 3 tipi (leggera/moderata/totale), con `domanda_mirata_key`/`default_conteggio` popolati per bagni/porte/condizionatori.
- `StimaSalvata.risposte_pro_json` pronta per persistere le risposte alle domande mirate (consumata da 03-03/03-04 per evitare la deriva PDF/schermata, Pitfall 2/3 del RESEARCH).
- Nessun blocco noto. Da tenere presente in 03-03: la deduplicazione per-descrizione nei cataloghi B/C/D (Issues Encountered) implica che il motore Pro vedrà una lista leggermente più corta di prodotti-varianti-prezzo identiche rispetto al file originale — non un problema per il calcolo bottom-up, ma da segnalare se un futuro QA conta le righe contro l'Excel.

---
*Phase: 03-pro-dettaglio-sottocategorie*
*Completed: 2026-08-27*

## Self-Check: PASSED

Tutti i file creati verificati presenti su disco; entrambi i commit di task (`051f41d`, `d4e0f27`) verificati presenti in `git log`.
