---
phase: 10-risultato-leggibile
plan: 10
subsystem: risultato
tags: [gap-closure, G1, G2, rangebar, iva-esclusa, pdf]
requires: []
provides:
  - importo, EUR/m2 e peso di categoria sulla stessa base (imponibile, IVA esclusa) in Free/Pro, web e PDF
  - cifre min/max della RangeBar (web e PDF) sotto gli estremi del segmento
affects: [10-15]
tech-stack:
  added: []
  patterns: [spaziatori flexBasis per allineare etichette a un segmento percentuale, tabella a celle percentuali nei PDF]
key-files:
  modified:
    - backend/app/services/risultato.py
    - backend/app/services/pdf_service.py
    - backend/app/templates/pdf_stima.html
    - backend/app/templates/pdf_stima_pro.html
    - backend/tests/test_risultato.py
    - backend/tests/test_pdf.py
    - backend/tests/test_pdf_pro.py
    - frontend/src/lib/risultato.ts
    - frontend/src/components/CategoryCard.tsx
    - frontend/src/components/SottocategoriaAccordion.tsx
    - frontend/src/components/DettaglioProView.tsx
    - frontend/src/components/RangeBar.tsx
decisions:
  - "G2: base per categoria = imponibile; riepilogo, barra del totale e budget restano IVA inclusa"
  - "pdf_service ricade su totale_* solo per snapshot senza imponibile_* di categoria"
metrics:
  completed: 2026-09-29
  tasks: 2
---

# Phase 10 Plan 10: chiusura G1 e G2 Summary

Importi, EUR/m2 e peso per categoria ora usano tutti l'imponibile (IVA esclusa) con etichetta esplicita, e le cifre min/max della RangeBar seguono gli estremi del segmento nel web e nei PDF.

## Commits
- aee52f9: G2, base imponibile (mirror Python, CategoryCard, etichette Pro).
- 4c1e838: G1, RangeBar e `.barra-cifre` dei PDF; colonna PDF Free su imponibile e etichette PDF Pro.

## Verifica
- pytest test_risultato, test_pdf, test_pdf_pro: 0 failed (skip WeasyPrint).
- `npm run build` ok; `npm run lint` solo warning preesistenti.

## Deviations from Plan
- Le modifiche ai template PDF (G2 e G1) sono nel secondo commit, non separabili per file: il primo commit non contiene i template.
- Nessun'altra deviazione. Nessun campo nuovo nei DTO (no-leak invariato).

## Known Stubs
None.

## Note
Ri-collaudo visivo (360px, cifre sotto il segmento) nella checklist del piano 10-15.

## Self-Check: PASSED
