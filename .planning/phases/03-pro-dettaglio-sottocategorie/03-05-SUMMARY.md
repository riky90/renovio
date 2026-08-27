---
phase: 03-pro-dettaglio-sottocategorie
plan: 05
subsystem: ui
tags: [react, react-query, react-router, shadcn, paywall, subscription]

requires:
  - phase: 03-pro-dettaglio-sottocategorie (03-01)
    provides: "POST /me/pro/attiva endpoint + UserOut.pro nel backend"
provides:
  - "api/subscription.ts (postAttivaPro)"
  - "UserOut.pro nel client frontend"
  - "PassaAProPage (/passa-a-pro) con 3 stati: anonimo, non-Pro, gia-Pro"
  - "SoftWallCta che naviga invece di soft-wall toast su Passa a Pro"
  - "CategoryCard con striscia teaser bloccata per utenti Free"
  - "AccountMenu con badge Pro"
affects: [03-06]

tech-stack:
  added: []
  patterns:
    - "PassaAProPage riusa la forma useMutation/isPending/isError di PdfDownloadButton per lo stub di attivazione"
    - "Flag Pro propagato via prop da EstimatePage (useAuth().user?.pro), nessuna fetch aggiuntiva in SoftWallCta/CategoryCard"

key-files:
  created:
    - frontend/src/api/subscription.ts
    - frontend/src/routes/PassaAProPage.tsx
  modified:
    - frontend/src/api/auth.ts
    - frontend/src/App.tsx
    - frontend/src/components/SoftWallCta.tsx
    - frontend/src/components/CategoryCard.tsx
    - frontend/src/components/AccountMenu.tsx
    - frontend/src/pages/EstimatePage.tsx

key-decisions:
  - "isPro propagato come prop dai componenti (derivato da useAuth().user?.pro in EstimatePage), mai una fetch dedicata per il flag"
  - "EstimatePage.tsx modificato oltre ai files_modified dichiarati nel frontmatter del piano, perché l'azione del Task 2 lo richiede esplicitamente per il wiring isPro (nessuna nuova rotta/fetch introdotta)"

patterns-established:
  - "Stub di attivazione Pro production-shaped: loading/success/error inline, invalidazione query ['me'] su successo"

requirements-completed: [PRO-03, PRO-02]

duration: 15min
completed: 2026-08-27
---

# Phase 3 Plan 05: Upgrade/paywall frontend Summary

**Flusso di attivazione Pro stub end-to-end lato UI (PassaAProPage + postAttivaPro) e ricablaggio della CTA "Passa a Pro" da soft-wall toast a navigazione reale, con teaser Free su CategoryCard e badge Pro su AccountMenu.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-08-27T06:48:25Z
- **Completed:** 2026-08-27T06:53:13Z
- **Tasks:** 2
- **Files modified:** 7 (2 nuovi, 5 modificati)

## Accomplishments
- `postAttivaPro()` in `api/subscription.ts` chiama `POST /me/pro/attiva`; `UserOut.pro: boolean` esposto nel client
- `PassaAProPage` (`/passa-a-pro`) gestisce i 3 stati richiesti: anonimo → redirect a `/registrati?intent=pro`, non-Pro → schermata upgrade con bottone "Attiva Pro" (loading/success/error), già-Pro → stato neutro con link a `/le-mie-stime`
- `SoftWallCta`: "Passa a Pro" ora naviga a `/passa-a-pro` (non più toast); per utenti Pro lo stesso slot diventa "Vedi dettaglio Pro" verso `/dettaglio-pro?stima={savedId}` (disabilitato con label "Salvataggio in corso…" se `savedId` è nullo)
- `CategoryCard`: striscia teaser bloccata (icona Lock + "Dettaglio disponibile con Pro" + link "Passa a Pro") mostrata solo per utenti Free
- `AccountMenu`: badge accent "Pro" quando `user.pro`
- Flag Pro propagato dai prop (`isPro={!!user?.pro}` in `EstimatePage.tsx`), nessuna nuova chiamata di rete introdotta

## Task Commits

1. **Task 1: api/subscription.ts + UserOut.pro + PassaAProPage + rotta** - `945e79f` (feat)
2. **Task 2: SoftWallCta naviga/variante Pro + teaser CategoryCard + badge Pro AccountMenu** - `b4c0a4d` (feat)

**Plan metadata:** (commit successivo)

## Files Created/Modified
- `frontend/src/api/subscription.ts` - `postAttivaPro()` → `POST /me/pro/attiva`
- `frontend/src/api/auth.ts` - `UserOut` esteso con `pro: boolean`
- `frontend/src/routes/PassaAProPage.tsx` - schermata upgrade/attivazione stub Pro (UI-SPEC §B)
- `frontend/src/App.tsx` - rotta `/passa-a-pro` registrata
- `frontend/src/components/SoftWallCta.tsx` - CTA "Passa a Pro"/"Vedi dettaglio Pro" naviga invece di soft-wall
- `frontend/src/components/CategoryCard.tsx` - striscia teaser bloccata per Free
- `frontend/src/components/AccountMenu.tsx` - badge "Pro" nel dropdown
- `frontend/src/pages/EstimatePage.tsx` - propaga `isPro` a `SoftWallCta`/`CategoryCard`

## Decisions Made
- Il flag Pro è derivato lato client da `useAuth().user?.pro` e passato via prop a `SoftWallCta`/`CategoryCard`, mai richiesto con una fetch dedicata — coerente col vincolo "nessuna nuova chiamata di rete" del piano.
- `EstimatePage.tsx` è stato modificato pur non comparendo nella lista `files_modified` del frontmatter del piano: l'azione del Task 2 lo richiede esplicitamente ("Passare `isPro={!!user?.pro}` da `EstimatePage.tsx`"), quindi non è una deviazione ma un'esecuzione fedele dell'azione descritta nel testo del piano.

## Deviations from Plan

None - plan executed exactly as written (l'unica nota è la modifica di `EstimatePage.tsx`, già richiesta testualmente dall'azione del Task 2 anche se assente dal frontmatter `files_modified`).

## Issues Encountered
None.

## User Setup Required
None - nessuna configurazione di servizio esterno richiesta.

## Next Phase Readiness
- La superficie di navigazione del paywall è completa e pronta per 03-06 (schermata dettaglio Pro `/dettaglio-pro`), che riceverà il traffico da "Vedi dettaglio Pro" (SoftWallCta) e dal link per-categoria previsto da UI-SPEC §A.
- Nessun dato Pro reale né impresa esposto in questo slice (verificato via grep anti-leak); il gate reale resta server-side (03-01/03-03/03-04).

---
*Phase: 03-pro-dettaglio-sottocategorie*
*Completed: 2026-08-27*
