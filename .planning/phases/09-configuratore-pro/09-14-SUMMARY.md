---
phase: 09-configuratore-pro
plan: 14
subsystem: database
tags: [alembic, sqlalchemy, migrazioni, taratura, configuratore-pro, gap-closure]

# Dependency graph
requires:
  - phase: 09-configuratore-pro
    provides: "regole di curatela G1/G2 nel generatore/applicatore (09-09), dati e prova a mondo aperto sul catalogo reale (09-10), review WR-02 (09-REVIEW.md)"
provides:
  - "migrazione 0023: porta G1/G2 (3 opzioni tipo_pavimento + 175 effetti) su ogni DB esistente gia' a 0022, create-if-missing, fail-loud, reversibile"
  - "downgrade 0021 corretto (WR-02): rimuove solo gli effetti includi che la propria sezione (A) ha creato, mai domanda/opzione_domanda di finitura"
  - "dev.db a 0023 (head), computo reale verificato senza alternative sommate su tutte le 7 opzioni di tipo_pavimento"
  - "09-HUMAN-UAT.md con la sezione di ri-collaudo G1..G4 per Riccardo"
affects: [10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "migrazione dati di sole INSERT create-if-missing (0023) accanto al pattern di sole UPDATE-su-valore-base gia' in uso (0022): stessa guardia fail-loud a due fasi (risolvi tutto -> raise se non risolte e catalogo presente -> scrivi), ma senza il _TEMPLATE_MIGRAZIONE condiviso perche' la forma delle scritture e' diversa (insert vs update)"
    - "test di migrazione su catalogo REALE (scripts.seed.seed su un DB a 0022), non curatela sintetica: il rischio che 0023 doveva coprire era un mojibake/drift del catalogo vero, non un caso di laboratorio"
    - "downgrade simmetrico all'upgrade per costruzione (voce.livello == opzione.code), non per traccia esplicita di chi ha scritto la riga: piu' semplice del 'track chi ha creato' proposto dalla review, stesso principio gia' in uso nella 0022"

key-files:
  created:
    - backend/alembic/versions/0023_pavimenti_alternativi.py
  modified:
    - backend/alembic/versions/0021_assi_pro_da_livello_e_chiavi_mirate.py
    - backend/tests/test_migrazioni_sqlite.py
    - .planning/phases/09-configuratore-pro/09-HUMAN-UAT.md

key-decisions:
  - "Le costanti _OPZIONI_NUOVE/_EFFETTI_AGGIUNTI/_EFFETTI_RIMOSSI della 0023 sono generate da uno script usa-e-getta (diff fra git show 2b6e29b:seed-domande.json e il file committato dopo il 09-10, encoding utf-8 esplicito), non scritte a mano voce per voce: 3 opzioni + 175 effetti, troppi per la trascrizione manuale senza errore"
  - "La guardia fail-loud della 0023 controlla solo la presenza della domanda 'tipo_pavimento' (non anche 'finitura'): sullo stesso catalogo le due domande sono sempre seminate insieme, un controllo su una sola basta e riusa lo stesso principio del template di applica_taratura.py"
  - "WR-02 risolto rendendo il downgrade della 0021 simmetrico ESATTAMENTE a cio' che l'upgrade scrive (voce.livello == opzione.code), invece di tracciare chi ha creato la riga: stesso schema gia' collaudato dalla 0022 (il cui downgrade tocca solo effetti, mai domanda/opzione)"

requirements-completed: [CFG-02, CFG-03, WIZ-04]

duration: ~3h
completed: 2026-09-28
---

# Phase 09 Plan 14: Gap closure finale — migrazione 0023, WR-02, dev.db a head Summary

**Migrazione Alembic 0023 (3 opzioni pavimento + 175 effetti, generata dal diff del catalogo reale, fail-loud e reversibile) porta G1/G2 sui DB esistenti; downgrade della 0021 corretto (WR-02); dev.db a 0023 (head) con il computo reale verificato su tutte le 7 opzioni di pavimento senza alternative sommate; suite backend 849 passed/5 skipped, build e lint frontend verdi**

## Performance

- **Duration:** ~3h
- **Tasks:** 3/3 completati
- **Files modified:** 4 (1 creato, 3 modificati)

## Accomplishments

- `backend/alembic/versions/0023_pavimenti_alternativi.py`: migrazione dati esplicita che porta le tre opzioni pavimento (laminato/vinilico_lvt/moquette) e i 175 effetti a bersaglio naturale (includi/escludi sui pavimenti alternativi e su A.6.3/A.6.9, `fattore_quantita` di quota bagno D-02 sulle voci individuali del gres a pavimento) su ogni DB gia' a 0022. Guardia fail-loud a due fasi: risolve TUTTE le chiavi naturali (voce sempre per codice/descrizione esatta; opzione gia' presente o fra quelle appena create) PRIMA di scrivere, poi `RuntimeError` se almeno una non risolve e il catalogo e' gia' presente (domanda `tipo_pavimento` esistente); no-op esplicito su DB vergine o popolato di sole righe fittizie. Create-if-missing sulla stessa chiave naturale del seed: idempotente su un secondo upgrade e su un DB dove il seed nuovo e' gia' girato. Downgrade tollerante che toglie solo cio' che l'upgrade ha scritto, cancella le tre opzioni nuove solo se restano senza effetti residui.
- WR-02 della code review (09-REVIEW.md): il downgrade della 0021 cancellava sempre `domanda`/`opzione_domanda` di `finitura`, anche quando preesistevano prima della 0021 (es. seminate dal seed su un DB nuovo) — un downgrade asimmetrico che distruggeva curatela mai scritta dall'upgrade. Ora rimuove solo gli effetti `includi` il cui bersaglio ha `voce.livello == opzione.code` (esattamente cio' che la sezione (A) dell'upgrade crea), mai domanda/opzione. `upgrade()` invariato (verificato: il diff tocca solo `downgrade()` e il suo docstring).
- `backend/dev.db` portato a `0023 (head)` (backup `dev.db.bak-pre-0023-20260928-191114`, gitignored). `scripts/seed.py` rieseguito dopo la migrazione: 0 righe nuove (374 effetti e 7 opzioni `tipo_pavimento` invariati prima/dopo) — conferma che dev.db aveva gia' il catalogo del 09-10 seminato localmente, la migrazione ha solo allineato `alembic_version`.
- Computo Pro reale verificato su una COPIA di dev.db (mai il file vero), Reggio Emilia/85 m2/tipo totale/finitura medio, per tutte le 7 opzioni di `tipo_pavimento` lette dal DB: nessuna doppia posa in A.6, nessuna doppia battiscopa, levigatura marmo (A.6.9) mai presente, levigatura parquet (A.6.10) solo con parquet, posa rivestimenti sempre 1 voce, LVT/laminato/sottofondo/moquette solo con la loro opzione in B-FINITURE > PAVIMENTI, una sola fornitura gres a pavimento per ogni scelta (con quota bagno per le opzioni non-gres, quota assente per moquette per decisione 09-09). Tabella completa in `09-HUMAN-UAT.md`.
- `09-HUMAN-UAT.md`: sezione "Ri-collaudo gap G1..G4" con la tabella dei controlli automatici e 15 nuove voci di checklist (`status: pending`, la spunta le fa solo Riccardo) — G1/G2/G3/G4 piu' cinque "scelte di Claude da confermare" (battiscopa legno anche con laminato/vinilico/moquette, moquette senza posa dedicata, posa rivestimenti A.6.3/A.6.4 per fascia, quale fornitura gres resta per livello, sottofondo solo con laminato).
- Gate: suite backend completa **849 passed, 5 skipped** (0:31:39), `npm run build` e `npm run lint` verdi (solo warning preesistenti `react(set-state-in-effect)`/`react(only-export-components)`).

## Task Commits

1. **Task 1: Migrazione 0023 esplicita, idempotente e rumorosa + test** - `db0e358` (feat)
2. **Task 2: WR-02 — downgrade della 0021 limitato a cio' che la 0021 crea** - `6971054` (fix)
3. **Task 3: dev.db a head, gate completi, controlli sul computo reale, checklist di ri-collaudo** - committed with this SUMMARY

Deviazione committata separatamente durante il Task 1 (vedi Deviazioni): `e33eab4` (fix).

_Nota: entrambi i Task 1 e 2 avevano `tdd="true"` — test e implementazione sono stati scritti nello stesso commit (non RED poi GREEN separati), stesso precedente gia' documentato nei piani 09-09/09-11 di questa fase._

## Files Created/Modified

- `backend/alembic/versions/0023_pavimenti_alternativi.py` (nuovo) - migrazione dati G1/G2, `_OPZIONI_NUOVE`/`_EFFETTI_AGGIUNTI`/`_EFFETTI_RIMOSSI` generate dal diff del catalogo reale, guardia fail-loud, create-if-missing, downgrade tollerante
- `backend/alembic/versions/0021_assi_pro_da_livello_e_chiavi_mirate.py` - `downgrade()` limitato agli effetti `includi` con `voce.livello == opzione.code` (WR-02), `upgrade()` invariato
- `backend/tests/test_migrazioni_sqlite.py` - 6 test nuovi su 0023 (resolved==total sul catalogo reale, ricostruzione senza doppioni, idempotenza, no-op su seed gia' passato, fail-loud senza scritture, round-trip upgrade/downgrade/upgrade), 2 test nuovi su WR-02 (effetto curato a mano su voce senza livello sopravvive, round-trip senza doppioni con finitura preesistente), 1 test esistente aggiornato alle nuove attese del downgrade 0021, assertion sulla testa della catena da 0022 a 0023
- `.planning/phases/09-configuratore-pro/09-HUMAN-UAT.md` - `status: pending`, sezione "Ri-collaudo gap G1..G4" con tabella dei controlli automatici e 15 voci di checklist

## Decisions Made

Vedi `key-decisions` in frontmatter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Helper di test con sessionmaker divergente dalla produzione**
- **Found during:** Task 3, prima esecuzione della suite backend completa
- **Issue:** `_semina_catalogo_reale` (helper dei test 0023 del Task 1) costruiva `sessionmaker(bind=engine_dedicato)` per conto proprio invece di usare `tests.session_factory.sessione_di_test(engine)`. Il meta-test `test_configurazione_sessione.py::test_nessun_file_di_test_costruisce_un_sessionmaker_per_conto_suo` (WR-04 di una fase precedente) lo ha intercettato: il default `autoflush=True` di un sessionmaker "nudo" diverge dalla configurazione di produzione (`autocommit=False, autoflush=False`, vedi `app/db.py`), la stessa divergenza che in passato aveva reso invisibile a 555 test una violazione di chiave naturale.
- **Fix:** sostituita la costruzione diretta con `sessione_di_test(engine_dedicato)` dalla fabbrica condivisa.
- **Files modified:** `backend/tests/test_migrazioni_sqlite.py`
- **Verification:** `pytest tests/test_migrazioni_sqlite.py tests/test_configurazione_sessione.py -q` -> 33 passed; suite completa rieseguita da capo -> 849 passed, 5 skipped, 0 failed
- **Committed in:** `e33eab4`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessario per la correttezza della suite di test (una divergenza autoflush avrebbe potuto nascondere futuri bug di integrita' referenziale, stesso precedente gia' documentato dal WR-04). Nessuno scope creep: solo l'helper di test toccato, non il codice di produzione.

## Issues Encountered

Nessuno oltre alla deviazione sopra. La generazione delle costanti della 0023 (diff fra base 2b6e29b e il seed committato) ha prodotto 175 effetti — molti di piu' del previsto a occhio, perche' il 09-09/09-10 ha ridisegnato la governance dell'intera A.6 e del gres a pavimento (non solo aggiunto le tre opzioni nuove): verificato riga per riga che il conteggio corrisponde esattamente al diff (nessun effetto rimosso dalla base, `_EFFETTI_RIMOSSI` vuoto) e che tutte le chiavi risolvono sul catalogo reale prima di fidarsene nella migrazione.

## User Setup Required

None - nessuna configurazione di servizi esterni richiesta. Backup pre-migrazione di `backend/dev.db` creato (`dev.db.bak-pre-0023-20260928-191114`, gitignored, contiene le stime salvate di Riccardo incluse quelle pre-esistenti come la stima 31).

## Next Phase Readiness

- G1/G2/G3/G4 chiusi nel codice e nei dati di ogni ambiente che passera' da questa migrazione (dev.db verificato, Postgres di produzione al push di fine Fase 10). WR-02 chiuso. WR-01 (verifica su Postgres) resta esplicitamente rimandato al push di fine Fase 10, come da obiettivo del piano — nessun Postgres disponibile in questo ambiente.
- `09-HUMAN-UAT.md` pronto per il ri-collaudo di Riccardo: le 15 nuove voci (G1..G4 + cinque scelte di Claude da confermare) restano non spuntate, nessun esecutore le ha marcate.
- Fase 09 completa: 14/14 piani (8 originari + 6 di gap closure). Prossimo: Fase 10.

---
*Phase: 09-configuratore-pro*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: `backend/alembic/versions/0023_pavimenti_alternativi.py`
- FOUND: `backend/alembic/versions/0021_assi_pro_da_livello_e_chiavi_mirate.py`
- FOUND: `backend/tests/test_migrazioni_sqlite.py`
- FOUND: `.planning/phases/09-configuratore-pro/09-HUMAN-UAT.md`
- FOUND: commit `db0e358`
- FOUND: commit `6971054`
- FOUND: commit `e33eab4`
