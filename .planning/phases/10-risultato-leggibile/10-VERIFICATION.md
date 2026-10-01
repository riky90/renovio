---
phase: 10-risultato-leggibile
verified: 2026-10-01T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "PDF Free: scaricare il PDF di una stima Free con budget superato (Render, WeasyPrint attivo)"
    expected: "Barra proporzionale con cifre ai bordi (G13), tacca 'Il tuo budget', riepilogo imponibile/IVA per aliquota/extra/totale, €/m² e peso per categoria, riquadro avviso con confronto a finiture inferiori e nota 'Il budget non cambia il prezzo della stima.', Bonus Mobili nel blocco Arredo. Nessun prezzo impresa o coefficiente."
    why_human: "Rendering WeasyPrint non eseguibile su questa macchina Windows (GTK3 assente); differito al go-live su Render per decisione dell'utente."
  - test: "PDF Pro: scaricare il PDF di una stima Pro con budget (Render)"
    expected: "Totale IVA esclusa in testa, blocco 'Totale IVA inclusa' con barra proporzionale e tacca, riepilogo per aliquota, €/m² e peso per categoria, riquadro avviso budget. Nessun prezzo impresa o coefficiente."
    why_human: "Stesso motivo: rendering PDF reale solo su Render."
---

# Phase 10: Risultato leggibile e tetto di budget — Verification Report

**Phase Goal:** Il numero smette di essere un numero: si legge da dove viene, quanto pesa ogni categoria, quanto è davvero incerto — e cosa fare se supera il budget dichiarato.
**Verified:** 2026-10-01
**Status:** human_needed (solo verifiche visive PDF differite al go-live)
**Re-verification:** No — verifica iniziale

> Nota MVP: la fase è marcata `mode: mvp` ma il goal non è nel formato User Story
> (`gsd-sdk query user-story.validate` → `valid: false`). Su richiesta dell'orchestratore la
> verifica procede contro i 5 Success Criteria della ROADMAP, che sono il contratto. Nessun
> impatto sull'esito; da sistemare eventualmente nel formato del goal.

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP SC) | Status | Evidence |
|---|---|---|---|
| 1 | `RangeBar` proporzionale ai valori reali (non più 12%/88% fissi) | ✓ VERIFIED | `frontend/src/components/RangeBar.tsx` usa `scalaBarra(min, max, budget)` da `lib/risultato.ts`: asse 0→tetto (1,2×max arrotondato a 1.000/5.000), `leftPct = min/tetto`, `rightPct = max/tetto`, larghezza minima 4%. Nessuna traccia di 12%/88%. Mirror Python `services/risultato.py::scala_barra` usato da `pdf_service.py` (righe 186, 223) e dai template `pdf_stima.html`/`pdf_stima_pro.html` (`barra.left_pct`, `barra.width_pct`). Usata in TotalCard (Free), DettaglioProView (Pro), BonusPanel. |
| 2 | Ogni `CategoryCard` mostra incidenza €/m² e peso relativo | ✓ VERIFIED | `CategoryCard.tsx` calcola `incidenzaEurMq(imponibile_min, imponibile_max, mq)` e `pesoCategoria(categoria, sommaMedi)` e li rende via `LetturaCategoria` (€/m² IVA esclusa + mini-barra "N% del totale"). `EstimatePage.tsx:483` e `SavedEstimateDetail.tsx:82` passano `mq` e `sommaMedi` reali. Pro: `lettura_categorie` nel DTO (`schemas/dettaglio_pro.py::LetturaCategoriaOut`) resa da `SottocategoriaAccordion` → `LetturaCategoria`. PDF Free righe 425-426, PDF Pro righe 514-522. |
| 3 | Il riepilogo espone imponibile, IVA ed extra | ✓ VERIFIED | `TotalCard.tsx` → `riepilogoIva(categorie, extra, totale)` → `RiepilogoIvaRighe` (imponibile lavori, righe IVA per aliquota che riconciliano con `totale.iva_*`, extra, totale). Pro: `RiepilogoIvaOut` server-side mappato in `routers/dettaglio_pro.py::_to_out` e reso in `DettaglioProView.tsx:421`. PDF Free righe 468-497 (`riepilogo-iva` con extra e `extra_totale`), PDF Pro idem. |
| 4 | Superato il budget, avviso con confronto ricalcolato a finiture inferiori | ✓ VERIFIED | Server: `routers/stima.py::_confronto_finiture` richiama davvero `EstimationService.compute` con `livello_finiture` un gradino sotto e restituisce `ConfrontoFinitureOut` solo se abbassa il massimo; Pro: `confronto_finiture` nel `DettaglioProOut`. Client: `BudgetAlert.tsx` a tre stati (`statoBudget`: fuori/limite/dentro), nello stato "fuori" mostra "Con finiture {livello} … circa {delta} in meno" o il testo "finiture economiche" se al minimo. Montato in `EstimatePage.tsx:472`, `SavedEstimateDetail.tsx:68`, `DettaglioProView.tsx:429`. PDF: `avviso_budget()` in `services/risultato.py` → riquadro `avviso-budget` nei due template. Budget persistito in colonna (`0024_budget_eur_su_stima.py`, `models/stima_salvata.py:67`), `PATCH /me/stime/{id}/budget`. Test: `test_confronto_finiture.py`, `test_dettaglio_pro_budget.py`, `test_budget_stima.py` passano. |
| 5 | Il budget non muove il prezzo (finiture sì, budget no) | ✓ VERIFIED | `StimaRequest` non ha alcun campo budget: il motore non può riceverlo. Budget solo nella colonna `stima.budget_eur`, escluso dallo snapshot (`routers/stime_salvate.py:68` `exclude={"preferenze_pro","budget_eur"}`). `PATCH …/budget` (righe 265-285) aggiorna solo la colonna senza chiamare motori. Pro: `budget_eur` passato a `_to_out` solo come eco, il calcolo non lo usa. Il confronto cambia solo `livello_finiture`. Test `test_patch_aggiorna_solo_la_colonna`, `test_get_post_stessi_campi_e_patch_invariante` passano. Nota UI "Il budget non cambia il prezzo della stima." presente in web e PDF. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `frontend/src/lib/risultato.ts` | Funzioni pure barra/€/m²/peso/riepilogo/budget | ✓ VERIFIED | Sostanziale, importato da RangeBar, CategoryCard, TotalCard, BudgetAlert |
| `frontend/src/components/RangeBar.tsx` | Barra proporzionale con tacca budget | ✓ VERIFIED | Wired in TotalCard, DettaglioProView, BonusPanel |
| `frontend/src/components/CategoryCard.tsx` + `LetturaCategoria.tsx` | €/m² e peso | ✓ VERIFIED | Wired in EstimatePage, SavedEstimateDetail; LetturaCategoria anche in Pro |
| `frontend/src/components/TotalCard.tsx` + `RiepilogoIvaRighe` | Riepilogo imponibile/IVA/extra | ✓ VERIFIED | Wired |
| `frontend/src/components/BudgetAlert.tsx` | Avviso a tre stati con confronto | ✓ VERIFIED | Wired in Free, stima salvata, Pro |
| `backend/app/services/risultato.py` | Mirror Python per PDF | ✓ VERIFIED | Usato da `pdf_service.py`; `test_risultato.py` passa |
| `backend/app/routers/stima.py::_confronto_finiture` | Ricalcolo vero | ✓ VERIFIED | Ricalcolo con `EstimationService.compute` |
| `backend/alembic/versions/0024_budget_eur_su_stima.py` | Colonna budget | ✓ VERIFIED | Presente; modello e schemi allineati |
| `backend/app/templates/pdf_stima.html`, `pdf_stima_pro.html` | Lettura completa e avviso nel PDF | ✓ VERIFIED (codice) / ? rendering | Template e contesto verificati; resa visiva differita |

### Key Link Verification

| From | To | Via | Status |
|---|---|---|---|
| EstimatePage | POST /stima → `confronto_finiture` | `result.confronto_finiture` → `BudgetAlert` | WIRED |
| BudgetAlert (Free/salvata/Pro) | PATCH /me/stime/{id}/budget | `onSalva` → `patchBudgetStima` + invalidate | WIRED |
| DettaglioProView | `DettaglioProOut.totale_ivato_*`, `riepilogo_iva`, `budget_eur`, `confronto_finiture` | props a RangeBar/RiepilogoIvaRighe/BudgetAlert | WIRED |
| pdf_service | `stima.budget_eur` → `scala_barra`/`avviso_budget` | contesto Jinja | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|---|---|---|---|---|
| TotalCard/RangeBar | `totale`, `categorie`, `extra` | POST /stima (motore su listino DB) | Sì | FLOWING |
| BudgetAlert (Free) | `confronto_finiture` | ricalcolo `EstimationService.compute` | Sì | FLOWING |
| DettaglioProView | `riepilogo_iva`, `lettura_categorie`, `confronto_finiture` | `CalcoloDettaglioPro` server-side | Sì | FLOWING |
| BudgetAlert | `budget` | colonna `stima.budget_eur` | Sì | FLOWING |

### No-leak (regola di dominio 1)

Nessun campo `coefficiente_impresa`, `prezzo_impresa`, `moltiplicatore`, `base_eur_mq` nei nuovi DTO (`ConfrontoFinitureOut`, `RiepilogoIvaOut`, `RigaIvaOut`, `LetturaCategoriaOut`, campi aggiunti a `DettaglioProOut`, `BonusOut` esteso con `su_arredo`/`rata_annua_lavori_*`, `budget_eur` in `StimaSalvata*`). I DTO sono costruiti campo-per-campo (nessun `model_validate` su ORM). I template PDF citano "impresa" solo nei commenti di intestazione che lo vietano. `VoceOut.prezzo_min/max` è prezzo cliente (preesistente). Output sempre a range in web e PDF.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Test mirati fase 10 | `pytest tests/test_risultato.py tests/test_budget_stima.py tests/test_confronto_finiture.py tests/test_dettaglio_pro_budget.py tests/test_bonus_stima.py` | 81 passed in 90.8s | ✓ PASS |
| Type check frontend | `npx tsc -b` | exit 0 | ✓ PASS |
| Lint frontend | `npm run lint` | exit 0, solo warning preesistenti (set-state-in-effect, only-export-components) | ✓ PASS |
| Script G12 | `node scripts/check-richiesta-stima.ts` | `check-richiesta-stima: OK` | ✓ PASS |

Suite backend completa non eseguita qui (in corso separatamente per istruzione dell'orchestratore).

### Probe Execution

Nessun probe dichiarato per la fase. SKIPPED.

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| RIS-01 | RangeBar proporzionale | ✓ SATISFIED | Truth 1 |
| RIS-02 | €/m² e peso per categoria | ✓ SATISFIED | Truth 2 |
| RIS-03 | Riepilogo imponibile/IVA/extra | ✓ SATISFIED | Truth 3 |
| RIS-04 | Avviso budget con confronto a finiture inferiori | ✓ SATISFIED | Truth 4, 5 |

Nessun requisito orfano. Nota: la tabella di tracciabilità in fondo a `REQUIREMENTS.md` (righe 125-128) riporta ancora "da fare" per RIS-01..04, mentre le checkbox in alto sono `[x]`: da aggiornare in chiusura fase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| — | — | Nessun TBD/FIXME/XXX nei file backend/app e frontend/src toccati dai commit `(10…)` | — | — |
| `backend/app/templates/pdf_stima_pro.html` | — | WR-04: bonus e arredo assenti nel PDF Pro | ℹ️ Info | Rinviato a backlog per decisione dell'utente; non è nei Success Criteria |

### Human Verification Required

UAT web approvato dall'utente il 2026-10-01 (checklist `2026-09-30-ricollaudo-10-g10-g14.md` + fix `f06bd43` per G15; `10-HUMAN-UAT.md` `status: resolved`). Restano solo le verifiche visive PDF, differite al go-live su Render (WeasyPrint/GTK3 assenti su questa macchina):

- [ ] **PDF Free con budget superato** — Passo: su Render, scaricare il PDF di una stima Free con budget sotto il minimo. Atteso: barra proporzionale con cifre ai bordi, tacca budget, riepilogo IVA con extra, €/m² e peso per categoria, avviso con confronto a finiture inferiori e nota sul budget, Bonus Mobili nel blocco Arredo; nessun prezzo impresa.
  Note:
- [ ] **PDF Pro con budget** — Passo: su Render, scaricare il PDF di una stima Pro con budget. Atteso: blocco "Totale IVA inclusa" con barra e tacca, riepilogo per aliquota, €/m² e peso, avviso budget; nessun prezzo impresa.
  Note:

### Gaps Summary

Nessun gap bloccante. I 5 Success Criteria sono implementati e cablati end-to-end (web Free, stima salvata, vista Pro, template PDF), con dati reali dal motore e dal DB, e la regola anti-leak è rispettata nei nuovi DTO e nei template. Lo stato è `human_needed` solo per la resa visiva dei PDF, differita al go-live su Render. Aspetti minori da registrare: tabella di tracciabilità di REQUIREMENTS.md non aggiornata; goal della fase non in formato User Story nonostante `mode: mvp`; WR-04 in backlog.

---

_Verified: 2026-10-01_
_Verifier: Claude (gsd-verifier)_
