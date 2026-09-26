---
phase: 09-configuratore-pro
plan: 06
subsystem: api
tags: [taratura, coefficienti-pro, alembic, cfg-04, seed, migrazione]

# Dependency graph
requires:
  - phase: 09-configuratore-pro
    provides: "09-01: genera_excel_taratura.py (leggi_decisioni, CoeffDeciso, proponi_coefficiente/PROPOSTA_PER_CLASSE), docs/taratura/09-taratura-pro-compilato.xlsx (bozza-accettata); 09-04: migrazione 0021 (asse finitura da voce.livello); 09-07: applica_taratura.py (applica_assi, risolvi_chiave_naturale, main con --file/--solo-assi/--dry-run)"
provides:
  - "backend/scripts/applica_taratura.py estesa: applica_coefficienti()/calcola_classi() (parte coefficienti) + emetti_migrazione() (diff -> modulo Alembic autosufficiente) + main() con --migrazione/--slug/--base-rev; senza --solo-assi applica assi E coefficienti in un'unica esecuzione"
  - "backend/seed_data/taratura-classi.json: valori per classe (9 classi) della bozza accettata, letti a runtime da computo_parsing.coefficienti_per_voce()"
  - "backend/seed_data/seed-dettaglio-pro.json (+ copia docs/): coefficienti tarati per i DB nuovi, 573 righe applicate dalla bozza accettata"
  - "backend/alembic/versions/0022_taratura_pro_approvata.py: applica la taratura ai DB esistenti (prima uscita di emetti_migrazione, base-rev 2089460 del 09-02)"
  - "computo_parsing.coefficienti_per_voce() basata su proponi_coefficiente() + taratura-classi.json (fallback a PROPOSTA_PER_CLASSE x TIPO_FACTOR), non piu' 0.6/0.15 uniforme"
  - "scripts/seed.py:_upsert_coefficiente_qta create-if-missing (D-41): il seed non riscrive piu' i coefficienti esistenti al boot"
affects: [09-08, 09-09, 09-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "applica_taratura.py e' ora un canale UNICO file-di-decisioni -> tre destinazioni (seed JSON nuovi DB, migrazione DB esistenti, taratura-classi.json per i computi futuri), con la stessa disciplina di applica_assi: rigenerativo/idempotente, chiavi non risolte saltate senza eccezione, mai coefficiente_impresa"
    - "emetti_migrazione() tratta una migrazione come uno SNAPSHOT: nessuna lettura di file esterni a runtime, diff in chiavi naturali incorporato come costanti (_COEFFICIENTI/_VALORI_EFFETTO/_INCLUDI_SPOSTATI/_EFFETTI_RIMOSSI) sempre presenti anche vuote, upgrade aggiorna SOLO le righe ancora al valore base (tolleranza 1e-6), downgrade simmetrico — una taratura fatta dal pannello dopo la migrazione non viene mai sovrascritta"
    - "coefficienti_per_voce() ha ora due fonti in ordine di priorita': taratura-classi.json (primaria, caricamento pigro/in cache) poi PROPOSTA_PER_CLASSE x TIPO_FACTOR (fallback di bootstrap, mai la fonte primaria) — stesso schema a due livelli di applica_assi/applica_coefficienti (bozza vs curatela)"
    - "Test dei quattro rami di emetti_migrazione su una 0022 SINTETICA (stesso _TEMPLATE_MIGRAZIONE, costanti ad hoc) dentro una copia temporanea di alembic/: necessario perche' la 0022 REALE ha due delle quattro costanti vuote (nessun valore di stepper o asse spostato tra la base 09-02 e la bozza corrente)"

key-files:
  created:
    - backend/seed_data/taratura-classi.json
    - backend/alembic/versions/0022_taratura_pro_approvata.py
  modified:
    - backend/scripts/applica_taratura.py
    - backend/tests/test_applica_taratura.py
    - backend/seed_data/seed-dettaglio-pro.json
    - docs/seed-dettaglio-pro.json
    - backend/app/services/computo_parsing.py
    - backend/scripts/seed.py
    - backend/tests/test_seed_dettaglio.py
    - backend/tests/test_taratura_pro.py
    - backend/tests/test_migrazioni_sqlite.py
    - backend/tests/test_dettaglio_pro.py
    - backend/tests/test_dettaglio_pro_livelli.py
    - .planning/phases/09-configuratore-pro/deferred-items.md

key-decisions:
  - "DATO_PER_CLASSE mappa 7 dei 15 dati_richiesti del 09-01 (quota_calpestabile/mq_rivestimento_bagno/ml_battiscopa_per_mq/quota_massetto/mq_pareti_soffitti_per_mq/quota_demolizioni/superficie_finestrata) alle rispettive classi di proponi_coefficiente; gli altri 8 (rivestimento_cucina, mq_controsoffitto, ecc.) non hanno una classe dedicata e restano fuori, come dichiarato dal piano"
  - "calcola_classi() usa la MEDIANA dei coefficienti finali decisi per classe/tipo, con override dal dato_richiesto (tipo totale, leggera/moderata = totale x TIPO_FACTOR) quando presente e numericamente interpretabile; classi senza voci decise e senza dato usano PROPOSTA_PER_CLASSE x TIPO_FACTOR — mai un buco nelle 9 classi"
  - "emetti_migrazione tratta SOLO gli effetti con target_voce (non target_sottocategoria): e' l'unico bersaglio che applica_assi/applica_coefficienti producono davvero oggi; estendere a target_sottocategoria resta possibile ma non necessario per questo piano"
  - "_prossima_revisione deriva revision/down_revision dal numero piu' alto trovato nei nomi file di versions_dir (catena lineare 0001..0021), non da alembic.script.ScriptDirectory: piu' semplice e sufficiente per una catena che e' sempre lineare per costruzione in questo progetto"
  - "base-rev 2089460 (commit 09-02 che ha chiuso seed-domande.json): verificato con git log che seed-dettaglio-pro.json a quel commit e' ancora la bozza 0.6/0.15 pre-09-06 (nessun piano intermedio lo tocca)"

requirements-completed: [CFG-04]

# Metrics
duration: ~2h30min
completed: 2026-09-26
---

# Phase 09 Plan 06: Taratura dei coefficienti su tre canali (DB nuovi, DB esistenti, computi futuri) Summary

**`applica_taratura.py` diventa il canale unico file-di-decisioni -> seed JSON (DB nuovi) + migrazione Alembic 0022 (DB esistenti) + `taratura-classi.json` (computi futuri caricati da admin), applicato sulla bozza accettata reale: 573 coefficienti, 9 classi, 309 righe nella 0022, validato su copia di dev.db.**

## Performance

- **Duration:** ~2h30min
- **Tasks:** 4/4
- **Files modified:** 10 modificati, 2 creati

## Accomplishments

- **Task 1** — `applica_coefficienti()` (OK/ATTUALE/MODIFICATO -> valore finale per voce/tipo, voci non presenti nel seed segnalate e saltate, valori negativi rifiutati) e `calcola_classi()` (mediana per classe/tipo, override da `dati_richiesti` via `DATO_PER_CLASSE`, fallback a `PROPOSTA_PER_CLASSE x TIPO_FACTOR`). Applicato sulla bozza accettata reale: `seed-dettaglio-pro.json` (573 coefficienti, identico bit-per-bit alla copia `docs/`) e `taratura-classi.json` (9 classi, tutte uguali a `PROPOSTA_PER_CLASSE x TIPO_FACTOR` — coerenza attesa perche' la bozza accettata e' proprio quella proposta). Idempotenza verificata: secondo lancio, nessun diff.
- **Task 2** — `computo_parsing.coefficienti_per_voce()` riscritta su `proponi_coefficiente()` + `taratura-classi.json` (fallback se file/classe manca, upload mai bloccato); le voci `cad` con parola chiave di domanda mirata restano invariate sullo stepper omonimo. `scripts/seed.py:_upsert_coefficiente_qta` create-if-missing (D-41): un coefficiente curato (da pannello o dalla 0022) non torna piu' alla bozza a ogni deploy.
- **Task 3** — `emetti_migrazione()`: diff in chiavi naturali fra JSON base e nuovi -> modulo Alembic autosufficiente (nessuna lettura di file esterni a runtime, quattro costanti sempre presenti anche vuote); `main()` con `--migrazione`/`--slug`/`--base-rev` legge i JSON base via `git show` e li passa a `emetti_migrazione`.
- **Task 4** — Generata la 0022 reale (`--base-rev 2089460`, il commit 09-02 che ha chiuso `seed-domande.json`): 309 righe di coefficiente, 0 valori di effetto, 0 assi spostati, 27 effetti rimossi. Validata su una copia di `backend/dev.db` (mai l'originale): `upgrade head -> downgrade 0021 -> upgrade head` senza errori, 309/309 righe coefficiente risolte e applicate correttamente. Cinque test su una 0022 sintetica (stesso template, costanti ad hoc) provano tutti i quattro rami del diff. Le due asserzioni numeriche pinnate su A.1.1.1 (`51.00`/`1836`/`2754`, dalla bozza 0.6 pre-09-06) ora derivano dal coefficiente seminato letto a DB.

## Task Commits

1. **Task 1: applica_coefficienti + calcola_classi** - `9e6c35f` (feat)
2. **Task 2: bozza computi futuri da taratura-classi.json + seed create-if-missing** - `41b1b90` (feat), con una correzione: `ba6a183` (fix) — test di coerenza spostato su `sessione_di_test` invece di un `sessionmaker` diretto (violava la guardia AST di `test_configurazione_sessione.py`)
3. **Task 3: emetti_migrazione + wiring CLI** - `5d3dbf2` (feat)
4. **Task 4: 0022 generata dal comando + test numerici adeguati** - `331bb49` (feat)

## Files Created/Modified

- `backend/scripts/applica_taratura.py` — `applica_coefficienti()`, `calcola_classi()`, `DATO_PER_CLASSE`, `emetti_migrazione()`, `_record_effetti()`/`_diff_coefficienti()`/`_prossima_revisione()`, `main()` con `--migrazione`/`--slug`/`--base-rev` (default `--solo-assi` rimosso: ora applica sempre anche i coefficienti)
- `backend/seed_data/taratura-classi.json` — nuovo: 9 classi, stato `bozza-accettata`
- `backend/seed_data/seed-dettaglio-pro.json` / `docs/seed-dettaglio-pro.json` — coefficienti tarati (573 righe), identici bit-per-bit
- `backend/alembic/versions/0022_taratura_pro_approvata.py` — nuovo: 309 righe coefficiente, 27 effetti rimossi (non risolti su questa copia di dev.db)
- `backend/app/services/computo_parsing.py` — `coefficienti_per_voce()` riscritta, `_carica_taratura_classi()`
- `backend/scripts/seed.py` — `_upsert_coefficiente_qta` create-if-missing
- `backend/tests/test_applica_taratura.py` — `TestApplicaCoefficienti`, `TestCalcolaClassi`, `TestEmettiMigrazione`, `TestMainArgomentiMigrazione`
- `backend/tests/test_taratura_pro.py` — `TestCoefficientiPerVoce`
- `backend/tests/test_seed_dettaglio.py` — create-if-missing, valori del seed JSON, coerenza JSON<->decisioni
- `backend/tests/test_migrazioni_sqlite.py` — cinque test 0022 su costanti sintetiche
- `backend/tests/test_dettaglio_pro.py`, `backend/tests/test_dettaglio_pro_livelli.py` — oracolo A.1.1.1 derivato dal coefficiente a DB
- `.planning/phases/09-configuratore-pro/deferred-items.md` — due fallimenti pre-esistenti loggati (vedi Deviations)

## Decisions Made

Vedi `key-decisions` in frontmatter. In sintesi: `DATO_PER_CLASSE` mappa 7 dei 15 dati_richiesti alle classi che hanno un coefficiente per m2; `calcola_classi()` usa la mediana con override dal dato_richiesto; `emetti_migrazione` tratta solo `target_voce` (unico bersaglio prodotto oggi); revision/down_revision dal numero file piu' alto in `versions_dir`; base-rev 2089460 verificato con git log.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test di coerenza JSON<->decisioni violava la guardia AST anti-sessionmaker**
- **Found during:** verifica suite completa dopo il Task 2
- **Issue:** `test_seed_json_coerente_con_le_decisioni_del_file_di_taratura` costruiva un `sessionmaker(bind=engine)` per conto suo (per leggere `backend/dev.db` in sola lettura), violando `test_configurazione_sessione.py::test_nessun_file_di_test_costruisce_un_sessionmaker_per_conto_suo` (WR-04: ogni test deve restare sulla configurazione di produzione via `tests.session_factory.sessione_di_test`).
- **Fix:** sostituito `sessionmaker(bind=engine)` con `sessione_di_test(engine)`.
- **Files modified:** `backend/tests/test_seed_dettaglio.py`
- **Commit:** `ba6a183`

### Fallimenti pre-esistenti, non causati da questo piano (loggati, non corretti — scope boundary)

Trovati lanciando la suite completa dopo il Task 2 (non richiesta dal piano, lanciata per prudenza), entrambi riprodotti come identici PRIMA e DOPO i Task 1/2 di questo piano:

- `test_dettaglio_pro.py::test_post_risposte_payload_generico_ricalcola_e_valida` — scritto nel 09-05, prima della decisione D-02 del 09-07 (A.6.1 resta sempre inclusa a prescindere dal pavimento scelto), mai aggiornato.
- `test_stima_tier.py::TestStimaFreeNonDiventaPro::test_post_risposte_403` — posta il payload FLAT pre-09-05, il contratto generico del 09-05 richiede `{risposte: {...}}` e risponde 422 prima del 403 atteso, mai aggiornato.

Dettagli completi in `.planning/phases/09-configuratore-pro/deferred-items.md`.

---

**Total deviations:** 1 auto-fixed (Rule 3), 2 fallimenti pre-esistenti loggati come deferred (fuori scope)
**Impact on plan:** Nessuno scope creep: il fix e' confinato al test che questo piano ha scritto; i due fallimenti pre-esistenti non toccano ne' l'endpoint ne' il contratto di nessun task di questo piano.

## Known Stubs

Nessuno. `taratura-classi.json` dichiara esplicitamente `"stato": "bozza-accettata"` (letto e stampato da `applica_taratura.py` a ogni lancio, come per gli assi del 09-07) — comportamento voluto (D-08, vincolo del 2026-09-26), non uno stub.

## Riapplicazione quando arriva il file vero di Riccardo

```
cd backend && .venv/Scripts/python.exe scripts/applica_taratura.py --file <xlsx compilato davvero> --migrazione
```

Base di default `HEAD` (i JSON versionati = cio' che i DB hanno dopo la 0022): applica assi + coefficienti, riscrive i JSON e la migrazione successiva (0023+) dal diff. Nessuna ripianificazione necessaria.

## Verification

- `cd backend && .venv/Scripts/python.exe -m pytest tests/test_applica_taratura.py tests/test_taratura_pro.py tests/test_seed_dettaglio.py tests/test_migrazioni_sqlite.py tests/test_dettaglio_pro.py tests/test_dettaglio_pro_livelli.py tests/test_upload_listino.py -q` — 158 passed, 1 failed (pre-esistente, deferred), invariato rispetto a prima di questo piano
- Suite completa lanciata una volta a meta' piano (dopo Task 2): 795 passed, 5 skipped, 5 failed (2 di taratura risolti nel Task 4, 1 di configurazione risolto subito, 2 pre-esistenti loggati come deferred)

## Issues Encountered

Vedi Deviations. Nessun blocco: il difetto scoperto e' stato corretto nello stesso piano; i due fallimenti pre-esistenti sono fuori scope e documentati.

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta.

## Next Phase Readiness

- CFG-04 e' chiuso sui tre canali (DB nuovi, DB esistenti via 0022, computi futuri via `taratura-classi.json`), con un comando ripetibile pronto a produrre la migrazione della taratura vera quando Riccardo la restituisce (`--migrazione` senza `--base-rev`, default HEAD).
- `docs/taratura/09-taratura-pro-compilato.xlsx` resta la bozza accettata dichiarata dal 09-01; nessuna modifica a quel file o a `genera_excel_taratura.py` in questo piano.
- I 27 effetti in `_EFFETTI_RIMOSSI` della 0022 non risolti sulla copia di dev.db usata per la validazione non bloccano nulla: sono chiavi naturali non trovate (comportamento dichiarato, "saltate senza errore") e i nuovi assegnamenti corrispondenti arriveranno comunque via seed create-if-missing al boot.

---
*Phase: 09-configuratore-pro*
*Completed: 2026-09-26*

## Self-Check: PASSED

- `backend/scripts/applica_taratura.py` — FOUND
- `backend/seed_data/taratura-classi.json` — FOUND
- `backend/alembic/versions/0022_taratura_pro_approvata.py` — FOUND
- `backend/app/services/computo_parsing.py` — FOUND
- `backend/tests/test_migrazioni_sqlite.py` — FOUND
- Commit `9e6c35f` — FOUND in `git log`
- Commit `41b1b90` — FOUND in `git log`
- Commit `ba6a183` — FOUND in `git log`
- Commit `5d3dbf2` — FOUND in `git log`
- Commit `331bb49` — FOUND in `git log`
