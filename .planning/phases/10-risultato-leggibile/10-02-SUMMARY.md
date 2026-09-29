---
phase: 10-risultato-leggibile
plan: 02
subsystem: backend-pdf
tags: [risultato, pdf, iva, presentazione, jinja]
requires: [10-01]
provides:
  - services/risultato.py (scala_barra, incidenza_eur_mq, somma_medi, peso_categoria, riepilogo_iva)
  - PdfService.render_html
affects: [10-09]
tech-stack:
  added: []
  patterns: [funzioni pure di presentazione mirror del TypeScript, HTML testabile senza WeasyPrint]
key-files:
  created:
    - backend/app/services/risultato.py
    - backend/tests/test_risultato.py
  modified:
    - backend/app/services/pdf_service.py
    - backend/app/templates/pdf_stima.html
    - backend/tests/test_pdf.py
key-decisions:
  - "Stesse regole del web: tetto 1,2 x max, passi 1000/5000, larghezza minima 4, peso solo sulle categorie, riga IVA piu' alta assorbe l'arrotondamento"
  - "Il PDF legge solo lo snapshot; snapshot pre-fase senza extra/mq si rendono (incidenza None, nessuna riga extra)"
requirements-completed: [RIS-01, RIS-02, RIS-03]
duration: ~15min
completed: 2026-09-29
---

# Phase 10 Plan 02: PDF Free leggibile Summary

Il PDF Free mostra la barra proporzionale statica (div a larghezza percentuale, niente JS/transform/calc), €/m² e peso per categoria con mini-barra, e il riepilogo Imponibile lavori / IVA per aliquota / Costi extra / Totale IVA inclusa, tutto da `risultato_json` tramite funzioni pure in `services/risultato.py`.

## Commits
- e995de4: test RED funzioni pure
- 4c56cdb: services/risultato.py
- 9b76566: test RED render_html
- 1d62670: render_html, template, test HTML

## Deviations from Plan

**1. [Rule 1 - Bug nel criterio] grep `transform` in pdf_stima.html**
- Il template ha già `text-transform: uppercase` preesistente, quindi `grep -c transform` = 0 non è soddisfacibile alla lettera. Il test verifica l'assenza della proprietà `transform:` (regex con lookbehind) e `calc(`: nessuno dei due presente.

**2. Extra separato**: il template non aveva un elenco extra separato da rimuovere; gli extra compaiono solo nel riepilogo.

## Verification
`pytest tests/test_pdf.py tests/test_risultato.py`: 24 passed, 2 skipped (WeasyPrint nativo assente). Guardia statica sul motore verde. Rendering PDF reale rinviato alla checklist 10-09.

## Known Stubs
None.

## Self-Check: PASSED
