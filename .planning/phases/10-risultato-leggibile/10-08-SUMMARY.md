---
phase: 10-risultato-leggibile
plan: 08
subsystem: pdf
tags: [pdf, budget, iva, range-bar, parita-schermo-pdf]
requires: [10-06]
provides:
  - stato_budget, TESTI_AVVISO, avviso_budget in services/risultato.py
  - PDF Free con tacca budget e riquadro avviso (da snapshot + colonna budget_eur)
  - PdfService.render_html_pro / render_pro(calcolo, ...) con lettura completa e budget su base IVA inclusa
affects: [10-09]
key-files:
  modified:
    - backend/app/services/risultato.py
    - backend/app/services/pdf_service.py
    - backend/app/templates/pdf_stima.html
    - backend/app/templates/pdf_stima_pro.html
    - backend/app/routers/dettaglio_pro.py
    - backend/tests/test_risultato.py
    - backend/tests/test_pdf.py
    - backend/tests/test_pdf_pro.py
key-decisions:
  - "Il PDF Free legge budget_eur dalla stessa riga dello snapshot (getattr, NULL sulle stime pre-fase): nessun motore chiamato"
  - "avviso_budget restituisce anche 'delta' e 'nota'; il livello del confronto e' in minuscolo come nel web"
  - "render_pro riceve CalcoloDettaglioPro: EUR/m2, peso e riepilogo IVA sono gli stessi valori (calcolo.lettura, calcolo.riepilogo) della vista Pro"
  - "Riquadro budget duplicato inline nei due template (niente include) per mantenere i grep di acceptance"
  - "Parita' testi con il web: test che legge frontend/src/lib/risultato.ts e cerca ogni frammento fisso di TESTI_AVVISO"
duration: n/a
completed: 2026-09-29
---

# Phase 10 Plan 08: Budget e lettura del risultato nei PDF Summary

Il PDF Free riporta tacca "Il tuo budget", riquadro di stato e confronto finiture dallo snapshot; il PDF Pro riporta barra, EUR/m2, peso, riepilogo IVA e riquadro budget sul totale IVA inclusa, dallo stesso `_compute_dettaglio` della schermata.

## Tasks

1. **PDF Free** (4447f2c): `stato_budget`, `TESTI_AVVISO`, `avviso_budget`; tacca con etichetta ancorata ai bordi senza transform/calc; riquadro assente senza budget o su snapshot pre-fase; test di parita' testi col TS.
2. **PDF Pro** (3acf073): `render_html_pro` + `render_pro(calcolo, ...)`; router passa `calcolo`; template con lettura per categoria, barra, riepilogo, riquadro; test HTML con e senza budget.

## Verifica

`pytest tests/test_pdf_pro.py tests/test_pdf.py tests/test_dettaglio_pro_budget.py tests/test_no_leak.py tests/test_risultato.py`: 75 passed, 4 skipped (rendering byte WeasyPrint non disponibile). Nessun motore chiamato in pdf_service; nessun "coefficiente"/"prezzo impresa" nei template.

## Deviations from Plan

**1. [Rule 3 - Blocking] Test esistente `_render_html` in test_pdf_pro.py**
- Renderizzava il template con il vecchio contesto (senza riepilogo/barra): ora usa `PdfService.render_html_pro`.
- Commit: 3acf073

Nota: il grep di acceptance `transform` sul template Free non puo' essere 0 (preesistente `text-transform`); i test escludono `text-transform` con lookbehind e nessun `transform:` o `calc(` e' stato aggiunto.

## Known Stubs

Nessuno.

## Threat Flags

Nessuno. T-10-22/23/24 mitigate: contesto con soli totali cliente, autoescape attivo, endpoint e gate invariati.

## Self-Check: PASSED
