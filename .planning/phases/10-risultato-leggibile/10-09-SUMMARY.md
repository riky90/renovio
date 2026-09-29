---
phase: 10-risultato-leggibile
plan: 09
subsystem: collaudo
tags: [uat, checklist, gaps]
requires: [10-07, 10-08]
provides:
  - checklist di collaudo 10-HUMAN-UAT.md compilata da Riccardo
  - elenco dei gap G1-G6 per il ciclo --gaps
affects: [10-risultato-leggibile]
key-files:
  modified:
    - .planning/phases/10-risultato-leggibile/10-HUMAN-UAT.md
decisions:
  - "Base IVA per categoria: tutto IVA esclusa in Free, Pro e PDF; il riepilogo mantiene imponibile + IVA per aliquota + extra + Totale IVA inclusa"
  - "Scope: G1-G6 si fanno ora nella Fase 10 tramite /gsd-plan-phase 10 --gaps"
  - "Sezione PDF differita al go-live su Render (WeasyPrint/GTK3 assenti in locale)"
metrics:
  completed: 2026-09-29
---

# Phase 10 Plan 09: Collaudo della fase Summary

Collaudo eseguito: i controlli automatici sono verdi, ma la verifica manuale di Riccardo ha restituito 6 gap (non approvato) e una sezione PDF differita al go-live.

## Risultati automatici

| Controllo | Esito |
| --- | --- |
| Suite backend completa | 936 passed, 5 skipped, 0 failed |
| `npm run build` (frontend) | ok |
| `npm run lint` (frontend) | ok |

I 5 test saltati sono quelli sui byte dei PDF (WeasyPrint non installato su Windows).

## Esito del collaudo manuale: gap trovati

Non approvato. Tutte le altre voci sono passate; le "Scelte di Claude da confermare" sono tutte confermate.

| Gap | Tipo | Sintesi |
| --- | --- | --- |
| G1 | bug | Etichette min/max della RangeBar ai bordi del box (`flex justify-between` in `frontend/src/components/RangeBar.tsx`), non sotto gli estremi del segmento |
| G2 | bug | Base IVA incoerente: CategoryCard Free mostra totale IVA inclusa mentre €/m² usa l'imponibile; Pro "Totale {categoria}" e' IVA esclusa. Decisione: tutto per categoria IVA esclusa (Free, Pro, PDF), etichette esplicite |
| G3 | bug | `confronto_finiture`: da "lusso/alto" il "Con finiture medie" da' 337.923, una stima fresca a "medio" da' 336.111. Causa radice da indagare |
| G4 | feature | "Modifica" nel Free riporta a un wizard vuoto: deve riaprire il wizard precompilato (budget incluso) |
| G5 | feature | Pannello Bonus: barra del costo totale con impatto di bonus/detrazioni evidenziato |
| G6 | feature | Pannello Bonus assente nella versione Pro: da aggiungere |

## Differito

- Intera sezione "PDF" della checklist: verifica umana al go-live su Render. Non fallita.

## Deviations from Plan

None - il piano e' stato eseguito come scritto. L'esito "gap trovati" e' il risultato del collaudo, non un difetto di esecuzione.

## Prossimo passo

`/gsd-plan-phase 10 --gaps` per pianificare G1-G6 (i gap sono nella sezione `## Gaps` di `10-HUMAN-UAT.md`).
