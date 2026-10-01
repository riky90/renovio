---
phase: 10-risultato-leggibile
plan: 24
subsystem: collaudo
tags: [gap-closure, ri-collaudo, G10-G15]
requires: [10-19, 10-20, 10-21, 10-22, 10-23]
provides:
  - "Checklist di ri-collaudo G10-G14 (.planning/checklists/2026-09-30-ricollaudo-10-g10-g14.md)"
  - "Esito registrato: approvato; G15 (da G14f) trovato, corretto e ri-collaudato"
affects: []
key-files:
  created:
    - .planning/checklists/2026-09-30-ricollaudo-10-g10-g14.md
  modified:
    - .planning/phases/10-risultato-leggibile/10-HUMAN-UAT.md
    - frontend/src/components/CategoryCard.tsx
    - frontend/src/components/SavedEstimateDetail.tsx
    - frontend/src/routes/LeMieStimePage.tsx
decisions:
  - "Nessun backfill: le stime salvate prima di 10-19..10-21 tengono il Bonus Mobili nel pannello Bonus"
  - "La stima aggiornata con Modifica tiene data e posizione originali in Le mie stime"
  - "Il piano della stima si fissa al primo salvataggio: una stima Free resta Free anche se l'utente passa a Pro"
  - "G15: nella vista snapshot (solo stime Free) il lucchetto c'e' sempre; per un utente Pro il link e' 'Rifai in versione Pro'"
metrics:
  tasks: 2
  files: 5
completed: 2026-10-01
---

# Phase 10 Plan 24: ri-collaudo G10-G14 Summary

Ri-collaudo del 2026-10-01: approvato. G10, G11, G12 e G14 passano dal vivo; G13 (PDF) e'
implementato e la verifica visiva resta differita al go-live. L'unica nota, G14(f), ha aperto
il gap G15, corretto in giornata e ri-collaudato da Riccardo.

## Commits
- 407a371: checklist di ri-collaudo G10-G14 e gap collegati in HUMAN-UAT
- c052f62: checklist compilata da Riccardo
- f06bd43: fix G15, stima Free resta Free in Le mie stime anche per un utente Pro
- b5bd5fc: gap G15 in HUMAN-UAT con causa radice

## Controlli automatici (Task 1)

| Controllo | Esito |
|---|---|
| Suite backend completa | 989 passed, 5 skipped (WeasyPrint), 0 failed |
| `npm run build` | ok |
| `npm run lint` | exit 0 |
| `node scripts/check-richiesta-stima.ts` | ok |
| Dopo il fix G15: `tsc -b`, `oxlint` sui tre file | puliti |

## Esito del checkpoint (Task 2)

Approvato. Le tre scelte da confermare sono confermate (vedi `decisions`).

G14(f) al primo giro: "quando la riapro dalle mie stime anche se era free la vedo pro". Il DB
era corretto (tier `free` invariato, badge assente); mancava il lucchetto sulle card perche'
`LeMieStimePage` passava a `SavedEstimateDetail` il piano dell'utente. Era il fix P5 del
2026-08-27, scritto quando anche le stime Pro si aprivano nella vista snapshot; dalla Fase 03
le stime Pro aprono `DettaglioProView`. Verificato nel browser con un utente Free diventato Pro:
stima Free con lucchetto e link a `/nuova-stima`, stima Pro su `DettaglioProView` senza teaser.

## Deviazioni
- **[Regola 1 - Bug] G15 corretto dentro questo piano**, invece che in un piano di gap nuovo:
  modifica di poche righe nel perimetro di G14, chiesta da Riccardo, ri-collaudata dal vivo.
- La voce G14(f) della checklist come scritta non era eseguibile (passare a Pro smonta la home e
  perde l'id della stima); Riccardo l'ha percorsa da "Le mie stime", che e' il caso reale.
