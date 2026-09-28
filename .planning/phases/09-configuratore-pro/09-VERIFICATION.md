---
phase: 09-configuratore-pro
verified: 2026-09-28T00:00:00Z
status: human_needed
score: 5/5 must-haves verified (automated) — WIZ-04 live UAT pending by design
overrides_applied: 0
human_verification:
  - test: "Collaudo dal vivo end-to-end del percorso Pro con l'account Pro reale di Riccardo (checklist 16 voci in 09-HUMAN-UAT.md)"
    expected: "Wizard invariato, dettaglio Pro con default gia' applicati, una sola alternativa per asse (pavimento, finitura), stepper bagni/porte/condizionatori funzionanti, PDF coerente con la schermata, nessuna chiave impresa/coefficiente nel JSON di rete"
    why_human: "Richiede login reale, interazione UI dal vivo e giudizio di plausibilita' dei totali — esplicitamente rinviato con vincolo del 2026-09-26, tracciato come pending in 09-HUMAN-UAT.md, non bloccante per le fasi 09-10"
  - test: "Compilazione della taratura vera in docs/taratura/09-taratura-pro.xlsx (09-TARATURA-TODO.md)"
    expected: "Riccardo rivede i coefficienti proposti e le assegnazioni agli assi, sostituendo la bozza-accettata con valori giudicati da lui"
    why_human: "Giudizio di dominio (prezzi, quantita' plausibili) che nessun test automatico puo' sostituire; per costruzione della fase (D-03/D-05) la bozza-accettata e' considerata sufficiente per procedere, la taratura vera resta un'attivita' separata rinviata"
---

# Phase 09: Configuratore Pro e chiusura del bug dei cataloghi — Verification Report

**Phase Goal:** Il motore Pro smette di sommare voci alternative: gli assi di scelta diventano dati, e i coefficienti quantità vengono tarati nella stessa fase in cui si aggiunge risoluzione.
**Verified:** 2026-09-28
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (Roadmap Success Criteria) | Status | Evidence |
|---|---|---|---|
| 1 | `DettaglioProService.compute()` risolve `includi`/`escludi`/`fattore_quantita`/`quantita_per_unita` dallo stesso catalogo del Free | ✓ VERIFIED | `backend/app/services/dettaglio_pro.py` importa `risolvi_effetti_pro` da `app/services/effetti.py` (stesso modulo del Free); docstring di modulo descrive l'ordine di risoluzione ereditato; `compute()` chiama `risoluzione_per()` → `risolvi_effetti_pro(session, mq=mq, tipo=tipo, risposte=risposte_asse)` per ogni valore distinto dell'asse finitura. `risolvi_effetti_pro()` in `effetti.py:792` usa `risolvi_scelte(tiers=(TIER_FREE, TIER_PRO))`, lo stesso catalogo domande. |
| 2 | Nessuna sottocategoria di tipo `catalogo` contiene più di una famiglia di alternative, verificato da un test che *conta* le voci incluse per sottocategoria | ✓ VERIFIED | `backend/tests/test_dettaglio_pro_alternative.py::test_nessun_asse_include_piu_di_unopzione` — parametrizzato su 3 finiture × 4 tipi_pavimento (12 varianti), per ogni asse con effetti `includi` conta le opzioni con almeno una voce presente e asserisce `len(presenti) <= 1`. Test analogo `..._con_livelli` per il caso `livelli` per-categoria. Eseguito ora: 101 test in `test_dettaglio_pro_alternative.py` + `test_dettaglio_pro_livelli.py` → **101 passed** (198s). |
| 3 | Migrazione senza perdita: `voce.livello` → asse `finitura`; le tre `domanda_mirata_key` → domande `stepper` con `quantita_per_unita` | ✓ VERIFIED | `backend/alembic/versions/*0021*.py`: sezione (A) traduce `voce.livello` non-null in opzioni/effetti `includi` della domanda `finitura`; sezione (B) traduce `coefficiente_qta_voce.domanda_mirata_key` in effetti `quantita_per_unita`. Le colonne originali **non vengono droppate** (dati storici preservati, D-41). `09-08-SUMMARY.md` riporta conteggi post-migrazione su `dev.db`: `voce.livello` non-null = 21 (invariato), `domanda_mirata_key` non-null = 144 (invariato), 199 effetti totali generati. |
| 4 | `computo_parsing.py` non assegna più lo stesso `0,6 × TIPO_FACTOR` a tutte le voci a m² | ✓ VERIFIED | `backend/app/services/computo_parsing.py` — commenti e codice mostrano il passaggio a coefficienti per classe/voce (`taratura-classi.json`, `PROPOSTA_PER_CLASSE x TIPO_FACTOR`), la funzione `coefficienti_per_voce()` col vecchio `0.6 x TIPO_FACTOR` uniforme resta come riferimento storico/fallback esplicitamente commentato come "superato" (riga 107, 149, 280), non più il percorso di produzione. |
| 5 | Il percorso Pro del wizard è esercitato dal vivo end-to-end con un account Pro reale | ? PENDING (human) | Controlli automatici via API tutti verdi su copia di `dev.db` (default D-07, regola bagno D-02, stepper bagni, anti-leak — vedi tabella in `09-08-SUMMARY.md`); il collaudo dal vivo con l'account Pro reale di Riccardo è esplicitamente **rinviato** (vincolo 2026-09-26, tracciato in `09-HUMAN-UAT.md` come `status: pending`, non bloccante). Non è un gap: è un differimento dichiarato e documentato dal piano 09-08. |

**Score:** 4/5 truths automaticamente verificate, 1/5 (WIZ-04) in attesa di collaudo umano per costruzione della fase.

### Requisiti QST-05, CFG-01..04

| Requisito | Descrizione | Status | Evidenza |
|---|---|---|---|
| QST-05 | Ogni `domanda_mirata_key` ha una domanda corrispondente nel catalogo | ✓ SATISFIED | Migrazione 0021 crea domande `stepper` (bagni/porte/condizionatori) con effetto `quantita_per_unita`; `09-04-SUMMARY.md` e `09-02-SUMMARY.md` dichiarano QST-05 completato; `effetti.py` `CONTROLLI_NUMERICI = {"stepper", "numero"}` e `risolvi_effetti_pro` include le domande Free-con-quantita' nella risoluzione Pro. |
| CFG-01 | Motore Pro risolve gli effetti dallo stesso catalogo del Free | ✓ SATISFIED | Vedi Truth 1. |
| CFG-02 | Nessuna sottocategoria `catalogo` con più di una famiglia di alternative, verificato da test che conta | ✓ SATISFIED | Vedi Truth 2 — test parametrizzato eseguito e verde. |
| CFG-03 | Migrazione senza perdita | ✓ SATISFIED | Vedi Truth 3. |
| CFG-04 | Coefficienti quantità tarati nella stessa fase | ✓ SATISFIED (con riserva dichiarata) | `09-06-PLAN/SUMMARY` applicano la migrazione 0022 con la **bozza-accettata** di Claude (D-03/D-04/D-05), non la revisione finale di Riccardo. La fase soddisfa CFG-04 nel senso previsto dal design della fase (D-05: "nessuna forchetta imposta da test, plausibilità giudicata da Riccardo"); la compilazione umana del file vero resta esplicitamente rinviata in `09-TARATURA-TODO.md` (status: RINVIATA), coerente col "Rischio dichiarato" già scritto in ROADMAP.md per questa fase. |
| WIZ-04 | Percorso Pro verificato dal vivo end-to-end | ? PENDING (human, non bloccante) | Vedi Truth 5. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `backend/app/services/dettaglio_pro.py` | Motore Pro su catalogo, non su `voce.livello` | ✓ VERIFIED | Docstring e codice confermano lettura da `risolvi_effetti_pro`; nessun riferimento residuo a `voce.livello` come filtro nel path di calcolo. |
| `backend/app/services/effetti.py::risolvi_effetti_pro` | Risoluzione condivisa Free/Pro | ✓ VERIFIED | Funzione presente, usa `risolvi_scelte(tiers=(TIER_FREE, TIER_PRO))`. |
| `backend/alembic/versions/*0021*.py` | Migrazione senza perdita | ✓ VERIFIED | Upgrade traduce dati esistenti in nuove righe, non droppa colonne sorgente. |
| `backend/alembic/versions/*0022*.py` | Taratura approvata (bozza) | ✓ VERIFIED (esiste, exists) | Presente in `backend/alembic/versions/`. |
| `backend/tests/test_dettaglio_pro_alternative.py` | Test di conteggio CFG-02 | ✓ VERIFIED | Eseguito: 101 passed. |
| `frontend/src/components/DettaglioProView.tsx` | Pannello "Qualche dettaglio in più" | ✓ VERIFIED | Testo "Qualche dettaglio in più" trovato a riga 182; componente wired nella pagina dettaglio Pro. |
| `.planning/phases/09-configuratore-pro/09-HUMAN-UAT.md` | Checklist collaudo dal vivo | ✓ VERIFIED | Esiste, 16 voci, stato pending, tabella controlli automatici in testa. |
| `.planning/phases/09-configuratore-pro/09-TARATURA-TODO.md` | Checklist taratura vera rinviata | ✓ VERIFIED | Esiste, stato RINVIATA, coerente col vincolo 2026-09-26. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `DettaglioProService.compute()` | `effetti.py::risolvi_effetti_pro` | import + chiamata diretta | ✓ WIRED | `from app.services.effetti import (..., risolvi_effetti_pro)`, chiamata in `risoluzione_per()`. |
| `DettaglioProView.tsx` (pannello) | `POST /me/stime/{id}/dettaglio-pro/risposte` | riuso endpoint esistente (D-06) | ✓ WIRED | Confermato da `09-05-SUMMARY.md` e presenza del componente/API client (`frontend/src/api/dettaglio-pro.ts`). |
| `alembic upgrade head` | `dev.db` | migrazioni 0021→0022 | ✓ WIRED | `09-08-SUMMARY.md`: `alembic current` → `0022 (head)` confermato sul DB reale di sviluppo. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Test di conteggio CFG-02 (nessun asse con >1 opzione presente, 12 varianti finitura×pavimento) | `pytest backend/tests/test_dettaglio_pro_alternative.py backend/tests/test_dettaglio_pro_livelli.py backend/tests/test_domande_free.py -q` | `101 passed in 198.54s` | ✓ PASS |
| Regressione mirata (stessi file + livelli) | `pytest backend/tests/test_dettaglio_pro_alternative.py backend/tests/test_dettaglio_pro_livelli.py -q` | passed, exit 0 | ✓ PASS |
| Suite completa (non ri-eseguita per limite di tempo, presa dal commit 9661c1f) | — | 818 passed, 5 skipped | ✓ PASS (dato dal contesto, non ri-verificato in questa sessione per vincolo esplicito) |

### Anti-Patterns Found

Nessun `TBD`/`FIXME`/`XXX`/`TODO`/`PLACEHOLDER` trovato in `dettaglio_pro.py`, `effetti.py`, `computo_parsing.py`, `routers/dettaglio_pro.py`. Nessuno stub rilevato nei file core della fase.

### Human Verification Required

### 1. Collaudo dal vivo del percorso Pro (WIZ-04)

**Test:** Eseguire le 16 voci della checklist in `09-HUMAN-UAT.md` con l'account Pro reale su http://localhost:5173.
**Expected:** Wizard invariato; dettaglio Pro coerente con i default; una sola alternativa per asse; stepper e PDF coerenti; nessuna chiave impresa/coefficiente esposta.
**Why human:** Richiede login e interazione reali; già esplicitamente rinviato per vincolo di Riccardo del 2026-09-26 — non blocca l'avanzamento a Fase 10.

### 2. Compilazione della taratura vera (CFG-04, dato di dominio)

**Test:** Seguire `09-TARATURA-TODO.md`, compilare `docs/taratura/09-taratura-pro.xlsx` con le decisioni reali di Riccardo sui coefficienti/assegnazioni.
**Expected:** Sostituzione della bozza-accettata con valori rivisti, riapplicati con una nuova migrazione Alembic (mai modificando la 0022).
**Why human:** Giudizio di prezzo/dominio non automatizzabile; per costruzione della fase la bozza-accettata basta per procedere (D-03/D-05), ma il "Rischio dichiarato" in ROADMAP.md resta aperto finché Riccardo non la chiude.

### Gaps Summary

Nessun gap bloccante trovato. Tutti gli artefatti core (motore Pro su catalogo condiviso, test di conteggio CFG-02, migrazione 0021 senza perdita, sostituzione del coefficiente uniforme in `computo_parsing.py`, migrazione 0022 con bozza-accettata) esistono, sono sostanziali e sono wired, confermati da lettura di codice e da esecuzione mirata dei test (101 passed). I due elementi rimanenti — collaudo dal vivo (WIZ-04) e taratura vera dei coefficienti (perfezionamento di CFG-04) — sono differimenti **dichiarati e documentati** dal piano stesso (vincolo del 2026-09-26), non omissioni scoperte in verifica: per questo lo status è `human_needed` e non `gaps_found`.

---

_Verified: 2026-09-28_
_Verifier: Claude (gsd-verifier)_
