---
phase: 03-pro-dettaglio-sottocategorie
plan: 06
subsystem: frontend
tags: [react, react-query, react-router, shadcn, accordion, pro-detail]

# Dependency graph
requires:
  - phase: 03-pro-dettaglio-sottocategorie
    plan: 03
    provides: "GET/POST /me/stime/{id}/dettaglio-pro dietro require_pro, DTO chiusi anti-leak"
  - phase: 03-pro-dettaglio-sottocategorie
    plan: 04
    provides: "GET /me/stime/{id}/pdf-pro (PDF Pro dettagliato)"
  - phase: 03-pro-dettaglio-sottocategorie
    plan: 05
    provides: "PassaAProPage, SoftWallCta con 'Vedi dettaglio Pro' -> /dettaglio-pro?stima={id}, UserOut.pro"
provides:
  - "api/dettaglio-pro.ts (getDettaglioPro/postRisposteDettaglioPro/scaricaPdfPro, normalizzazione Decimal)"
  - "ui/accordion.tsx (shadcn) + SottocategoriaAccordion (righe-voce a range, empty-state)"
  - "DettaglioProPage (/dettaglio-pro?stima={id}): domande mirate + accordion + PDF Pro"
affects: []

tech-stack:
  added: []
  patterns:
    - "toNumber() duplicato in api/dettaglio-pro.ts (non condiviso con stima.ts) per non introdurre una dipendenza incrociata tra i due moduli client"
    - "scaricaPdfPro rispecchia byte-per-byte scaricaPdf (fetch diretto blob, filename da Content-Disposition, download nativo via <a download>)"
    - "Stato 'domande mirate collassate' derivato client-side dal primo GET (risposte tutte a zero -> form espanso; almeno una valorizzata -> riepilogo collassato), nessun flag esplicito 'risposto' nel DTO backend"

key-files:
  created:
    - frontend/src/api/dettaglio-pro.ts
    - frontend/src/components/ui/accordion.tsx
    - frontend/src/components/SottocategoriaAccordion.tsx
    - frontend/src/pages/DettaglioProPage.tsx
  modified:
    - frontend/src/App.tsx

key-decisions:
  - "toNumber/normalizzazione Decimal duplicati in dettaglio-pro.ts invece di estratti in un helper condiviso con stima.ts (scelta esplicitamente lasciata all'esecutore dal piano)"
  - "Il riepilogo collassato delle domande mirate è derivato lato client (risposte non tutte zero al primo caricamento => collassato), non da un flag server-side dedicato — coerente col DTO DettaglioProOut.risposte esistente (03-03), nessuna modifica al backend richiesta"

requirements-completed: [PRO-01, PDF-02]

# Metrics
duration: 20min
completed: 2026-08-27
---

# Phase 3 Plan 06: Frontend dettaglio Pro (accordion sottocategorie + domande mirate + PDF) Summary

**Client `api/dettaglio-pro.ts` (normalizzazione Decimal-al-confine) + accordion shadcn con `SottocategoriaAccordion` (righe-voce sempre a range) + `DettaglioProPage` (`/dettaglio-pro?stima={id}`) con domande mirate bagni/porte/condizionatori e bottone "Scarica PDF dettagliato" — codice completo e typecheck verde; il checkpoint umano di verifica end-to-end in browser (Task 3) resta aperto in attesa dell'utente.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-08-27
- **Completed:** 2026-08-27 (Task 1-2)
- **Tasks:** 2/3 completati (Task 3 è un checkpoint `human-verify` non eseguibile dall'agente)
- **Files modified:** 5 (4 creati, 1 modificato)

## Accomplishments

- `frontend/src/components/ui/accordion.tsx`: installato via `npx shadcn@latest add accordion` (registry ufficiale, nessun gate legittimità richiesto).
- `frontend/src/api/dettaglio-pro.ts`: `VoceOut`/`SottocategoriaOut`/`CategoriaDettagliataOut`/`RisposteDomande`/`DettaglioProOut` a numerici tipizzati `number`; normalizzatore `toNumber` che converte `quantita_stimata`/`prezzo_min`/`prezzo_max` dalla stringa-Decimal Pydantic al confine API (stesso pattern di `stima.ts`); `getDettaglioPro(stimaId)`, `postRisposteDettaglioPro(stimaId, risposte)`, `scaricaPdfPro(stimaId)` (rispecchia byte-per-byte `scaricaPdf` su `/me/stime/{id}/pdf-pro`).
- `frontend/src/components/SottocategoriaAccordion.tsx`: un `Accordion` shadcn per categoria, un `AccordionItem` per sottocategoria (trigger `codice · nome` per la famiglia gerarchica A-EDILE, solo `nome` per la famiglia catalogo B/C/D); contenuto = righe-voce (`descrizione` · `quantità stimata + UM` tabular-nums · `€ min – € max` tabular-nums); empty-state "Nessuna voce stimata per questa sottocategoria con i dati inseriti."; nessun accent su alcuna riga (solo il chevron del trigger, gestito dal primitivo shadcn).
- `frontend/src/pages/DettaglioProPage.tsx`: legge `stima` da `useSearchParams`; redirect a `/passa-a-pro` se anonimo/non-Pro, a `/le-mie-stime` se `stima` mancante o non numerico; heading "Dettaglio Pro" + intro di non-riconciliazione (D-01); `useQuery(getDettaglioPro)` con skeleton in loading e `Alert` destructive + "Riprova" in errore; blocco domande mirate (bagni/porte/condizionatori, `input` `inputmode="numeric"` min 0, nota amber sul default-se-salti, validazione "Inserisci un numero valido (0 o superiore).") con "Calcola il dettaglio" (`postRisposteDettaglioPro`) e "Salta, usa la stima automatica" (POST con risposte a zero), collassa a riepilogo con "Modifica"; dettaglio reso via `SottocategoriaAccordion` una per categoria; cluster CTA "Scarica PDF dettagliato" (`scaricaPdfPro`, stati loading/errore identici a `PdfDownloadButton`) + "Torna alla stima" (outline, `/`).
- `frontend/src/App.tsx`: rotta `/dettaglio-pro` registrata.

## Task Commits

1. **Task 1: shadcn accordion + api/dettaglio-pro.ts + SottocategoriaAccordion** - `a898d33` (feat)
2. **Task 2: DettaglioProPage (domande mirate + accordion + PDF Pro) + rotta** - `d32adf1` (feat)
3. **Task 3: Verifica manuale flusso Pro end-to-end (attivazione -> dettaglio a range -> domande mirate -> PDF, anti-leak/paywall)** - checkpoint `human-verify` (`gate="blocking"`), **non eseguito dall'agente**: codice pronto, verifica in browser resta all'utente.

**Plan metadata:** (commit successivo con SUMMARY.md/STATE.md/ROADMAP.md)

## Files Created/Modified

- `frontend/src/components/ui/accordion.tsx` - primitivo shadcn (net-new)
- `frontend/src/api/dettaglio-pro.ts` - client GET/POST dettaglio-pro + download PDF Pro (net-new)
- `frontend/src/components/SottocategoriaAccordion.tsx` - accordion righe-voce a range (net-new)
- `frontend/src/pages/DettaglioProPage.tsx` - schermata dettaglio Pro completa (net-new)
- `frontend/src/App.tsx` - rotta `/dettaglio-pro`

## Decisions Made

- Vedi `key-decisions` in frontmatter. Nessuna modifica al backend richiesta: il DTO `DettaglioProOut.risposte` (03-03) è sufficiente per derivare lo stato "collassato/espanso" delle domande mirate lato client.

## Deviations from Plan

None - plan eseguito esattamente come scritto (Task 1 e 2 auto).

## Issues Encountered

Nessuno. `npx tsc --noEmit` pulito su entrambi i task; grep anti-leak (`coefficiente_impresa|prezzo_impresa|base_eur_mq`) vuoto su tutti i file creati/modificati.

## Known Stubs

Nessuno. Tutti i dati mostrati provengono dagli endpoint reali `dettaglio-pro`/`pdf-pro` (03-03/03-04), nessun placeholder/mock.

## User Setup Required

Nessuna configurazione esterna. **Task 3 richiede la verifica manuale dell'utente in browser** (backend `:8000` + frontend `:5173` attivi): attivazione Pro -> `/dettaglio-pro?stima={id}` -> accordion per sottocategoria a range -> domande mirate ricalcolano -> "Scarica PDF dettagliato" -> anti-leak/paywall 403 da Free. Nota: su Windows senza GTK3 il download PDF può dare 500 sul render (atteso e non bloccante, come 02-08/02-09) — l'endpoint resta comunque raggiungibile e gated.

## Threat Flags

Nessuna superficie non prevista dal `<threat_model>` del piano: T-03-13 (redirect UI, gate reale server-side su require_pro), T-03-01e (rendering solo dei campi del DTO chiuso), T-03-07b (validazione client min 0 + bound server-side già presente in 03-03) — tutte già mitigate come pianificato, nessuna modifica extra necessaria.

## Next Phase Readiness

- Codice Fase 3 Plan 06 completo e verificato via typecheck (`npx tsc --noEmit` verde su entrambi i task) e grep anti-leak.
- **Gate aperto:** il checkpoint `human-verify` (Task 3) non è stato approvato in questa sessione — resta da eseguire manualmente dall'utente prima di considerare il Plan 06 (e quindi la Fase 3) chiuso end-to-end.
- Con questo plan, i success criteria PRO-01 e PDF-02 della Fase 3 sono implementati end-to-end lato codice; restano da confermare dal vivo tramite il checkpoint Task 3 (che copre anche l'intero flusso Pro cross-plan: attivazione 03-05, dettaglio 03-03, PDF 03-04).

---
*Phase: 03-pro-dettaglio-sottocategorie*
*Completed: 2026-08-27 (Task 1-2; Task 3 in attesa di verifica manuale dell'utente)*

## Self-Check: PASSED

Tutti i file dichiarati (5) e i commit dichiarati (`a898d33`, `d32adf1`) verificati presenti su disco / in git log.
