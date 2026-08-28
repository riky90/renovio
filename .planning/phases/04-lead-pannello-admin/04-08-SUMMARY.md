---
phase: 04-lead-pannello-admin
plan: 08
subsystem: frontend-admin
tags: [admin, crud, listini, coefficienti, excel-upload]
dependency-graph:
  requires: [04-07, 04-02, 04-10, 04-05]
  provides: [ListiniPage, CoefficientiPage, ExcelUploadDialog, api/admin/listini, api/admin/coefficienti, api/admin/uploadListino]
  affects: [frontend/src/App.tsx routes (già registrate da 04-07, nessuna modifica qui)]
tech-stack:
  added: []
  patterns:
    - "api/admin/*.ts: wrapper apiGet/apiPost/apiPatch/apiDelete + toNumber() locale per normalizzare i campi Decimal-come-stringa dal wire (stesso pattern di api/stima.ts)"
    - "ExcelUploadDialog: multipart via fetch diretto con credentials:'include' (non apiPost, FormData non JSON)"
key-files:
  created:
    - frontend/src/api/admin/listini.ts
    - frontend/src/api/admin/coefficienti.ts
    - frontend/src/api/admin/uploadListino.ts
    - frontend/src/components/admin/ExcelUploadDialog.tsx
  modified:
    - frontend/src/pages/admin/ListiniPage.tsx
    - frontend/src/pages/admin/CoefficientiPage.tsx
decisions:
  - "Voce: nessuna 'creazione' via CRUD — solo modifica (prezzo/UM) ed elimina, coerente con l'assenza di un endpoint POST /admin/listini/voci sul backend 04-02 (le voci nascono solo dall'upload Excel). La 'crea' del must_have si applica a listino (nuova città) e categoria, entrambi supportati da POST reali."
  - "CoefficientiPage: 5 tab (Moltiplicatori, Base €/m² sola lettura, IVA, Extra, Coefficienti Pro) invece di 4 — Base €/m² separata da Moltiplicatori per rispecchiare 1:1 i 5 endpoint GET del router 04-10, restando comunque entro l'Open Question 6 (planner-discretion)."
  - "Categoria listino mostrata solo con categoria_code (nessun nome descrittivo) — il backend 04-02 non espone un nome per ListinoCategoria, solo il code; nessuna sorgente per un nome più leggibile senza introdurre un nuovo lookup."
metrics:
  duration: "~50 minuti"
  completed: 2026-08-28
---

# Phase 04 Plan 08: Listini/Coefficienti CRUD + upload Excel a due passi Summary

CRUD reali per Listini e prezzi (creazione listino/città, categoria con base_eur_mq/coefficiente_impresa, modifica/elimina voce) e Coefficienti (5 famiglie), più `ExcelUploadDialog` con entry-point esplicito "Nuova città" oltre al listino esistente, sopra i backend 04-02/04-10/04-05.

## What Was Built

- **`frontend/src/api/admin/listini.ts`**: `getListini`, `createListino` (POST, onboarding città), `updateListino`, `getListinoCategorie`, `createListinoCategoria`, `updateListinoCategoria`, `deleteListinoCategoria`, `getVoci`, `updateVoce` (solo prezzo/UM), `deleteVoce`. Normalizza `base_eur_mq`/`coefficiente_impresa`/`prezzo_cliente` (Decimal-come-stringa) con `toNumber()`.
- **`frontend/src/api/admin/coefficienti.ts`**: `getMoltiplicatori`/`updateMoltiplicatore`, `getIva`/`updateIva`, `listExtra`/`createExtra`/`updateExtra`/`deleteExtra`, `getCoeffPro`/`updateCoeffPro`, `getBaseEurMq` (sola lettura).
- **`frontend/src/pages/admin/ListiniPage.tsx`**: header con "Aggiungi listino" (dialog nome/città/is_default) + "Carica listino da Excel"; selettore listino; `AdminTable` categorie (categoria_code · base €/m² · coefficiente impresa · azioni: voci/modifica/elimina) con `tabular-nums`; `AdminTable` voci per la categoria selezionata (codice · descrizione · UM · prezzo cliente · azioni), edit voce con SOLO prezzo/UM (descrizione read-only). Elimina categoria/voce via `AdminDeleteConfirm`.
- **`frontend/src/pages/admin/CoefficientiPage.tsx`**: `Tabs` con 5 sotto-sezioni (Moltiplicatori, Base €/m² sola lettura, IVA, Extra con create/edit/delete, Coefficienti Pro), stesso pattern `AdminTable`+`AdminCrudDialog` di ListiniPage.
- **`frontend/src/api/admin/uploadListino.ts`**: `previewUpload(file, target)` multipart (FormData, niente scritture, anche ramo nuova città) e `confirmUpload(target, nuove, modificate)` (round-trip stateless, JSON).
- **`frontend/src/components/admin/ExcelUploadDialog.tsx`**: step destinazione (radio "Listino esistente"/"Nuova città" con input città esplicito) → dropzone (.xlsx, ≤10MB, pre-check client + drag&drop) → skeleton "Verifica del file in corso…" → anteprima diff (3 badge nuove/modificate/scartate, tabella valore precedente→nuovo, pannello scarti con motivo, `accordion` oltre 10 righe) → "Conferma import" (disabilitato a 0 righe valide) / "Annulla import" (alert-dialog "Torna alla preview"/"Annulla import"). Wired in `ListiniPage` col bottone "Carica listino da Excel"; alla conferma invalida `["admin-listini"]` e `["admin-listino-categorie", listinoId]`.

## Verification

- `npx tsc --noEmit` pulito (dopo `npm install`, node_modules non presente all'avvio del worktree).
- `npx vite build` completato con successo (bundle emesso, solo warning non bloccante su chunk size).
- `grep -n "nuova_citta"` trova il ramo sia in `ExcelUploadDialog.tsx` che in `uploadListino.ts`.
- Anti-leak: `base_eur_mq`/`coefficiente_impresa` compaiono solo in `api/admin/listini.ts`/`api/admin/coefficienti.ts` e nelle pagine `pages/admin/*` — nessun altro file del frontend li referenzia.
- App.tsx non modificato (route già registrate da 04-07).

## Deviations from Plan

None — plan eseguito come scritto, con le 3 decisioni documentate sopra (voce senza "crea" per assenza endpoint backend; 5 tab invece di 4 per Coefficienti; categoria mostrata solo per code).

## OPEN CHECKPOINT — Task 3 (checkpoint:human-verify, gate="blocking")

Non eseguibile in autonomia in questo contesto (worktree isolato, nessun backend/DB live per una verifica visiva end-to-end con login admin reale). Registrato come aperto per la verifica umana:

**What built:** Pagine Listini (create listino + categoria + voce prezzo/UM, con base €/m² e coefficiente impresa) e Coefficienti CRUD reali, più upload .xlsx a due passi con entry-point nuova città, sopra 04-02/04-10/04-05.

**How to verify:**
1. Accedi come admin, `/admin/listini`: "Aggiungi listino" crea un nuovo listino/città; poi crea/modifica/elimina categorie e voci (edit voce mostra solo prezzo/UM; l'elimina chiede conferma). Verifica che coefficiente impresa e base €/m² siano visibili SOLO qui.
2. `/admin/coefficienti`: modifica un moltiplicatore, poi calcola una nuova stima Free → il totale riflette il nuovo valore (D-11).
3. "Carica listino da Excel" → scegli "Nuova città", inserisci un nome città, prova un file non-.xlsx e uno >10MB (bloccati), poi carica `docs/computo-base-reggio-emilia.xlsx` → anteprima diff con conteggi/scarti; conferma → toast righe importate; calcola una stima per quella città nuova → non va in fallback.
4. Ripeti l'upload verso un listino esistente e verifica che al preview nulla sia stato scritto (cambia solo dopo "Conferma import").

**Resume signal:** "approvato" oppure descrivi i problemi.

## Self-Check: PASSED

- FOUND: frontend/src/api/admin/listini.ts
- FOUND: frontend/src/api/admin/coefficienti.ts
- FOUND: frontend/src/api/admin/uploadListino.ts
- FOUND: frontend/src/pages/admin/ListiniPage.tsx
- FOUND: frontend/src/pages/admin/CoefficientiPage.tsx
- FOUND: frontend/src/components/admin/ExcelUploadDialog.tsx
- FOUND commit: 55bbe0e feat(04-08): CRUD listini/prezzi e coefficienti sopra 04-02/04-10
- FOUND commit: 6fadac6 feat(04-08): ExcelUploadDialog con destinazione esistente/nuova città
