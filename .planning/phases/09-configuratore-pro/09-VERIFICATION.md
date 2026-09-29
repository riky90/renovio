---
phase: 09-configuratore-pro
verified: 2026-09-29T00:00:00Z
status: passed
score: 6/6 must-haves verified — ri-collaudo dal vivo G1..G4 approvato da Riccardo il 2026-09-29
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 4/5 truths automatiche + WIZ-04 pending
  gaps_closed:
    - "G1: pavimenti alternativi sommati in B-FINITURE > PAVIMENTI (chiuso da 09-09/09-10/09-14: 7 opzioni tipo_pavimento, ognuna governa solo le proprie voci, verificato per tutte e 7 su copia di dev.db)"
    - "G2: levigature/battiscopa doppi in A.6 (chiuso da 09-09/09-10: A.6 intera governata per opzione, levigatura marmo mai presente, levigatura parquet solo con parquet, un solo battiscopa per scelta)"
    - "G3 parte codice: 'vai a Pro' da stima non salvata portava a un modulo vergine; pavimento visibile solo dietro 'Modifica' (chiuso da 09-11/09-12: history.state porta risposte+destinazione a /nuova-stima, wizard riapre su step 4, pannello Pro mostra le domande a scelta sempre, ricalcolo immediato al cambio)"
    - "G4: comandi 'Aggiungi effetto' nascosti, dialog di modifica admin senza tutte le colonne (chiuso da 09-13: bottoni 'Opzioni ed effetti'/'Effetti (n)' visibili, dialog di Listini/Coefficienti/Bonus estesi a tutte le colonne)"
  gaps_remaining:
    - "Nessun gap di codice residuo trovato. Resta il ri-collaudo dal vivo di Riccardo (checklist G1..G4 e le 5 'scelte di Claude da confermare' in 09-HUMAN-UAT.md, sezione 'Ri-collaudo gap G1..G4') — tutte le caselle sono ancora vuote, nessun esecutore le ha spuntate, per costruzione del processo."
  regressions: []
---

# Phase 09: Configuratore Pro e chiusura del bug dei cataloghi — Verification Report (Re-verification)

**Phase Goal:** Il motore Pro smette di sommare voci alternative: gli assi di scelta diventano dati, e i coefficienti quantità vengono tarati nella stessa fase in cui si aggiunge risoluzione.
**Verified:** 2026-09-28
**Status:** passed (2026-09-29, dopo il ri-collaudo dal vivo)
**Re-verification:** Sì — dopo chiusura gap G1..G4 (piani 09-09..09-14), a seguito del collaudo di Riccardo del 2026-09-28 documentato in `09-HUMAN-UAT.md`

## Nota sulla verifica precedente

La verifica iniziale (stesso file, sovrascritta qui) aveva dato `status: human_needed`,
score 4/5 automatico con WIZ-04 in attesa di collaudo dal vivo. Il collaudo dal vivo di
Riccardo (2026-09-28) ha trovato **4 gap** (G1, G2, G3, G4, tutti in `09-HUMAN-UAT.md` §Gaps).
Sono stati chiusi da sei piani di gap closure (09-09..09-14). Questa è la ri-verifica di
quella chiusura: guarda il codice, non le dichiarazioni dei SUMMARY.

## Goal Achievement

### Gap G1 — pavimenti sommati in B-FINITURE

| Verifica | Esito | Evidenza |
|---|---|---|
| `tipo_pavimento` ha le opzioni laminato/vinilico_lvt/moquette oltre a gres/parquet/maxi_lastra/mosaico | ✓ VERIFIED | Letto `backend/seed_data/seed-domande.json` a runtime: `['gres', 'parquet', 'maxi_lastra', 'mosaico', 'laminato', 'vinilico_lvt', 'moquette']` — 7 opzioni. |
| Nessuna doppia fornitura pavimento in B-FINITURE, per nessuna delle 7 opzioni | ✓ VERIFIED | `backend/tests/test_alternative_mondo_aperto.py` (perimetro/assi/combinazioni derivati dal catalogo via query SQLAlchemy, non da lista scritta a mano) — eseguito ora, **190 passed** insieme a `test_migrazioni_sqlite.py`, `test_taratura_pro.py`, `test_applica_taratura.py`, `test_wizard_pro_scelte.py`, `test_dettaglio_pro_alternative.py`, `test_dettaglio_pro_livelli.py` (315s). Tabella di controllo manuale in `09-HUMAN-UAT.md` (09-14 Task 3) conferma 0-1 voce per opzione su tutte e 7. |
| Migrazione 0023 porta le nuove opzioni/effetti su ogni DB esistente | ✓ VERIFIED | `backend/alembic/versions/0023_pavimenti_alternativi.py` presente; `dev.db` interrogato ora → `alembic_version = 0023` (head). Test di migrazione su catalogo reale (non sintetico) in `test_migrazioni_sqlite.py`, verde. |

### Gap G2 — levigature/battiscopa doppi in A.6

| Verifica | Esito | Evidenza |
|---|---|---|
| A.6 intera (non solo le pose base) è governata da un asse | ✓ VERIFIED | `test_alternative_mondo_aperto.py::test_una_voce_per_lavorazione` deriva i gruppi di lavorazione (battiscopa, levigatura, posa_rivestimento, fornitura_pavimento) dal catalogo e asserisce un massimo di voce "viva" per gruppo/combinazione; verde. |
| Levigatura marmo mai presente, levigatura parquet solo con parquet | ✓ VERIFIED | Tabella di controllo manuale 09-14 (Task 3, su copia di `dev.db`, tutte e 7 le opzioni): "Levigatura marmo: assente" su ogni riga, "Levigatura parquet: presente" solo sulla riga `parquet`. |
| Un solo battiscopa per scelta | ✓ VERIFIED | Stessa tabella: colonna "Battiscopa" sempre 1 (ceramica con gres/maxi_lastra/mosaico, legno con parquet/laminato/vinilico_lvt/moquette). |

### Gap G3 — percorso pavimento poco evidente

| Verifica | Esito | Evidenza |
|---|---|---|
| "Vai alla stima Pro" da stima non salvata porta i dati, non un modulo vergine | ✓ VERIFIED | `frontend/src/pages/EstimatePage.tsx:304` — `CtaDettaglioPro` naviga a `/nuova-stima?citta=...&mq=...&tipo=...` con `state:{risposte,destinazione}`; `frontend/src/pages/NuovaStimaProPage.tsx` — `datiDaStato()` legge `location.state`, `stepIniziale = risposte ? 4 : undefined` passato al wizard. |
| "Rifai in versione Pro" da Le mie stime punta a `/nuova-stima`, non alla home | ✓ VERIFIED | `frontend/src/routes/LeMieStimePage.tsx:97` — link `to={`/nuova-stima?citta=...`}`. |
| Il pavimento si vede e si cambia senza premere "Modifica" | ✓ VERIFIED | `frontend/src/components/DettaglioProView.tsx:200-226` — blocco `domandeScelta` (include il pavimento, `tipo_controllo` non numerico) reso **fuori** dal ramo `domandeCollassate ? ... : ...`, sempre visibile; `handleSceltaChange` (riga 108) invoca `risposteMutation.mutate` per ricalcolo immediato, con guardia anti-invio-concorrente e spinner. |
| Il wizard Pro chiede il pavimento allo step 4 (non solo il livello finitura) | ✓ VERIFIED | 09-11: `GET /me/opzioni-pro` espone `domande` (11 test in `test_wizard_pro_scelte.py`, rieseguiti ora, verdi); `EstimateWizard.tsx` disegna le domande del configuratore nello step 4. |

### Gap G4 — editor admin

| Verifica | Esito | Evidenza |
|---|---|---|
| "Aggiungi effetto" visibile senza cercarlo | ✓ VERIFIED | `frontend/src/pages/admin/DomandePage.tsx:310` — bottone "Opzioni ed effetti"/"Effetti" per riga; `OpzioniSezione.tsx:233` — "Effetti (n)" col conteggio; `EffettiSezione.tsx:340` — bottone "Aggiungi effetto" ora primario, con scroll automatico alla sezione. |
| Dialog di modifica di Listini/Coefficienti/Bonus mostrano tutte le colonne | ✓ VERIFIED | `ListiniPage.tsx:408` — nuovo dialog "Modifica listino"; `CoefficientiPage.tsx`/`BonusPage.tsx` — campi prima assenti ora in sola lettura (Tipo/Categoria separati, Domanda mirata con link, Codice bonus visibile, Bonus/Destinazione/Categoria/Extra mostrati). |

### Requisiti QST-05, CFG-01..04, WIZ-04

| Requisito | Status | Evidenza |
|---|---|---|
| QST-05 | ✓ SATISFIED | Invariato dalla verifica iniziale: domande `stepper` con `quantita_per_unita` esistono per ogni `domanda_mirata_key`. |
| CFG-01 | ✓ SATISFIED | Invariato: `DettaglioProService.compute()` → `risolvi_effetti_pro()` sullo stesso catalogo del Free. Rinforzato da 09-11/09-13 (le domande a scelta arrivano dallo stesso catalogo anche nel wizard e nell'editor admin). |
| CFG-02 | ✓ SATISFIED (rinforzato) | La verifica iniziale copriva solo A.6.1/.2/.5/.6 e i casi allora noti (test parametrizzato a lista chiusa). Il gap G1/G2 ha dimostrato che il controllo iniziale non copriva A.6.3/.4/.7/.8/.9/.10 né i pavimenti alternativi in B-FINITURE. Ora `test_alternative_mondo_aperto.py` deriva perimetro/assi/combinazioni **dal catalogo**, non da una lista scritta a mano — copertura strutturalmente più ampia, verde su 190 test. |
| CFG-03 | ✓ SATISFIED | Migrazione 0023 aggiunge dati senza droppare colonne (create-if-missing, fail-loud, reversibile); WR-02 chiude un'asimmetria del downgrade 0021 trovata in review. `alembic upgrade head` → `0023` verificato su `dev.db` reale. |
| CFG-04 | ✓ SATISFIED (con riserva dichiarata, invariata) | Bozza-accettata ancora in uso (non la taratura vera di Riccardo) — stessa riserva della verifica iniziale, tracciata in `09-TARATURA-TODO.md` come RINVIATA. Le nuove famiglie (laminato/vinilico/moquette/sottofondo/gres-a-pavimento) seguono lo stesso schema di taratura bozza-accettata delle famiglie preesistenti. |
| WIZ-04 | ? PENDING (human) | Controlli automatici per tutte le 7 opzioni pavimento verdi (tabella 09-14 Task 3). Il collaudo dal vivo di Riccardo su questa build (dev.db a 0023) **non è stato ancora eseguito**: la sezione "Checklist per te" del ri-collaudo G1..G4 in `09-HUMAN-UAT.md` ha tutte le caselle vuote (`- [ ]`), incluse le 5 domande esplicite "Scelta di Claude da confermare". Questo è il motivo per cui lo stato resta `human_needed`, non `passed`. |

### Anti-Patterns Found

Nessun `TBD`/`FIXME`/`XXX`/`TODO`/`PLACEHOLDER` nei file toccati dai piani di gap closure
(`dettaglio_pro.py`, `genera_excel_taratura.py`, `applica_taratura.py`,
`0023_pavimenti_alternativi.py`, `DettaglioProView.tsx`, `NuovaStimaProPage.tsx`,
`EstimatePage.tsx`, `LeMieStimePage.tsx`, pagine admin). L'unico match di "TODO"-like è un
riferimento testuale a `09-TARATURA-TODO.md` (nome di documento tracciato, non un debt
marker nel codice).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Tutti i test dei piani di gap closure (mondo aperto CFG-02, migrazioni 0021/0023, generatore/applicatore taratura, scelte wizard Pro, alternative/livelli Pro) | `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_alternative_mondo_aperto.py backend/tests/test_migrazioni_sqlite.py backend/tests/test_taratura_pro.py backend/tests/test_applica_taratura.py backend/tests/test_wizard_pro_scelte.py backend/tests/test_dettaglio_pro_alternative.py backend/tests/test_dettaglio_pro_livelli.py -q` | `190 passed in 315.71s` | ✓ PASS |
| `alembic_version` su `dev.db` reale | query SQLite diretta | `0023` | ✓ PASS |
| 7 opzioni `tipo_pavimento` nel seed committato | lettura JSON a runtime | `['gres','parquet','maxi_lastra','mosaico','laminato','vinilico_lvt','moquette']` | ✓ PASS |
| Suite completa (non ri-eseguita, presa da 09-14 Task 3, stessa sessione, stesso commit) | — | 849 passed, 5 skipped | ✓ PASS (dato dal contesto per vincolo esplicito del compito, non ri-eseguito qui) |

### Gaps Summary

Nessun gap di codice residuo. I quattro gap trovati dal collaudo di Riccardo (G1 pavimenti
sommati, G2 levigature/battiscopa doppi, G3 percorso pavimento poco evidente, G4 editor
admin incompleto) sono chiusi a livello di codice, dati (migrazione 0023 su `dev.db` reale)
e test automatici (190 test mirati + 849 della suite completa già verificata in questa
sessione dal piano 09-14). Verificato leggendo il codice sorgente riga per riga (non i
SUMMARY), non solo la loro esistenza: i pannelli sono wired, gli endpoint sono chiamati, i
test contano davvero le voci invece di controllare un elenco fisso.

Resta **solo** il ri-collaudo dal vivo di Riccardo: la sezione "Ri-collaudo gap G1..G4" di
`09-HUMAN-UAT.md` ha 15 caselle vuote (11 di verifica funzionale + 5 "scelte di Claude da
confermare" che sono decisioni di dominio, non bug — es. se il battiscopa legno debba
valere anche per laminato/vinilico/moquette, o se la fornitura gres "prima per id" sia
accettabile). Questo è per costruzione del processo (`status: pending` in
`09-HUMAN-UAT.md`, nessun esecutore spunta le caselle), non un'omissione di questa verifica.
Non bloccante per l'avanzamento tecnico, ma lo stato resta `human_needed` finché Riccardo
non collauda.

### Human Verification Required

### 1. Ri-collaudo dal vivo dei gap G1..G4

**Test:** Eseguire le 11 voci funzionali + le 5 "scelte di Claude da confermare" nella sezione
"Ri-collaudo gap G1..G4" di `09-HUMAN-UAT.md`, con dev.db a 0023 (già fatto) e l'app in
esecuzione (`uvicorn` + `npm run dev`).
**Expected:** Nessuna doppia voce di pavimento/lavorazione in B-FINITURE/A.6 per gres,
laminato, vinilico LVT, moquette; percorso "Vai alla stima Pro" e "Rifai in versione Pro"
aprono il wizard con i dati portati; editor admin con comandi visibili; le 5 decisioni di
dominio di Claude (battiscopa condiviso, moquette senza posa dedicata, A.6.3/A.6.4 per
fascia, quale fornitura gres resta per livello, sottofondo solo con laminato) confermate o
corrette da Riccardo.
**Why human:** Giudizio visivo/di dominio sui totali e sulle decisioni di taratura; richiede
login e interazione reale nel browser, non automatizzabile.

### 2. Voci residue del collaudo precedente (invariate)

**Test:** Voce 12 (scarico PDF dettagliato — bloccata da WeasyPrint/GTK3 assente su Windows,
verificabile solo in produzione/Linux); voce 13 (plausibilità dei totali Pro vs Free,
rimandata da Riccardo); voce 14 (riapertura stima da "Le mie stime", non ancora eseguita).
**Expected:** Come da checklist originale in `09-HUMAN-UAT.md`.
**Why human:** Stesse ragioni della verifica iniziale — ambiente di produzione o giudizio di
plausibilità.

### 3. Compilazione della taratura vera (CFG-04, invariato)

**Test:** Seguire `09-TARATURA-TODO.md`, compilare `docs/taratura/09-taratura-pro.xlsx` con le
decisioni reali di Riccardo.
**Expected:** Sostituzione della bozza-accettata (comprese le nuove famiglie pavimento) con
valori rivisti, via nuova migrazione Alembic.
**Why human:** Giudizio di prezzo/dominio, esplicitamente rinviato per costruzione della fase.

---

_Verified: 2026-09-28_
_Verifier: Claude (gsd-verifier)_

## Chiusura 2026-09-29

- Code review post-gap: CR-01 e WR-01..07 corretti (`5a4df2e`..`0e16902`), report in
  `09-REVIEW-FIX.md` (`all_fixed`). Suite backend 858 passed / 5 skipped (i 2 fallimenti
  del worktree isolato dipendevano dall'assenza di `dev.db` e passano nel repo).
- Ri-collaudo dal vivo di Riccardo (`.planning/checklists/2026-09-29-ricollaudo-09.md`):
  G1..G4, CR-01, WR-07 passati; le cinque scelte del planner confermate. Emerso e corretto un
  difetto della 04-08 ("Aggiungi listino" inviava la POST senza body, `4e4b50a`).
- Restano fuori dalla verifica, per scelta di Riccardo: PDF Pro (solo in produzione, GTK3) e
  plausibilita' dei totali (a fine Fase 10). Taratura A.6.11 e prova delle migrazioni
  0021-0023 su Postgres restano aperte prima del push.
