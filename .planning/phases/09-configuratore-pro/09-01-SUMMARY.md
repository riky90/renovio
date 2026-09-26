---
phase: 09-configuratore-pro
plan: 01
subsystem: api
tags: [openpyxl, export-excel, import-excel, taratura, coefficienti-pro]

# Dependency graph
requires:
  - phase: 08-export-import-excel
    provides: "export_excel/parametri.py (build_workbook_parametri, foglio coefficienti_pro), import_excel/parametri.py (round-trip, #CANCELLA#, colonne ignorate in lettura)"
provides:
  - "proponi_coefficiente(): bozza ragionata di coefficienti per classe di voce (D-03), separata da coefficienti_per_voce() che resta la bozza uniforme per gli upload futuri"
  - "genera_excel_taratura.py: costruisci_workbook_taratura()/proponi_assegnazione()/leggi_decisioni()/accetta_bozza() — canale di generazione e lettura del file di taratura, riusabile dai piani 09-06/09-07"
  - "docs/taratura/09-taratura-pro.xlsx (D-04, stato da-compilare) e 09-taratura-pro-compilato.xlsx (stato bozza-accettata) come deliverable reale per Riccardo e input non bloccante per la fase"
  - "09-TARATURA-TODO.md: checklist rinviata + comando ripetibile di riapplicazione (scripts/applica_taratura.py, piano 09-06)"
affects: [09-02, 09-03, 09-06, 09-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Generatore Excel one-off che riusa build_workbook_parametri() e aggiunge colonne extra al foglio esistente, mai un formato ad-hoc (Pitfall 3 09-RESEARCH.md): le colonne di curatela sono ignorate in lettura da import_excel senza toccarne COLONNE_COEFF_PRO"
    - "Bozza-accettata come stato esplicito e distinto ('bozza-accettata' vs 'compilato'), letto da leggi_decisioni() e riportato ai piani successivi, per non confondere una proposta non rivista con una taratura vera (T-09-03b)"
    - "Classificazione per classe di voce (parole chiave + UM) come funzione pura, separata dalla scrittura del file: testabile senza DB, riusata identica dal generatore"

key-files:
  created:
    - backend/scripts/genera_excel_taratura.py
    - docs/taratura/09-taratura-pro.xlsx
    - docs/taratura/09-taratura-pro-compilato.xlsx
    - .planning/phases/09-configuratore-pro/09-TARATURA-TODO.md
  modified:
    - backend/app/services/computo_parsing.py
    - backend/tests/test_taratura_pro.py

decisions:
  - "Classificazione delle voci basata SOLO su descrizione (non su descrizione+nome sottocategoria come da testo letterale del piano): il nome di A.6 ('PAVIMENTI E RIVESTIMENTI') avrebbe classificato erroneamente le sue pose di pavimento come rivestimento"
  - "Per le voci con domanda_mirata_key valorizzata, il coefficiente proposto nel file di taratura resta identico a quello a DB (nessuna modifica), con motivazione che spiega che la quantita' vera viene dallo stepper omonimo — coerente col round-trip a scarti zero"
  - "Famiglie di alternative (sanitari, porte, condizionatori) assegnate a base/medio/alto per fascia di prezzo cliente, criterio esplicito e riproducibile in assenza di un giudizio qualitativo di Riccardo"

metrics:
  duration: "~70min"
  completed: "2026-09-26"
---

# Phase 09 Plan 01: Excel di taratura Pro (D-03/D-04/D-08) Summary

Genera il file Excel di taratura dei coefficienti Pro con bozza ragionata per classe di voce
(D-03) e assegnazione proposta alle voci agli assi finitura/tipo_pavimento/stepper (D-08),
produce il deliverable reale per Riccardo e, accanto, una bozza accettata che alimenta i piani
successivi senza bloccare la fase sulla sua compilazione.

## What Was Built

**Task 1 — `proponi_coefficiente()` in `computo_parsing.py`.** Classifica ogni voce del computo
in una di dieci classi (pavimento, rivestimento, battiscopa, massetto, pareti_soffitti,
demolizione, serramento_mq, lineare, altro_mq, conteggio, percentuale) per UM + parole chiave
sulla descrizione, e propone un coefficiente motivato per il tipo `totale` (bozza di Claude in
`PROPOSTA_PER_CLASSE`), scalato per `leggera`/`moderata` con lo stesso `TIPO_FACTOR` esistente.
`coefficienti_per_voce()` resta invariata bit-per-bit (Pitfall 4 del RESEARCH: e' ancora la bozza
usata dagli upload futuri finche' Riccardo non valida la taratura nel piano 09-06). 11 test TDD
(RED→GREEN) coprono classificazione, crescita monotona per tipo, motivazioni non vuote e
anti-leak.

**Task 2 — `backend/scripts/genera_excel_taratura.py`.** `costruisci_workbook_taratura(db)`
riparte da `build_workbook_parametri(db, con_margine=False)` (stessi cinque fogli, stesso
`ISTRUZIONI` con timestamp) e:
- estende `coefficienti_pro` con 12 colonne di curatela (`categoria_code`, `sottocategoria`,
  `codice_voce`, `um`, `prezzo_unitario_cliente`, `coefficiente_attuale`,
  `default_conteggio_attuale`, `coefficiente_proposto`, `default_conteggio_proposto`,
  `motivazione`, `decisione`, `note`), senza toccare `COLONNE_COEFF_PRO` di `import_excel` — le
  colonne extra sono ignorate in lettura per costruzione;
- scrive `assi_proposti` (`proponi_assegnazione()`, funzione pura): livello curato →
  finitura, A.6.1/A.6.2/A.6.5/A.6.6 → tipo_pavimento (+ righe `fattore_pavimento` su A.6.1 per
  D-02), sottocategoria PAVIMENTI PARQUET / tesserine-mosaico / lastre di bassissimo spessore /
  battiscopa legno-gres → tipo_pavimento, voci con `domanda_mirata_key` → stepper omonimo, 6
  famiglie di alternative (vaso, bidet, cassetta, doccia/vasca, porte, condizionatori) → finitura
  base/medio/alto per fascia di prezzo con eccedenze `escludi_sempre`, il resto → `sempre_inclusa`;
- scrive `dati_richiesti` (15 dati, uno per ogni coefficiente/regola non deducibile dal computo)
  e `LEGGIMI_TARATURA` con lo stato (`da-compilare`/`bozza-accettata`/`compilato`).

`leggi_decisioni(wb)` interpreta `OK`/`ATTUALE`/`MODIFICATO`/`NO` e solleva `ValueError` su un
valore non riconosciuto o su uno stato fuori dall'insieme chiuso. `accetta_bozza(wb)` produce
una copia con ogni riga a `decisione="OK"`, `dati_richiesti.valore_riccardo` = proposto, e stato
`bozza-accettata` con una riga `avviso` esplicita — mai confondibile con una validazione vera.
15 test TDD coprono fogli presenti, coerenza righe/DB, round-trip a zero scarti sull'handler
`parametri` reale, anti-leak su ogni cella di ogni foglio, le tre decisioni, gli errori, e
`accetta_bozza()`.

**Task 3 — generazione reale su `dev.db`.** Lanciato in sola lettura (verificato:
`effetto_opzione` 68 righe prima e dopo). Risultati: `coefficienti_pro` 573 righe (=
`coefficiente_qta_voce` a DB), `assi_proposti` 133 righe (37 finitura, 26+11+11 stepper
bagni/porte/condizionatori, 17 tipo_pavimento, 10 escludi_sempre, 18 sempre_inclusa, 3
fattore_pavimento), `dati_richiesti` 15 righe. `09-taratura-pro.xlsx` stato `da-compilare`;
`09-taratura-pro-compilato.xlsx` stato `bozza-accettata`, `leggi_decisioni()` senza errori.
`09-TARATURA-TODO.md` (checklist rinviata, 9 voci con `Note:`) registra la validazione vera come
lavoro non cancellato, con il comando di riapplicazione del piano 09-06.

Cinque motivazioni rappresentative (tipo `totale`):
- A.0.1 (allestimento cantiere, cad): "Voce a conteggio (UM cad/ac/n.*): nessun coefficiente per
  m2 possibile, proposto un default_conteggio di partenza da confermare con Riccardo."
- A.1.1.1 (demolizione muratura, mq): "Quota dei m2 dell'appartamento soggetta a
  demolizione/rimozione, scalata per intensita' di intervento."
- A.2.1 (massetto, mq): "Quota dei m2 dell'appartamento su cui si rifa' il massetto, scalata per
  intensita' di intervento."
- A.4.1 (intonaci, mq): "Superficie di pareti e soffitto per m2 di pavimento (altezza media
  locale x perimetro, piu' il soffitto), coefficiente maggiore di 1 per costruzione."
- Rivestimenti bagno (A.6.3/A.6.4): "Coefficiente di fallback quando manca il numero di bagni
  della stima: circa 20 m2 di parete rivestita per bagno su un appartamento di riferimento di 85
  m2 (D-03)."

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Classificazione basata solo su descrizione, non su descrizione+nome sottocategoria**
- **Found during:** Task 1, primo test RED→GREEN
- **Issue:** il testo letterale dell'azione ("parole chiave su descrizione e nome
  sottocategoria") avrebbe classificato ogni voce di A.6 ("PAVIMENTI E RIVESTIMENTI") come
  `rivestimento` per il solo fatto che il nome della sottocategoria contiene "rivestiment" —
  anche A.6.1 (posa della pavimentazione), il caso esplicitamente citato nel `<behavior>` del
  piano come dover restare `pavimento`.
- **Fix:** la classificazione usa solo `descrizione.lower()`; `sottocategoria_nome` resta nella
  firma della funzione (per compatibilita' e uso futuro) ma non alimenta il testo classificato.
- **Files modified:** `backend/app/services/computo_parsing.py`
- **Commit:** `4ab0826`

**2. [Rule 1 - Bug] Testo del foglio LEGGIMI_TARATURA riformulato per non contenere "coefficiente_impresa"/"AVVISO"**
- **Found during:** Task 2, test anti-leak
- **Issue:** la prima stesura del testo di istruzioni citava letteralmente "nessuna colonna
  coefficiente_impresa" per spiegare l'assenza del dato — violando il criterio meccanico
  `grep`/scansione-celle usato dal test anti-leak (stesso precedente delle fasi 02/03/08: mai la
  stringa letterale, anche in un commento/testo che la NEGA).
- **Fix:** riformulato in "nessuna colonna di margine, nessun foglio dedicato all'avviso di
  riservatezza".
- **Files modified:** `backend/scripts/genera_excel_taratura.py`
- **Commit:** `bead415`

**3. [Rule 1 - Bug] Test sulle "21 voci gres livellate" riscritto per curare la fixture**
- **Found during:** Task 2, test `assi_proposti`
- **Issue:** l'affermazione di CONTEXT ("21 voci con `voce.livello` valorizzato") descrive lo
  stato curato di `backend/dev.db`, non il seed idempotente (`scripts/seed.py` + `docs/
  seed-dettaglio-pro.json`) usato dalla fixture in-memory dei test — coerente con STATE.md
  ("la curatela di `voce.livello` esiste solo nel dev.db locale"). Il test come scritto
  inizialmente falliva sempre (0 righe), non per un bug del generatore.
- **Fix:** il test cura esplicitamente 3 voci nella fixture prima di generare il workbook, e
  verifica che `proponi_assegnazione()` proponga l'asse finitura esattamente su quelle. La
  verifica delle vere 21 voci gres di `dev.db` e' fatta nel Task 3, contro il database reale
  (573 righe coefficienti_pro, 133 righe assi_proposti coerenti).
- **Files modified:** `backend/tests/test_taratura_pro.py`
- **Commit:** `bead415`

## Known Stubs

Nessuno che impedisca l'obiettivo del piano. Le assegnazioni proposte in `assi_proposti` (in
particolare le famiglie di alternative per fascia di prezzo) sono bozze esplicitamente marcate
"da confermare con Riccardo" — e' il comportamento dichiarato del piano (D-08), non uno stub non
documentato: la validazione vera e' registrata come lavoro rinviato in `09-TARATURA-TODO.md`.

## Self-Check: PASSED

- `backend/app/services/computo_parsing.py` — FOUND
- `backend/scripts/genera_excel_taratura.py` — FOUND
- `backend/tests/test_taratura_pro.py` — FOUND
- `docs/taratura/09-taratura-pro.xlsx` — FOUND
- `docs/taratura/09-taratura-pro-compilato.xlsx` — FOUND
- `.planning/phases/09-configuratore-pro/09-TARATURA-TODO.md` — FOUND
- commit `4ab0826` — FOUND
- commit `bead415` — FOUND
- commit `c0f2403` — FOUND
