---
phase: 09-configuratore-pro
plan: 04
subsystem: database
tags: [alembic, migrazione-dati, sqlite, catalogo-domande]

# Dependency graph
requires:
  - phase: 09-configuratore-pro plan 02
    provides: "domanda finitura (base/medio/alto), domande stepper bagni/porte/condizionatori con opzione valore, chiave naturale opzione/tipo_effetto/target/tipo_code per il seed"
provides:
  - "Migrazione 0021: voce.livello -> effetti includi sull'asse finitura; coefficiente_qta_voce.domanda_mirata_key -> effetti quantita_per_unita sulle domande stepper esistenti"
  - "Percorso senza perdita per dev.db/produzione: un DB esistente non passa piu' da seed create-if-missing per questa curatela, ma dalla migrazione dati 0021"
  - "Prova a secco sui dati reali di dev.db (copia), coerente col seed idempotente"
affects: [09-05-refactor-motore-pro-legge-effetti]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Migrazione dati pura (nessun ADD/DROP COLUMN) con sa.table()/sa.column() locali e op.get_bind(), mai i modelli ORM"
    - "Stessa chiave naturale del seed (opzione_id, tipo_effetto, target_categoria_code, target_sottocategoria_id, target_voce_id, tipo_code) per garantire idempotenza fra migrazione e seed"

key-files:
  created:
    - backend/alembic/versions/0021_assi_pro_da_livello_e_chiavi_mirate.py
  modified:
    - backend/tests/test_migrazioni_sqlite.py

key-decisions:
  - "Nessun DROP COLUMN: voce.livello, coefficiente_qta_voce.domanda_mirata_key e stima.livelli_pro_json restano dato storico non letto dal motore (Open Question 1 del RESEARCH, gia' risolta)"
  - "Downgrade ricalcola gli stessi gruppi (voce, chiave)/(voce, livello) dell'upgrade per restare simmetrico, invece di cancellare per data o per un marcatore 'creato da questa migrazione' che non esiste a schema"
  - "quantita_per_unita con tipo_code NULL solo quando la chiave copre TUTTI i tipi presenti in tipo_ristrutturazione per quella voce; altrimenti un effetto per tipo presente (stesso principio del seed 09-02: tipo_code nullo e' il caso normale, si riempie solo quando serve davvero)"

requirements-completed: [CFG-03, QST-05]

# Metrics
duration: ~50min
completed: 2026-09-26
---

# Phase 09 Plan 04: Migrazione 0021 (asse finitura + stepper mirati da curatela esistente) Summary

**Una migrazione Alembic di soli dati (0021) trasforma la curatela esistente di `voce.livello` e `coefficiente_qta_voce.domanda_mirata_key` negli stessi effetti che il seed del 09-02 crea su un DB nuovo, senza perdere nessuna riga e senza toccare lo schema.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 2/2
- **Files modified:** 2 (1 creato)

## Accomplishments

- La migrazione `0021` legge `voce.livello` (base/medio/alto) e crea (se manca) la domanda `finitura`, le sue 3 opzioni (medio default, stessi valori dell'interfaccia del 09-02) e un effetto `includi` per ogni voce livellata, con la stessa chiave naturale del seed — un seed successivo riconosce le righe e non le duplica.
- Legge `coefficiente_qta_voce.domanda_mirata_key` raggruppato per (voce, chiave): se la chiave ha una domanda con opzione `valore`, crea un effetto `quantita_per_unita` (valore 1); `tipo_code` resta `NULL` solo quando la chiave copre tutti e 3 i tipi di ristrutturazione per quella voce, altrimenti un effetto per tipo presente.
- Valori sconosciuti (`livello` fuori da base/medio/alto, chiave senza domanda corrispondente) vengono saltati senza errore — coerente con la disciplina D-24 gia' in uso nel seed (mai un boot fallito per un dato di curatela).
- Nessun `ADD COLUMN`/`DROP COLUMN`/`UPDATE` su `voce` o `coefficiente_qta_voce`: la migrazione e' scritta con `sa.table()`/`sa.column()` locali e `op.get_bind()`, mai i modelli ORM, per non dipendere da come cambieranno i modelli nel refactor del motore (09-05).
- Downgrade reversibile: rimuove gli effetti `quantita_per_unita` sulle chiavi mirate (ricalcolando gli stessi gruppi dell'upgrade) e poi effetti/opzioni/domanda `finitura`, in quest'ordine esplicito (SQLite non applica i CASCADE senza `PRAGMA`).
- Prova a secco sulla copia di `dev.db` (mai il file reale): conteggi esatti come da inventario del RESEARCH — 7/7/7 voci livellate, 21 effetti `includi` totali dopo la migrazione, 144 righe con chiave mirata invariate, 26/11/11 effetti `quantita_per_unita` (bagni/condizionatori/porte, uno per voce distinta) — e un secondo `scripts/seed.py` sulla stessa copia non ha cambiato nessuno di questi numeri (idempotenza D-41 verificata sui dati reali, non solo su fixture di test).

## Task Commits

1. **Task 1: migrazione 0021 + test** - `7540f14` (feat) — migrazione + 5 nuovi test in `test_migrazioni_sqlite.py` (creazione/non-duplicazione/valori-sconosciuti/invarianza-dati/reversibilita'), piu' l'aggiornamento dell'assert di testa da `0020` a `0021` nel test esistente sul DB vergine.
2. **Task 2: prova a secco su copia di dev.db** - nessun commit di codice: la migrazione ha superato la prova senza richiedere correzioni (vedi "Prove sui dati reali" sotto). Nessun file da committare oltre a quanto gia' nel Task 1.

## Prove sui dati reali (Task 2)

Eseguito su una copia di `dev.db` in scratchpad di sessione (`dev-copy-09-04.db`), mai sul file reale.

| Conteggio | Prima della migrazione | Dopo `upgrade head` | Dopo `scripts/seed.py` |
|---|---|---|---|
| `voce.livello` per valore | base 7 / medio 7 / alto 7 / NULL 170 | identico (invariato) | identico (invariato) |
| `coefficiente_qta_voce.domanda_mirata_key` per chiave | bagni 78 / porte 33 / condizionatori 33 / NULL 429 | identico (invariato) | identico (invariato) |
| Effetti `includi` sulla domanda `finitura` (per opzione base/medio/alto) | domanda inesistente | 7 / 7 / 7 = **21 totali** | **21** (non raddoppiati) |
| Effetti `quantita_per_unita` per domanda mirata | 0 | bagni 26 / condizionatori 11 / porte 11 (= voci distinte per chiave) | identici (non raddoppiati) |
| `alembic_version` sulla copia | `0020` | `0021` | `0021` |
| `alembic_version` sul **vero** `backend/dev.db` | `0020` | **`0020` (mai toccato)** | **`0020` (mai toccato)** |

Verificato al termine che il file reale `backend/dev.db` riporta ancora `version_num = '0020'` e zero effetti `includi` sulla domanda `finitura` — nessuna scrittura e' avvenuta sul file vivo in nessun momento di questo piano.

## Files Created/Modified

- `backend/alembic/versions/0021_assi_pro_da_livello_e_chiavi_mirate.py` — nuova migrazione dati, `revision='0021'`, `down_revision='0020'`
- `backend/tests/test_migrazioni_sqlite.py` — assert di testa aggiornato a `0021`; 5 nuovi test per la 0021

## Decisions Made

- Downgrade simmetrico all'upgrade (ricalcola gli stessi gruppi voce/chiave e voce/livello) invece di affidarsi a un marcatore "creato da questa migrazione", che non esiste a schema per una migrazione dati senza colonne proprie.
- `tipo_code` dell'effetto `quantita_per_unita` resta `NULL` solo se la chiave mirata copre tutti i tipi di ristrutturazione presenti per quella voce — altrimenti un effetto per tipo, stesso principio di parsimonia gia' adottato nel seed 09-02 per `tipo_code`.
- Nessun DROP di `voce.livello`/`domanda_mirata_key`/`livelli_pro_json` in questa fase (scelta gia' fissata dal RESEARCH, Open Question 1 RESOLVED): restano dato storico, il motore Pro (09-05) smettera' di leggerli via guard dedicata, non via rimozione di colonna.

## Deviations from Plan

Nessuna. Il piano e' stato eseguito esattamente come scritto: la migrazione ha superato la prova a secco su dati reali al primo tentativo, senza necessita' di correzioni (il ciclo "se un conteggio non torna, correggere e ripetere" previsto dal Task 2 non e' stato necessario).

## Issues Encountered

Nessuno.

## User Setup Required

None — nessuna configurazione di servizio esterno richiesta. Nessuna azione richiesta su `dev.db`: la sua migrazione vera avverra' nel piano 09-08, come da nota ambientale del CLAUDE.md di questa fase.

## Next Phase Readiness

- La curatela esistente (21 voci livellate + 144 righe a chiave mirata) e' ora rappresentabile con la stessa migrazione dati su qualunque ambiente esistente (dev.db locale quando verra' migrato in 09-08, produzione al primo deploy della milestone).
- Il piano 09-05 (refactor del motore Pro per leggere `effetti.py`/`risolvi_scelte()`) puo' procedere sapendo che, dopo la migrazione, i dati di curatela sono raggiungibili sia via `voce.livello`/`domanda_mirata_key` (storico) sia via `EffettoOpzione` (nuovo canale) — il guard che impedisce al motore di leggere il canale storico e' responsabilita' del 09-05, non di questo piano.
- Nessun blocco noto.

---
*Phase: 09-configuratore-pro*
*Completed: 2026-09-26*

## Self-Check: PASSED

- `backend/alembic/versions/0021_assi_pro_da_livello_e_chiavi_mirate.py` — FOUND
- `backend/tests/test_migrazioni_sqlite.py` — FOUND (modificato)
- Commit `7540f14` — FOUND in `git log`
- 16/16 test in `test_migrazioni_sqlite.py` verdi (11 preesistenti + 5 nuovi)
- 253 test dell'intersezione `migrazioni or seed or domande or effetti or dettaglio_pro` verdi (nessuna regressione)
- Prova a secco su copia di `dev.db`: conteggi 7/7/7, 21/21, 26-11-11 confermati; `dev.db` reale invariato a `0020`
