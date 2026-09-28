---
phase: 09-configuratore-pro
plan: 10
subsystem: database
tags: [taratura, configuratore-pro, pavimenti, test, gap-closure]

# Dependency graph
requires:
  - phase: 09-configuratore-pro
    provides: "proponi_assegnazione/applica_assi con regole G1/G2 (09-09): mappa A.6, bersagli condivisi, fail-loud"
provides:
  - "test_alternative_mondo_aperto.py: controllo CFG-02 a mondo aperto (perimetro/assi/combinazioni derivati dal catalogo, non da una lista di famiglie note)"
  - "seed-domande.json con 7 opzioni tipo_pavimento (gres/parquet/maxi_lastra/mosaico/laminato/vinilico_lvt/moquette) e A.6 intera governata"
  - "docs/taratura/09-taratura-pro-compilato.xlsx e 09-taratura-pro.xlsx aggiornati (foglio assi_proposti rigenerato, decisioni accettate conservate)"
affects: [09-14]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "test a mondo aperto: perimetro/assi/combinazioni/lavorazioni derivati dal catalogo seminato via query SQLAlchemy, unica lista scritta a mano (VOCI_COMUNI) per le voci sempre incluse per costruzione"
    - "voce.livello (colonna legacy, vestigiale dal 2021->0021) deve essere ripopolata a mano in dev.db PRIMA di --aggiorna-assi quando il DB e' fresco (scripts/seed.py non lo scrive mai): altrimenti proponi_assegnazione perde silenziosamente le decisioni finitura gia' accettate"

key-files:
  created:
    - backend/tests/test_alternative_mondo_aperto.py
  modified:
    - backend/seed_data/seed-domande.json
    - backend/tests/fixtures/famiglie_alternative_pro.json
    - docs/taratura/09-taratura-pro-compilato.xlsx
    - docs/taratura/09-taratura-pro.xlsx
    - backend/tests/test_dettaglio_pro_alternative.py
    - backend/tests/test_seed_domande_pro.py
    - backend/tests/test_effetti_pro.py
    - backend/tests/test_dettaglio_pro_livelli.py

key-decisions:
  - "dev.db del worktree ricostruito da zero (alembic upgrade head + scripts/seed.py) e voce.livello ripopolato a mano dalle 21 voci GRES gia' governate da finitura nel seed-domande.json committato, PRIMA di rigenerare i workbook — altrimenti --aggiorna-assi cancella silenziosamente le 21 decisioni finitura storiche (Rule 1, vedi Deviazioni)"
  - "le 11 voci RUBINETTERIE/PORTE/PRODOTTI che il vecchio seed aveva anche su voce.livello sono state ESCLUSE dalla ripopolazione (solo GRES): sono gia' governate dalla regola famiglie-per-fascia-di-prezzo, ripopolarle avrebbe creato una doppia proposta (finitura via livello + finitura via famiglia prezzo) sullo stesso bersaglio, rilevata da un MultipleResultsFound in scripts/seed.py"

requirements-completed: [CFG-02]

duration: ~5h (comprese due false partenze sul dev.db, vedi Deviazioni)
completed: 2026-09-28
---

# Phase 09 Plan 10: Gap G1/G2 — dati e prova a mondo aperto Summary

**Test CFG-02 a mondo aperto (perimetro/assi/combinazioni dal catalogo, non da una lista nota) dimostrato rosso sul seed di ieri e verde su quello di oggi: A.6 intera e i pavimenti alternativi (incluse le tre nuove opzioni laminato/vinilico LVT/moquette) sono ora governati uno-per-lavorazione**

## Performance

- **Duration:** ~5h
- **Tasks:** 3
- **Files modified:** 9 (1 creato, 8 modificati)

## Accomplishments

- `backend/tests/test_alternative_mondo_aperto.py`: un controllo CFG-02 che deriva perimetro (A.6 + sottocategorie pavimento di B-FINITURE + ogni sottocategoria bersaglio di un effetto `tipo_pavimento`), assi (domande pro con `includi`), combinazioni (opzioni attive di finitura x tipo_pavimento) e gruppi di lavorazione (classificazione testuale) dal catalogo seminato — l'unica lista scritta a mano e' `VOCI_COMUNI` (3 voci). Dimostrato **ROSSO** sul seed di ieri (A.6.3/.4/.7/.8/.9/.10 e le voci LVT/laminato/sottofondo/moquette non classificate, gruppi battiscopa/levigatura/posa_rivestimento/fornitura_pavimento con piu' di una voce), **VERDE** dopo il Task 2. `test_voce_trappola_viene_segnalata` gia' verde al commit RED (una voce mai vista dalla curatela viene sempre segnalata, anche dopo il fix).
- `tipo_pavimento` ha ora 7 opzioni (aggiunte a mano `laminato`/`vinilico_lvt`/`moquette`, effetti generati da `applica_taratura.py`). I workbook di taratura sono stati rigenerati con `--aggiorna-assi` (0 righe perse, decisioni gia' accettate conservate) e applicati con `--solo-assi`: A.6.7/A.6.8/A.6.10 e le forniture laminato/vinilico/sottofondo/moquette sono ora governate dall'asse `tipo_pavimento`; A.6.9 (levigatura marmo) esclusa su tutte le finiture; il gres a pavimento e' deduplicato a una fornitura per livello con quota bagno (`fattore_quantita`) sulle sei opzioni non-gres (moquette esclusa, D-02). Idempotente (secondo lancio bit-identico), zero mojibake, zero effetti duplicati.
- I test esistenti (`test_dettaglio_pro_alternative.py`, `test_seed_domande_pro.py`, `test_effetti_pro.py`) sono stati allineati all'invariante "bersagli condivisi" (09-09): una voce puo' essere bersaglio dell'`includi` di piu' opzioni dello stesso asse per costruzione (es. A.6.2 con parquet/laminato/vinilico_lvt), quindi il vecchio conteggio "al massimo un'opzione con una voce presente" e' stato sostituito da "ogni voce presente bersaglio di un includi dell'asse deve essere bersaglio dell'opzione SCELTA e non di un suo escludi". Aggiunti `test_moquette_non_riduce_a6_1` e `test_laminato_include_sottofondo_e_esclude_parquet`.
- Batteria mirata della fase (10 file, incluso il nuovo): **208 passed, 2 skipped** (WeasyPrint/GTK3 assente su Windows, limite noto).

## Task Commits

1. **Task 1 (RED): controllo CFG-02 a mondo aperto, rosso sul seed attuale** - `5120107` (test)
2. **Task 2 (GREEN): nuove opzioni pavimento, workbook aggiornati, seed e fixture rigenerati** - `b459d83` (feat)
3. **Task 3: test esistenti allineati ai bersagli condivisi** - `c82e7c2` (test)

## Files Created/Modified

- `backend/tests/test_alternative_mondo_aperto.py` (nuovo) - perimetro/assi/combinazioni/gruppi derivati dal catalogo; `violazioni()` pura; 3 test
- `backend/seed_data/seed-domande.json` - 7 opzioni `tipo_pavimento`, A.6 intera governata, gres a pavimento deduplicato con quota bagno
- `backend/tests/fixtures/famiglie_alternative_pro.json` - famiglie estese (fornitura_pavimento_laminato/vinilico/moquette, sottofondo_laminato, posa_battiscopa_A6, levigatura_A6, posa_rivestimento_A6, fornitura_pavimento_gres)
- `docs/taratura/09-taratura-pro-compilato.xlsx`, `docs/taratura/09-taratura-pro.xlsx` - foglio `assi_proposti` rigenerato via `--aggiorna-assi`
- `backend/tests/test_dettaglio_pro_alternative.py` - invariante bersagli condivisi, combinazioni dal catalogo, 2 nuovi test
- `backend/tests/test_seed_domande_pro.py` - 7 opzioni, posa condivisa A.6.2, nessun fattore su A.6.1 per moquette
- `backend/tests/test_effetti_pro.py` - voce sintetica scratch spostata da A.6.9 (ora governata) ad A.6.11
- `backend/tests/test_dettaglio_pro_livelli.py` (deviazione, fuori dai `files_modified` del piano) - `bersagli_finitura` scoped a GRES, insieme "governate" di A.6 aggiornato

## Decisions Made

- Vedi `key-decisions` in frontmatter: ricostruzione mirata di `voce.livello` nel dev.db del worktree, limitata alle 21 voci GRES (non alle 11 RUBINETTERIE/PORTE/PRODOTTI gia' coperte dalla regola famiglie-per-fascia-di-prezzo).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug ambientale] `--aggiorna-assi` su un dev.db "fresco" cancella silenziosamente le decisioni finitura storiche**
- **Trovato durante:** Task 2, prima esecuzione di `genera_excel_taratura.py --aggiorna-assi` + `applica_taratura.py --solo-assi`
- **Problema:** `voce.livello` (colonna letta dalla Regola 1 di `proponi_assegnazione` per proporre l'asse `finitura`) non viene mai scritta da `scripts/seed.py` in nessun ambiente — e' vestigiale dalla migrazione 0021 ("asse finitura da voce.livello"), che l'ha letta UNA VOLTA da un DB storico e l'ha trasformata in effetti permanenti in `seed-domande.json`. Un dev.db ricostruito da zero (come nel worktree, via `alembic upgrade head` + `scripts/seed.py`) ha quindi SEMPRE `voce.livello IS NULL`: la Regola 1 non propone piu' nulla per le 32 voci storicamente governate da finitura, `aggiorna_foglio_assi` non trova un rigo nuovo con cui far combaciare le vecchie decisioni accettate ("0 righe vecchie riaggiunte") e le scarta. Il primo tentativo ha prodotto un `seed-domande.json` con GRES intera non governata da finitura (tutte le 21 voci gres/rivestimento diventate "sempre incluse"), rilevato da `test_perimetro_tutte_le_voci_classificate` (le voci risultavano ANCORA non classificate anche dopo il fix, un campanello d'allarme).
- **Fix:** dev.db ricostruito una seconda volta; `voce.livello` ripopolato a mano dalle 21 voci GRES (non le 11 RUBINETTERIE/PORTE/PRODOTTI, gia' coperte da un'altra regola — ripopolarle tutte e 32 ha causato una seconda regressione, un `MultipleResultsFound` in `scripts/seed.py._crea_effetto_se_manca` per doppia proposta sullo stesso bersaglio) leggendo gli `includi` di `finitura` dal `seed-domande.json` COMMITTATO (git HEAD, non quello gia' scritto/rotto). Poi rieseguiti `--aggiorna-assi` e `--solo-assi`: 129 decisioni conservate (108 gres pre-esistenti + 21 ripristinate), 0 duplicati, idempotente.
- **File modificati:** nessun file di prodotto oltre a quelli gia' previsti dal Task 2 (il fix e' stato nello STATO del dev.db locale, mai committato: `backend/dev.db` e' in `.gitignore`)
- **Nota per chi rigenera in futuro:** su un dev.db "vero" (main checkout, mai wipeато) questo problema non si presenta, perche' la colonna porta ancora i valori scritti a suo tempo. Si presenta solo su un dev.db ricostruito da zero — come sara' sempre il caso in un worktree isolato. Documentato qui perche' il prossimo esecutore che rigenera i workbook in un worktree pulito ci sbatta contro altrimenti.

**2. [Rule 1 - Bug, fuori dai file del piano] `test_dettaglio_pro_livelli.py` rotto dalla nuova governance G2 di A.6**
- **Trovato durante:** Task 3, batteria mirata della fase
- **Problema:** `bersagli_finitura[livello][0]` (fixture non scoped a GRES) ora puo' pescare A.6.3/A.6.4 (posa rivestimenti), diventate bersaglio di `finitura` per il G2 di questo piano — tre test confrontavano quella descrizione con l'elenco delle voci di GRES e fallivano. `test_le_voci_non_governate_da_tipo_pavimento_restano` assumeva "A.6.1/.2/.5/.6" come uniche voci governate: con A.6.3/.4/.7/.8/.9/.10 ora governate (da finitura o tipo_pavimento), l'assert falliva su A.6.4 (presente solo con finitura=alto, non col default medio) e su A.6.9 (mai presente, esclusa su tutte le finiture).
- **Fix:** `bersagli_finitura` filtrata a GRES; l'insieme "governate" di A.6 esteso a tutte le voci tranne A.6.11 (l'unica rimasta davvero non governata da alcun asse).
- **File modificati:** `backend/tests/test_dettaglio_pro_livelli.py` (non nei `files_modified` del piano, ma necessario per il `<verify>` della fase)
- **Commit:** `c82e7c2`

### Note (non deviazioni)

- Una fornitura gres ambigua ("Fornitura di pavimentazione/rivestimento in gres porcelanato TIPO: Padana...") non e' classificata da `genera_excel_taratura.py` come "gres a pavimento" (il suo testo contiene sia "pavimentazione" sia "rivestimento", quindi la regola `e_gres_a_pavimento` la esclude) e sopravvive alla deduplica insieme a un'altra fornitura per livello base (2 voci "vive" invece di 1). Non e' un difetto rilevato dal test a mondo aperto (classificata "fornitura_rivestimento" dal testo, gruppo dove il livello 'base' ha comunque al massimo una voce reale per slot) ne' dai test esistenti — e' una nota di qualita' del dato per una futura taratura reale (fuori scope di questo piano, che lavora sulla bozza accettata).

## Issues Encountered

Vedi Deviazioni sopra: due false partenze sul dev.db del worktree hanno richiesto ricostruirlo tre volte (`alembic upgrade head` + `scripts/seed.py`) prima di trovare la sequenza corretta (dev.db pulito -> ripopola `voce.livello` solo per GRES dal seed committato -> `--aggiorna-assi` -> `--solo-assi`).

## User Setup Required

None - nessuna configurazione di servizi esterni richiesta. Nota per il ri-collaudo di Riccardo: le tre nuove opzioni pavimento (Laminato, Vinilico LVT, Moquette) sono visibili nel selettore `tipo_pavimento` con effetti generati dalla bozza accettata, non ancora dalla taratura vera.

## Next Phase Readiness

- G1 e G2 di `09-HUMAN-UAT.md` chiusi a livello di dati e di prova automatica: il computo Pro non somma piu' pavimenti alternativi ne' lavorazioni A.6 alternative, per nessuna delle 21 combinazioni finitura x tipo_pavimento lette dal catalogo, e il controllo sa fallire (dimostrato sul seed di ieri).
- Il gap G3 (percorso di scelta del pavimento poco evidente) e G4 (editor admin) restano aperti in `09-HUMAN-UAT.md` per un piano successivo.
- La migrazione Alembic (0023) che porta queste modifiche sul DB di produzione NON e' stata emessa qui (`--migrazione` non usato, come da istruzione del piano): resta al 09-14.

---
*Phase: 09-configuratore-pro*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: `backend/tests/test_alternative_mondo_aperto.py`
- FOUND: `.planning/phases/09-configuratore-pro/09-10-SUMMARY.md`
- FOUND: commit `5120107`
- FOUND: commit `b459d83`
- FOUND: commit `c82e7c2`
