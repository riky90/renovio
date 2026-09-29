---
phase: 10-risultato-leggibile
plan: 06
subsystem: dettaglio-pro-backend
tags: [pro, iva, confronto-finiture, lettura-risultato]
requires: [10-05]
provides:
  - risultato.riepilogo_iva_pro, lettura_categorie_pro, LetturaCategoria
  - CalcoloDettaglioPro e _compute_dettaglio esteso (IVA, lettura, confronto)
  - DettaglioProOut.totale_ivato_min/max, riepilogo_iva, lettura_categorie, confronto_finiture, finiture_al_minimo, budget_eur
affects: [10-07, 10-08]
key-files:
  created:
    - backend/tests/test_dettaglio_pro_budget.py
  modified:
    - backend/app/services/risultato.py
    - backend/app/schemas/dettaglio_pro.py
    - backend/app/routers/dettaglio_pro.py
    - backend/tests/test_risultato.py
    - backend/tests/test_no_leak.py
    - backend/tests/test_pdf_pro.py
key-decisions:
  - "Totale Pro IVA inclusa = IVA per categoria (Categoria.iva_pct) sulle sole categorie nel_totale_lavori + extra attivi lordi (regola _eur del Free), calcolato una sola volta in _compute_dettaglio"
  - "Confronto Pro = seconda DettaglioProService.compute con ogni categoria un gradino sotto (LivelloFinitura.ordine); None se il massimo IVA inclusa non scende; livello mostrato = inferiore della categoria col livello piu' alto (A4)"
  - "Nome del livello dal catalogo domanda 'finitura' se attivo, altrimenti LivelloFinitura.nome"
duration: n/a
completed: 2026-09-29
---

# Phase 10 Plan 06: Dettaglio Pro con IVA, lettura e confronto Summary

Il dettaglio Pro porta server-side totale IVA inclusa, riepilogo per aliquota, EUR/m2 e peso per categoria e confronto con finiture un livello sotto, tutto da un unico `_compute_dettaglio` condiviso da GET, POST e PDF.

## Tasks

1. **Totale IVA, riepilogo, lettura** (f7645c2 funzioni e DTO, d927748 router): `riepilogo_iva_pro` e `lettura_categorie_pro` in `risultato.py` (solo composizione di funzioni esistenti), nuovi modelli DTO, `CalcoloDettaglioPro`, `_categorie_nel_totale`, `_riepilogo_pro`, `_to_out(calcolo, livelli, budget_eur)`. L'arredo resta fuori da IVA, pesi e confronto.
2. **Confronto Pro** (d927748): `_confronto_pro` con ricalcolo vero; `finiture_al_minimo` true se tutte le categorie con livello sono al minimo.

I due task sono stati implementati insieme nel router (stesso file): i commit sono divisi per file (funzioni+DTO / router+test), non per task.

## Verifica

- `pytest test_dettaglio_pro_budget test_risultato test_no_leak test_dettaglio_pro test_dettaglio_pro_livelli test_dettaglio_pro_alternative test_dettaglio_pro_paywall test_pdf_pro`: verdi (104 passed nella prima run + test_pdf_pro/test_risultato rieseguiti dopo il fix: 31 passed, 2 skipped weasyprint).
- Motori (`services/dettaglio_pro.py`, `estimation.py`) non toccati.

## Deviations from Plan

**1. [Rule 3 - Blocking] test_pdf_pro.py adeguato alla nuova firma**
- `_compute_dettaglio` ora ritorna `CalcoloDettaglioPro` e `_to_out` ha firma nuova: due test di test_pdf_pro.py (parita' GET/PDF e pavimento scelto) aggiornati. Nessun cambio di asserzioni.

**2. Test del confronto adattato ai dati seed**
- Nel seed attuale "base" costa piu' di "medio" (voci non curate), quindi da "medio" il ricalcolo non abbassa il massimo e il confronto e' None (D-09 corretto). Il caso positivo e' testato da "alto" -> "medio", con verifica di uguaglianza col totale IVA di una stima a livelli "medio". Aggiunto un test per il caso None. Il caso "tutti base" resta `finiture_al_minimo` true.

## Known Stubs

Nessuno.

## Threat Flags

Nessuno. T-10-18 mitigata (DTO chiusi, mapping manuale, test_no_leak esteso con confronto e budget); T-10-19 gate invariati; T-10-21 livelli solo da DB. T-10-20 accettata: una seconda `compute` Pro per richiesta (N+1 noto).

## Self-Check: PASSED

File creato presente (`backend/tests/test_dettaglio_pro_budget.py`), commit f7645c2 e d927748 in git log.
