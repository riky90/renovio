---
phase: 10-risultato-leggibile
plan: 20
subsystem: pdf
tags: [pdf, barra, bonus, arredo, G13, G10]
requires: ["10-19"]
provides:
  - "Cifre della barra ai bordi nei PDF Free e Pro"
  - "PDF Free: detrazioni sull'arredo nel blocco Arredo, bonus lavori separato"
affects: ["10-24 (verifica a occhio dei PDF al go-live)"]
tech-stack:
  added: []
  patterns: ["derivato di presentazione in Python (_bonus_pdf), non in Jinja"]
key-files:
  modified:
    - backend/app/templates/pdf_stima.html
    - backend/app/templates/pdf_stima_pro.html
    - backend/app/services/pdf_service.py
    - backend/tests/test_pdf.py
    - backend/tests/test_pdf_pro.py
key-decisions:
  - "Il filtro su_arredo e il ripiego sui campi pre-G5/G10 stanno in _bonus_pdf: nessun calcolo, solo scelta di campi congelati"
requirements-completed: [RIS-01, RIS-03]
completed: 2026-09-30
---

# Phase 10 Plan 20: PDF, cifre ai bordi e Bonus Mobili nell'Arredo Summary

Nei PDF Free e Pro la riga delle cifre della barra e' a tutta larghezza (min a sinistra, "fino a" al centro, max a destra); nel PDF Free le detrazioni `su_arredo` passano dal blocco bonus al blocco Arredo.

## Commit

- `2f8b878` fix(10-20): cifre della barra ai bordi (G13), test RED poi GREEN nello stesso commit
- `5b9a091` feat(10-20): `_bonus_pdf` e template Free (G10)

## Cosa e' stato fatto

- Template Free e Pro: la tabella `barra-cifre` ha tre celle senza larghezze da `left_pct`/`width_pct`; il segmento resta proporzionale.
- `pdf_service._bonus_pdf`: separa `lavori`/`arredo`, sceglie `detrazione_lavori_*` e `rata_annua_lavori_*` con ripiego sui totali per gli snapshot vecchi. Passata al template come `bonus_pdf`.
- Template Free: "Totale detraibile" diventa "Detrazione sui lavori"; dopo "Totale arredo" le voci arredo a range; se non ci sono voci lavori compare il disclaimer bonus nel blocco Arredo.
- Test: `test_cifre_barra_ai_bordi` (Free e Pro) e classe `TestPdfBonusArredo` (4 test: voce spostata, ripiego pre-G5, solo voci arredo, senza arredo/bonus).

## Verifica

`test_pdf.py`, `test_pdf_pro.py`, `test_no_leak.py`: 40 passed, 4 skipped (WeasyPrint non installato). `grep MOBILI` su service e template = 0; "Totale detraibile" = 0.

## Deviazioni dal piano

Nessuna. Il RED del task 1 e' stato verificato (2 failed) prima della modifica dei template.

## Known Stubs

Nessuno.

## Threat Flags

Nessuno.

## Nota per la checklist di collaudo (10-24)

La resa grafica dei PDF (cifre ai bordi, blocco Arredo con detrazioni) e' provata solo sull'HTML: va guardata a occhio sul PDF reale al go-live.

## Self-Check: PASSED
