---
phase: 09-configuratore-pro
plan: 07
subsystem: api
tags: [catalogo-domande, motore-pro, effetti, taratura, cfg-02, admin]

# Dependency graph
requires:
  - phase: 09-configuratore-pro
    provides: "09-01: genera_excel_taratura.py (leggi_decisioni, AsseDeciso, stato bozza-accettata), docs/taratura/09-taratura-pro-compilato.xlsx; 09-03: risolvi_effetti_pro()/RisoluzionePro in effetti.py, DettaglioProService riscritto sul catalogo"
provides:
  - "backend/scripts/applica_taratura.py: applica_assi() ripetibile che ricostruisce da zero, dalle decisioni approvate del file di taratura, gli effetti Pro a bersaglio naturale su finitura/tipo_pavimento/bagni/porte/condizionatori"
  - "backend/seed_data/seed-domande.json aggiornato: 37 finitura, 26/11/11 stepper, 17 tipo_pavimento, 10 escludi_sempre, 18 sempre_inclusa, 3 fattore_pavimento — dalla bozza accettata del 09-01"
  - "backend/tests/fixtures/famiglie_alternative_pro.json: 126 righe, fonte del test di conteggio CFG-02"
  - "TestFamiglieAlternative in test_dettaglio_pro_alternative.py: CFG-02 verificato per famiglia su TUTTE le sottocategorie catalogo (non solo GRES/A.6)"
  - "Pannello admin Dettaglio Pro: livello voce in sola lettura, link a /admin/domande"
affects: [09-06, 09-08, 09-09, 09-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "applica_assi() e' rigenerativo, non incrementale: a ogni chiamata pulisce TUTTI gli effetti a bersaglio naturale delle domande che possiede e li ricostruisce da zero dalle decisioni correnti — idempotenza per costruzione, non per convenzione"
    - "D-02 senza doppio bersaglio: una voce 'sempre presente a prescindere dalla scelta di un asse' (la quota bagno A.6.1) non riceve un `includi` sull'opzione alternativa — resterebbe bersaglio di DUE opzioni e romperebbe il conteggio per-asse di CFG-02 — resta NON governata (regola 4, sempre inclusa) e scala solo via `fattore_quantita`"
    - "Deduplica famiglia-su-stessa-opzione: quando la bozza assegna piu' voci alla stessa opzione della stessa famiglia (collisione), applica_assi tiene la prima (voce_id minore) come includi e le altre come includi+escludi (governate ma sempre escluse), mai piu' di una voce viva per famiglia/opzione"
    - "Guardia contro i falsi positivi del match per parola-chiave: le sei famiglie di alternative per fascia di prezzo (sanitari_*/porte_apertura/condizionatori_marca) sono ignorate quando il bersaglio e' una sottocategoria 'gerarchica' (A-EDILE rimozioni/montaggi che menzionano la parola nel testo, non prodotti alternativi)"
    - "Test di conteggio raggruppato per FAMIGLIA (non per sottocategoria+famiglia): una famiglia di alternative puo' avere membri in sottocategorie diverse restando un'unica scelta esclusiva sullo stesso asse"

key-files:
  created:
    - backend/scripts/applica_taratura.py
    - backend/tests/test_applica_taratura.py
    - backend/tests/fixtures/famiglie_alternative_pro.json
  modified:
    - backend/seed_data/seed-domande.json
    - backend/tests/test_dettaglio_pro_alternative.py
    - backend/tests/test_seed_domande_pro.py
    - backend/tests/test_effetti_pro.py
    - frontend/src/pages/admin/DettaglioProPage.tsx

key-decisions:
  - "fattore_pavimento non produce mai un `includi`: la voce (A.6.1, quota bagno) resta non governata e sempre inclusa; solo la quantita' scala con fattore_quantita sulle opzioni diverse da gres — altrimenti sarebbe bersaglio di due opzioni contemporaneamente e romperebbe il conteggio per-asse di CFG-02 (09-03)"
  - "Deduplica automatica (Rule 1) delle famiglie di alternative che la bozza 09-01 assegna TUTTE alla stessa opzione: scoperto sui dati reali su fornitura_pavimento_parquet (6 voci) e battiscopa (4 voci), entrambe -> parquet"
  - "Filtro sottocategorie_gerarchiche (Rule 1) per i falsi positivi del match per parola-chiave delle sei famiglie sanitari_*/porte_apertura/condizionatori_marca su voci A-EDILE di rimozione/montaggio (7 righe reali: A.0.3, A.0.5(x2 famiglie diverse sulla stessa voce), A.0.6, A.0.16, A.0.17, A.10.1)"
  - "Test di conteggio (Task 2) escludono dal controllo 'al massimo una voce' le famiglie 'comune' (sempre_inclusa), 'stepper_*' (quantita' per unita') e 'finitura:<sottocategoria>' (varieta' di SKU migrata da voce.livello, deliberatamente multi-voce, gia' verificata dalla 09-03) — non sono alternative a scelta singola per costruzione"
  - "Gruppo di conteggio per FAMIGLIA sola, non (sottocategoria, famiglia): condizionatori_marca ha membri sia in D-PRODOTTI sia (per il falso positivo gerarchico, ora filtrato) in A-EDILE; resta comunque un'unica scelta esclusiva sull'asse finitura"

requirements-completed: [CFG-02]

# Metrics
duration: ~3h30min
completed: 2026-09-26
---

# Phase 09 Plan 07: Curatela degli assi (D-08) e chiusura di CFG-02 su tutte le sottocategorie Summary

**`applica_taratura.py` applica ripetibilmente la curatela degli assi del file di decisioni al catalogo; CFG-02 e' verificato per famiglia su tutte le sottocategorie catalogo, non solo gres e A.6 — con due bug reali di curatela scoperti e corretti nel processo (doppio bersaglio A.6.1, falsi positivi di parola-chiave su voci A-EDILE gerarchiche).**

## Performance

- **Duration:** ~3h30min
- **Tasks:** 3/3
- **Files modified:** 5 modificati, 3 creati

## Accomplishments

- `backend/scripts/applica_taratura.py`: `risolvi_chiave_naturale()` (voce_id di dev.db -> chiave naturale categoria/sottocategoria/voce) + `applica_assi()` (funzione pura, nessun accesso a DB) che ricostruisce da zero gli effetti Pro a bersaglio naturale delle cinque domande gestite (finitura, tipo_pavimento, bagni, porte, condizionatori), lasciando intatto tutto il resto — inclusi gli effetti Free sulla stessa opzione (`eur_per_scostamento` di bagni/porte/condizionatori).
- Applicato sulla bozza accettata reale (`docs/taratura/09-taratura-pro-compilato.xlsx`, stato `bozza-accettata`): `seed-domande.json` aggiornato con 133 righe di decisioni tradotte in effetti (37 finitura, 26/11/11 stepper, 17 tipo_pavimento, 10 escludi_sempre, 18 sempre_inclusa, 3 fattore_pavimento), fixture `famiglie_alternative_pro.json` con 126 righe. Idempotenza verificata sui dati reali: hash identico dopo un secondo lancio.
- `TestFamiglieAlternative` in `test_dettaglio_pro_alternative.py`: per le 12 combinazioni finitura × tipo_pavimento, nessuna famiglia di alternative (sanitari, porte, condizionatori, posa/fornitura pavimento, battiscopa) mostra piu' di una voce nello stesso computo; ogni famiglia approvata ha almeno una combinazione in cui compare; A.6.1 (quota bagno, D-02) resta presente con parquet a quantita' ridotta dal fattore letto dal DB seminato; le voci escludi_sempre non compaiono mai.
- Pannello admin (`DettaglioProPage.tsx`): il Select del livello nel form voce e' ora testo in sola lettura "Livello storico: {nome|nessuno}" con link a `/admin/domande`; il salvataggio della voce continua a inviare il livello letto, invariato (CFG-03, nessuna perdita di dato storico).

## Task Commits

1. **Task 1: applica_assi() ripetibile + effetti Pro nel JSON + fixture delle famiglie** - `7333453` (feat), con due correzioni successive scoperte durante la verifica sui dati reali:
   - `356409f` (fix) — deduplica delle famiglie di alternative assegnate alla stessa opzione
   - `596f370` (fix) — D-02 senza doppio bersaglio + filtro dei falsi positivi gerarchici
2. **Task 2: test CFG-02 per famiglia su tutte le sottocategorie catalogo** - `4ff5215` (test)
3. **Task 3: livello della voce in sola lettura nel pannello admin** - `f0750c0` (feat)

_Nessun commit RED/GREEN separato: `tdd="true"` inteso come "scrivi test insieme al codice" (stesso schema delle 09-02/09-03), con l'eccezione dei due fix del Task 1 che sono commit `fix` distinti, scoperti durante la verifica sui dati reali dopo il primo commit `feat`._

## Files Created/Modified

- `backend/scripts/applica_taratura.py` - nuovo: `risolvi_chiave_naturale()`, `applica_assi()`, `main()` (`--file`/`--solo-assi`/`--dry-run`)
- `backend/tests/test_applica_taratura.py` - nuovo: 20 test su decisioni/JSON sintetici (nessun numero di taratura cablato)
- `backend/seed_data/seed-domande.json` - effetti Pro rigenerati dalla bozza accettata
- `backend/tests/fixtures/famiglie_alternative_pro.json` - nuovo: 126 righe
- `backend/tests/test_dettaglio_pro_alternative.py` - `TestFamiglieAlternative` (Task 2); due test 09-03 aggiornati per D-02 (A.6.1 ora sempre presente) e due test bagni spostati su una voce non toccata dalla curatela delle famiglie
- `backend/tests/test_seed_domande_pro.py` - due asserzioni 09-02 da conteggio esatto a minimo garantito/verifica strutturale (la curatela di questo piano aggiunge legittimamente altri bersagli allo stesso asse)
- `backend/tests/test_effetti_pro.py` - due test aggiornati per il nuovo comportamento di A.6.1 (non piu' bersaglio di `includi`)
- `frontend/src/pages/admin/DettaglioProPage.tsx` - Select livello -> testo in sola lettura + link

## Decisions Made

Vedi `key-decisions` in frontmatter. In sintesi: **fattore_pavimento non produce mai un `includi`** (A.6.1 resta non governata e sempre inclusa, sola la quantita' scala) per non rompere il conteggio per-asse della 09-03; **deduplica automatica** delle collisioni famiglia-su-stessa-opzione scoperte sui dati reali; **filtro dei falsi positivi gerarchici** delle sei famiglie per fascia di prezzo; test di conteggio raggruppato per **famiglia sola**, con esclusione esplicita delle famiglie non-esclusive (comune/stepper/finitura:SKU-variety).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Doppio bersaglio su A.6.1 rompeva il conteggio per-asse di CFG-02**
- **Found during:** Task 1, verifica del comando `--dry-run` sui dati reali seguita dall'esecuzione della suite completa
- **Issue:** il testo letterale dell'azione ("fattore_pavimento -> fattore_quantita... Le rendiamo bersaglio anche delle altre opzioni") avrebbe aggiunto un `includi` su A.6.1 per parquet/maxi_lastra/mosaico ACCANTO al suo `includi` esistente su gres — rendendola bersaglio di DUE opzioni contemporaneamente, che il test per-asse della 09-03 (`test_nessun_asse_include_piu_di_unopzione`) rileva correttamente come il bug che la fase chiude.
- **Fix:** A.6.1 non riceve mai un `includi` (nemmeno dalla sua riga `tipo_pavimento`->gres gemella): resta NON governata da alcun asse, quindi sempre inclusa per la regola 4 di `effetti.py`; solo `fattore_quantita` (sulle opzioni non-gres) ne riduce la quantita' alla quota bagno.
- **Files modified:** `backend/scripts/applica_taratura.py`, `backend/tests/test_applica_taratura.py`, `backend/tests/test_dettaglio_pro_alternative.py`, `backend/tests/test_effetti_pro.py`, `backend/tests/test_seed_domande_pro.py`
- **Commit:** `596f370`

**2. [Rule 1 - Bug] Famiglie di alternative con piu' voci sulla stessa opzione (bug di curatela della bozza 09-01)**
- **Found during:** Task 1, verifica sui dati reali
- **Issue:** la bozza assegna TUTTE le 6 voci di `fornitura_pavimento_parquet` e tutti i 4 zoccolini in legno di `battiscopa` alla STESSA opzione `parquet` — tornerebbero a sommarsi fra loro, esattamente il bug che la fase chiude, se applicate cosi' com'erano.
- **Fix:** deduplica automatica: quando piu' righe della stessa famiglia condividono (asse, opzione), tiene solo la prima (voce_id minore) come `includi`; le altre restano governate (per l'esclusione quando un'opzione diversa e' scelta) ma sempre escluse. Eccezione esplicita per `finitura:<sottocategoria>` (varieta' di SKU intenzionale).
- **Files modified:** `backend/scripts/applica_taratura.py`, `backend/tests/test_applica_taratura.py`
- **Commit:** `356409f`

**3. [Rule 1 - Bug] Falsi positivi del match per parola-chiave su voci A-EDILE gerarchiche**
- **Found during:** Task 1/2, suite completa dopo il redesign D-02
- **Issue:** le sei famiglie di alternative per fascia di prezzo (`sanitari_vaso`/`sanitari_bidet`/`sanitari_cassetta`/`sanitari_doccia_vasca`/`porte_apertura`/`condizionatori_marca`) di `genera_excel_taratura.py` (09-01) fanno match per parola-chiave sulla descrizione SENZA distinguere la sottocategoria: catturano anche righe A-EDILE gerarchiche di rimozione/montaggio che menzionano "bidet"/"doccia"/"condizionatore" nel testo (es. A.0.3 "Rimozione di apparecchi idro-termo-sanitari... doccia..." assegnata a finitura=base) — voci di logistica sempre necessarie, non prodotti alternativi. Il sintomo: 7 test pre-esistenti (09-02/09-03) che usavano queste voci come oracolo (es. il miscelatore bidet, A.0.3) le trovavano sparite dal computo di default.
- **Fix:** nuovo filtro in `applica_assi()` (`sottocategorie_gerarchiche`): una riga con una di queste sei famiglie su una voce la cui sottocategoria e' `famiglia='gerarchica'` viene ignorata (nessun effetto creato, resta sempre inclusa come prima di questa fase). `main()` popola il filtro da dev.db.
- **Files modified:** `backend/scripts/applica_taratura.py`, `backend/tests/test_applica_taratura.py`, `backend/tests/test_dettaglio_pro_alternative.py` (due test bagni spostati su una voce non toccata da questa curatela)
- **Commit:** `596f370`

---

**Total deviations:** 3 auto-fixed (Rule 1)
**Impact on plan:** Nessuno scope creep verso `genera_excel_taratura.py` (09-01, fuori dai `files_modified` di questo piano): tutti i fix vivono in `applica_taratura.py`, che e' esattamente il layer pensato per "correggere le decisioni sbagliate senza ripianificare". Il file di taratura reale (Excel) non e' stato toccato.

## Known Stubs

Nessuno. Le famiglie di alternative rimangono, per costruzione, una bozza di Claude non rivista da Riccardo (stato `bozza-accettata`, dichiarato dallo script a ogni lancio) — comportamento voluto (D-08, vincolo del 2026-09-26), non uno stub. Resta un debito noto e visibile: alcune assegnazioni per fascia di prezzo (es. sanitari_bidet: la voce economicamente piu' bassa "vince" il tier base anche se e' un accessorio diverso dal prodotto principale, come visto per il miscelatore) restano bozze da confermare — annotato in `09-TARATURA-TODO.md` (09-01) e non richiedono azione per chiudere questo piano.

## Riapplicazione quando arriva il file vero di Riccardo

```
cd backend && .venv/Scripts/python.exe scripts/applica_taratura.py --solo-assi
```
Legge `docs/taratura/09-taratura-pro-compilato.xlsx` (default), stampa lo stato del file (oggi `bozza-accettata`, con avviso esplicito), i conteggi per asse e le righe deduplicate/ignorate/modificate, e scrive `seed-domande.json` + la fixture. Nessuna ripianificazione necessaria.

## Verification

- `cd backend && .venv/Scripts/python.exe -m pytest tests/test_applica_taratura.py tests/test_dettaglio_pro_alternative.py tests/test_seed_domande_pro.py tests/test_estimation.py -x -q` — 77 passed
- Suite backend completa: 771 passed, 5 skipped (GTK3, invariati) in ~8 minuti
- `cd frontend && npm run build && npm run lint` — 0 errori (warning pre-esistenti nel resto della codebase)

## Issues Encountered

Vedi Deviations. Nessun blocco: tutti i difetti scoperti sono stati corretti nello stesso piano.

## User Setup Required

None - nessuna configurazione di servizio esterno richiesta.

## Next Phase Readiness

- CFG-02 e' chiuso su tutte le sottocategorie catalogo (non solo gres/A.6), con un comando ripetibile pronto a riapplicare la taratura vera quando Riccardo la restituisce.
- `docs/taratura/09-taratura-pro-compilato.xlsx` resta la bozza accettata dichiarata dal 09-01; nessuna modifica a quel file o a `genera_excel_taratura.py` in questo piano.
- Il piano 09-06 (coefficienti quantita') puo' estendere lo stesso `applica_taratura.py` con la parte coefficienti, come previsto dal piano.

---
*Phase: 09-configuratore-pro*
*Completed: 2026-09-26*

## Self-Check: PASSED

- `backend/scripts/applica_taratura.py` — FOUND
- `backend/tests/test_applica_taratura.py` — FOUND
- `backend/tests/fixtures/famiglie_alternative_pro.json` — FOUND (126 righe)
- `backend/seed_data/seed-domande.json` — FOUND (modificato)
- `backend/tests/test_dettaglio_pro_alternative.py` — FOUND (modificato)
- `frontend/src/pages/admin/DettaglioProPage.tsx` — FOUND (modificato)
- Commit `7333453` — FOUND in `git log`
- Commit `356409f` — FOUND in `git log`
- Commit `596f370` — FOUND in `git log`
- Commit `4ff5215` — FOUND in `git log`
- Commit `f0750c0` — FOUND in `git log`
