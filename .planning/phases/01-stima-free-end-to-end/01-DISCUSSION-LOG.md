# Phase 1 — Discussion Log

**Date:** 2026-08-24 · Mode: discuss (default)

Riferimento human-only. Le decisioni operative sono in `01-CONTEXT.md`.

## Aree discusse (scelte dall'utente: tutte e 4)

### 1. Definizione dei 3 tipi
- Opzioni: €/m² per categoria per tipo · **moltiplicatore per tipo** · definizione diversa.
- Scelta: **moltiplicatore per tipo** su €/m² base per categoria. Definizioni leggera/moderata/totale proposte da Claude accettate implicitamente.

### 2. Come nasce il range
- Opzioni: **±% configurabile per tipo** · ±% unico · due set di coefficienti.
- Scelta: **±% configurabile per tipo**, gestita da admin.

### 3. Città & fallback (UX)
- Opzioni: **campo libero + fallback trasparente** · elenco chiuso · campo libero con avviso "zona non coperta".
- Scelta: **campo libero + autocomplete + fallback su RE con disclaimer**.

### 4. Schermata risultato Free + CTA
- Layout scelto: **4 card categoria + totale, range in evidenza** (no grafico).
- CTA scelte: Passa a Pro, Contatta professionista, Scarica PDF, Salva/crea account.
- **Emersa decisione strutturale**: l'utente vuole account per accedere al Free + salvataggio automatico.

### 4b. Risoluzione del gate account (follow-up)
- Trade-off di conversione sollevato da Claude (signup wall vs soft wall).
- Scelte utente: **soft wall** (vede la stima, account per salvare/PDF/contatto; auto-save alla registrazione) + **PDF in Fase 2 dedicata**.
- Conseguenza: la stima Free resta **anonima in Fase 1**, auth resta in Fase 2, **roadmap non ristrutturata**.

## Deferred
Auth/salvataggio/PDF → F2 · Pro/paywall → F3 · Lead/Admin CRUD → F4 · moltiplicatori zona → post-v1 · aliquota IVA serramenti da confermare.
