---
phase: 10-risultato-leggibile
plan: 16
subsystem: frontend-risultato
tags: [gap-closure, G7, G8, bonus, rangebar]
requires: [10-13, 10-14]
provides:
  - "BonusPanel con una sola barra: range della detrazione (detrazione_min/max)"
  - "RangeBar con cifre min/max ai bordi (flex justify-between), senza prop evidenza"
affects: [10-18]
key-files:
  modified:
    - frontend/src/components/BonusPanel.tsx
    - frontend/src/components/RangeBar.tsx
    - frontend/src/lib/risultato.ts
    - frontend/src/pages/EstimatePage.tsx
    - frontend/src/components/SavedEstimateDetail.tsx
    - frontend/src/components/DettaglioProView.tsx
decisions:
  - "La barra del Bonus usa la detrazione COMPLESSIVA (detrazione_min/max, Bonus Mobili incluso): esiste in tutti gli snapshot, anche precedenti a G5. Da confermare in checklist 10-18"
  - "Il server continua a mandare netto_* e detrazione_lavori_*; il client non disegna piu' il netto"
  - "Posizione delle cifre nel PDF invariata (resta quella di 10-10): da confermare in checklist 10-18"
metrics:
  tasks: 2
  files: 6
completed: 2026-09-30
---

# Phase 10 Plan 16: G7 e G8, Bonus a barra singola e cifre RangeBar ai bordi Summary

Il pannello Bonus mostra solo la barra del range recuperato in detrazione, e le cifre della RangeBar tornano ai bordi del contenitore, solo frontend.

## Commits
- 562e21e: G7, BonusPanel senza `totaleMin`/`totaleMax`, senza barra del totale, senza "Dopo le detrazioni" e "Costo totale IVA inclusa"; legenda con "Recuperi in detrazione sui lavori" (se presente) e rata annua; nuova testata "Quanto recuperi con le detrazioni"; nota arredo riscritta; tre chiamanti aggiornati
- 3aefa2b: G8, riga cifre della RangeBar a `flex items-baseline justify-between gap-2`, "fino a" sempre visibile; rimossi `evidenza` e `pctSuScala` (nessun altro utilizzatore)

## Verifiche
- `npm run build` ok; `npm run lint` exit 0, nessun warning su RangeBar/BonusPanel (restano solo i preesistenti)
- Grep di accettazione: BonusPanel 0 match sui termini vietati, un solo `<RangeBar`; RangeBar 0 match su `flexBasis|evidenza|pctSuScala`, `justify-between` e `fino a` presenti, `budgetPct` intatto; `grep evidenza|pctSuScala frontend/src` vuoto
- Verifica visiva (una barra nel Bonus, cifre ai bordi, 360px) rimandata alla checklist del piano 10-18

## Deviations from Plan
- [Rule 3] Dopo la rimozione di `evidenza`, `tetto` restava destrutturato e inutilizzato in RangeBar (errore TS6133): tolto dalla destrutturazione.

## Nota sugli strumenti
Aggiornamento di STATE.md/ROADMAP.md fatto secondo le indicazioni del prompt (gli handler `state` del gsd-sdk sono inaffidabili su questo progetto).

## Known Stubs
None.

## Threat Flags
None. Nessun campo nuovo nel DTO ne' nel client; nessun calcolo fiscale nel client; ogni importo resta a range.

## Self-Check: PASSED
