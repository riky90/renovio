---
phase: 10-risultato-leggibile
plan: 21
subsystem: frontend-bonus-arredo
tags: [bonus, arredo, G10, G11]
requires: ["10-19"]
provides:
  - "Pannello Bonus sui soli lavori, Bonus Mobili nella card Arredo"
  - "Card Arredo dentro DettaglioProView (Le mie stime e /dettaglio-pro uguali)"
affects: ["10-22", "10-24"]
key-files:
  modified:
    - frontend/src/api/stima.ts
    - frontend/src/lib/risultato.ts
    - frontend/src/components/BonusPanel.tsx
    - frontend/src/components/ArredoCard.tsx
    - frontend/src/pages/EstimatePage.tsx
    - frontend/src/components/SavedEstimateDetail.tsx
    - frontend/src/components/DettaglioProView.tsx
    - frontend/src/pages/DettaglioProPage.tsx
key-decisions:
  - "Il client filtra per su_arredo e sceglie campi gia' calcolati dal server; nessun calcolo fiscale"
  - "Titolo del pannello Bonus e legenda 'Recuperi in detrazione sui lavori' invariati (decisione di Riccardo)"
requirements-completed: [RIS-01, RIS-03]
completed: 2026-09-30
---

# Phase 10 Plan 21: Bonus Mobili nella card Arredo, card Arredo nella vista Pro condivisa Summary

Il pannello Bonus mostra solo le voci sui lavori (barra e rata con ripiego per gli snapshot vecchi); il Bonus Mobili sta nella card Arredo, a range, in Free, stima salvata e Pro.

## Commit

- `67547d0` feat(10-21): tipi, `normalizeBonus`, `vociBonusLavori`/`vociBonusArredo`/`formatAliquota`, BonusPanel, ArredoCard
- `de39ad3` fix(10-21): chiamanti e ArredoCard in DettaglioProView

## Cosa e' stato fatto

- `normalizeBonus` riporta `su_arredo` e `rata_annua_lavori_min/max` (null preservato): la home li rimanda a `postSalvaStima` nello snapshot.
- BonusPanel: nessun rendering se non ci sono voci sui lavori; nota sull'arredo al posto di `detrazioneEsclusa`.
- ArredoCard: prop `bonus`, sezione "Detrazione sull'arredo" con range, rate e nota tetto; disclaimer bonus se il pannello Bonus non c'e'. Niente RangeBar.
- G11: `DettaglioProView` legge lo snapshot con la queryKey `["stima-dettaglio", stimaId]` e mostra la card Arredo indipendentemente dal blocco IVA; `DettaglioProPage` non la duplica piu'. `LeMieStimePage.tsx` non toccato.

## Verifica

`npm run build` OK; `npm run lint` senza warning nuovi (restano quelli preesistenti su altri file e `DettaglioProView.tsx:167`, effetto gia' presente). `<ArredoCard` in 3 posti; `MOBILI` in `frontend/src` = 0.

## Deviazioni dal piano

Nessuna.

## Known Stubs

Nessuno.

## Threat Flags

Nessuno.

## Nota per la checklist (10-24)

Le stime con arredo salvate prima di G10 non hanno `su_arredo`: mostrano ancora il Bonus Mobili nel pannello Bonus (nessun backfill). Verifica dal vivo necessaria (nessun test runner frontend).

## Self-Check: PASSED
