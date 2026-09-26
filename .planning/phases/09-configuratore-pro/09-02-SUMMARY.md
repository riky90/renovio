---
phase: 09-configuratore-pro
plan: 02
subsystem: database
tags: [sqlalchemy, seed, catalogo-domande, effetti]

# Dependency graph
requires:
  - phase: 08.1-catalogo-domande-pagina-crud-e-file-excel
    provides: "domanda/opzione_domanda/effetto_opzione, valida_effetto, TIPI_EFFETTO_PRO, D-41 create-if-missing"
provides:
  - "Bersagli a chiave naturale nel seed (_risolvi_bersaglio_naturale), usati per creare effetti che puntano a voci/sottocategorie senza id cablati"
  - "Domanda finitura (base/medio/alto) con 21 effetti includi sulle voci gres oggi livellate in dev.db"
  - "Domanda tipo_pavimento (gres/parquet/maxi_lastra/mosaico) con effetti includi su A.6.1/.2/.5/.6"
  - "Effetti quantita_per_unita sull'opzione valore di bagni/porte/condizionatori per ogni voce con quella domanda_mirata_key"
  - "GRUPPO_CONFIGURATORE_PRO: le domande del configuratore Pro sono escluse da GET /api/v1/domande (wizard invariato)"
affects: [09-03-motore-pro-legge-effetti, 09-frontend-pannello-affina-la-stima]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bersaglio a chiave naturale nel JSON di seed (target_voce/target_sottocategoria), risolto a id concreti del listino di default al momento del seed, non cablato"
    - "Costanti di convenzione (DOMANDA_FINITURA, GRUPPO_CONFIGURATORE_PRO) accanto a OPZIONE_VALORE in effetti.py"

key-files:
  created:
    - backend/tests/test_seed_domande_pro.py
  modified:
    - backend/app/services/effetti.py
    - backend/scripts/seed.py
    - backend/seed_data/seed-domande.json
    - backend/app/routers/domande.py
    - backend/tests/test_domande_api.py
    - backend/tests/test_domande_free.py

key-decisions:
  - "_risolvi_bersaglio_naturale risolve fuori da _crea_effetto_se_manca, nel ciclo di seed_domande: la firma di _crea_effetto_se_manca resta invariata per i chiamanti esistenti"
  - "seed_domande ora ritorna il numero di bersagli naturali non risolti (int); seed() ignora il valore, i test lo usano per il criterio 0-non-risolti sul JSON reale"
  - "test_domande_free.py::test_nessuna_opzione_di_default_porta_effetti filtrato ai soli effetti Free (Rule 1): un includi Pro sul default (finitura=medio, tipo_pavimento=gres) e' il meccanismo di D-07, non una correzione di prezzo silenziosa come i quattro tipi Free"

patterns-established:
  - "Un effetto del JSON di seed puo' puntare a una voce/sottocategoria per chiave naturale (categoria_code, sottocategoria codice-o-nome, voce codice-o-descrizione) invece che per id — utile ogni volta che il target vive nello stesso listino di default seminato nella stessa run"

requirements-completed: [QST-05, CFG-03]

# Metrics
duration: ~55min
completed: 2026-09-26
---

# Phase 09 Plan 02: Catalogo Pro (finitura + tipo_pavimento + stepper mirati) Summary

**Seed a bersaglio naturale: la domanda `finitura` (dalla migrazione di `voce.livello`), la domanda `tipo_pavimento` (pose A.6) e gli effetti `quantita_per_unita` su bagni/porte/condizionatori sono ora dati del catalogo, esclusi dal wizard.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 2/2
- **Files modified:** 6 (+ 1 creato)

## Accomplishments

- Il seed sa risolvere bersagli di effetto a chiave naturale (`target_voce`/`target_sottocategoria`) sul listino di default, saltando in silenzio un bersaglio rotto invece di far fallire il boot del container.
- Un DB nuovo seminato da zero ha la domanda `finitura` (base/medio/alto, medio default) con 21 effetti `includi` (7 per opzione) sulle voci gres oggi livellate a mano in `dev.db`, e la domanda `tipo_pavimento` (gres default/parquet/maxi_lastra/mosaico) con 4 effetti `includi` su A.6.1/A.6.2/A.6.5/A.6.6.
- Le domande stepper esistenti `bagni`/`porte`/`condizionatori` hanno ora effetti `quantita_per_unita` (valore 1) su ogni voce di `seed-dettaglio-pro.json` con quella `domanda_mirata_key` (26/11/11 voci uniche rispettivamente).
- `GET /api/v1/domande` esclude sempre le domande del gruppo `configuratore_pro` (nuovo filtro in `_domande_attive`): il wizard, anche a tier `pro`, non riceve `finitura` né `tipo_pavimento`.
- `voce.livello` e `coefficiente_qta_voce.domanda_mirata_key` non sono stati toccati (nessun DROP, nessuna migrazione dati): restano leggibili finche' il motore Pro (09-03) non smette di consultarli.

## Task Commits

1. **Task 1: bersagli a chiave naturale nel seed + costanti del configuratore** - `bfdc3c9` (feat)
2. **Task 2: catalogo Pro nel JSON + esclusione dal wizard** - `2089460` (feat)

_Nessun task TDD separato in RED/GREEN: entrambi i task hanno prodotto test e implementazione nello stesso commit, come previsto dal piano (`tdd="true"` inteso come "scrivi test insieme al codice", non come commit separati)._

## Files Created/Modified

- `backend/app/services/effetti.py` - `DOMANDA_FINITURA`, `GRUPPO_CONFIGURATORE_PRO` (costanti di convenzione)
- `backend/scripts/seed.py` - `_risolvi_bersaglio_naturale`, `seed_domande` esteso (listino di default, conteggio non risolti, return int)
- `backend/seed_data/seed-domande.json` - domande `finitura` e `tipo_pavimento`, effetti `quantita_per_unita` su bagni/porte/condizionatori, nota estesa
- `backend/app/routers/domande.py` - `_domande_attive` esclude `GRUPPO_CONFIGURATORE_PRO`
- `backend/tests/test_seed_domande_pro.py` - nuovo: risoluzione bersagli naturali (Task 1) + catalogo Pro sul JSON reale (Task 2)
- `backend/tests/test_domande_api.py` - test esclusione dal wizard
- `backend/tests/test_domande_free.py` - `test_nessuna_opzione_di_default_porta_effetti` filtrato ai soli effetti Free

## Decisions Made

- La risoluzione del bersaglio naturale avviene nel ciclo di `seed_domande`, non dentro `_crea_effetto_se_manca` — la firma di quest'ultima resta identica per non toccare i chiamanti esistenti.
- `seed_domande` ora espone il conteggio dei bersagli non risolti come valore di ritorno (prima `None`); `seed()` lo ignora, i test lo usano come oracolo (0 sul JSON reale).
- La collisione di descrizione fra due voci distinte di `seed-dettaglio-pro.json` (es. "Cassetta d'incasso da 9 litri..." in RUBINETTERIE, "Porta interna in legno..." in PORTE) è una wrinkle pre-esistente dell'upsert per chiave naturale di `_upsert_voce` (già presente prima di questo piano): le due righe JSON collassano in una sola riga DB. Non introduce un bug nuovo — gli effetti a bersaglio naturale di questo piano puntano comunque, correttamente, alla singola riga sopravvissuta — ma resta un difetto di dati pre-esistente fuori scope, annotato qui per visibilita' futura.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_nessuna_opzione_di_default_porta_effetti` falliva sui nuovi default Pro**
- **Found during:** Task 2 (verifica della suite dopo l'aggiunta del catalogo Pro)
- **Issue:** Il test (in `test_domande_free.py`, scritto per il layer Free) asserisce che nessuna opzione di default abbia effetti, per proteggere la neutralita' del layer a riposo. I nuovi default Pro (`finitura=medio`, `tipo_pavimento=gres`) hanno effetti `includi` per costruzione (D-07: il default e' cio' che rende il primo computo "senza alternative sommate"), quindi il test falliva su un comportamento voluto, non un bug.
- **Fix:** Filtrato il test ai soli `tipo_effetto` in `TIPI_EFFETTO_FREE`, con docstring che spiega la distinzione: un `includi` Pro sul default e' il meccanismo stesso della neutralita' Pro, non una correzione di prezzo silenziosa come `moltiplicatore_categoria`/`eur_per_scostamento`.
- **Files modified:** `backend/tests/test_domande_free.py`
- **Verification:** Suite completa richiesta dal piano (170 test su seed/domande/estimation/export/import) verde.
- **Committed in:** `2089460` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** Nessuno scope creep — il fix corregge un test che assumeva (correttamente per il Free) che ogni default fosse neutro, senza prevedere il caso Pro introdotto proprio da questo piano.

## Issues Encountered

None oltre alla deviazione sopra.

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta.

## Next Phase Readiness

- Il catalogo Pro (`finitura`, `tipo_pavimento`, stepper mirati) e' dato in tabella, curabile da `/admin/domande` come ogni altra domanda (08.1).
- Il piano 09-03 (motore Pro) puo' ora leggere questi effetti via `risolvi_scelte(tier="pro")` + `EffettoOpzione` invece di `voce.livello`/`domanda_mirata_key` — nessuna colonna e' stata rimossa, la migrazione resta senza perdita di dati.
- Nessun blocco noto. Resta aperta la nota su "Decisions Made" (collisione descrizione voci) come possibile pulizia futura, non bloccante per 09-03.

---
*Phase: 09-configuratore-pro*
*Completed: 2026-09-26*

## Self-Check: PASSED

All created/modified files verified present (`backend/app/services/effetti.py`,
`backend/scripts/seed.py`, `backend/seed_data/seed-domande.json`,
`backend/app/routers/domande.py`, `backend/tests/test_seed_domande_pro.py`).
Both task commits (`bfdc3c9`, `2089460`) verified present in `git log`.
