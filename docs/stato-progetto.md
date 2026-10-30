# Stato del progetto — 2026-10-30

Fotografia di Renovio (`ristruttura-stima`) al commit `c8785a7`, identico su `riky90/renovio`
(pubblico, PR) e `riky90/stima` (privato, deploy). Serve a chi riprende il lavoro senza la
storia delle sessioni precedenti.

## In una riga

Il prodotto è completo e in produzione con il **computo parametrico** (v3.0, fase 11): un solo
motore per Free e Pro. Il motore non è ancora stato confrontato con computi veri, e i suoi
valori sono una bozza ragionata dalle note del file Excel. Il prossimo passo è proprio
questo confronto (vedi `HANDOVER.md`).

## Cosa c'è

| Milestone | Fasi | Stato |
|---|---|---|
| v1.0 MVP | 01–04 | Chiusa il 2026-09-09. Stima Free a range, account Google, PDF, lead, pannello admin. |
| v2.0 domande e motore parametrico | 05–10 | Chiusa il 2026-10-01. Catalogo domande, wizard unico, arredo, Excel admin, configuratore Pro, budget. |
| v3.0 computo parametrico | 11 | Implementata e mergiata su `main` (PR #1–#4). Taratura sui casi reali fatta (2026-10-30). |

Fase 11, in sintesi (dettaglio in `docs/proposta-computo-parametrico.md` §10):

- **Motore unico** in `backend/app/services/computo.py`: grandezze (cosa misura la casa) →
  interventi (cosa si fa) → regola per voce (come si calcola), sei tipi di regola, traccia per
  voce. Il Free è il computo sommato per categoria, il Pro lo mostra voce per voce.
- **Migrazioni** `0025`–`0028`: modello grandezze/regole/preset, catalogo del computo, sanitari
  per livello sui DB già seminati, accenti del catalogo.
- **18 domande d'intervento** nel wizard Free. Il tipo di ristrutturazione
  (leggera/moderata/totale) è un **preset** di risposte, ed è il punto di partenza del wizard.
- **Curatela da Excel** nella pagina Coefficienti, scheda "Computo parametrico": scarica,
  anteprima con errori, applica tutto o niente.
- **Fallback**: un listino senza regole usa ancora il calcolo €/m² della v1.
- **Sito pubblico**: SEO, prerender (`vite build --ssr` + `scripts/prerender.mjs`), guide ai
  costi, `vercel.json`, pagina 404.
- `/health` riporta la versione della migrazione applicata.

Numeri dopo la prima taratura (Reggio Emilia, 85 m², risposte di default, imponibile):

| Tipo | Edile | Totale lavori |
|---|---|---|
| Leggera | 14,0 k€ | 17,6 k€ |
| Moderata | 32,3 k€ | 40,9 k€ |
| Totale | 39,4 k€ | 69,2 k€ |

## Cosa manca

1. **Dopo la taratura (TAR-01, 2026-10-30)**: eccedenza IVA al 22% dei beni significativi,
   altri computi reali per le voci di cantiere e per un eventuale range asimmetrico. Le domande
   Pro per i lavori a corpo e il clima "solo predisposizione" sono fatti (migrazione `0030`). Dettaglio in
   `.planning/prove/2026-11-taratura/README.md`.
2. **Incoerenze del file da chiarire con il tecnico** (proposta §7): il 7% senza etichetta su
   `(B+C+D)`. A.9.1, A.9.2 e movimentazione sono state decise sui computi reali (2026-10-30).
3. **Domande non ancora poste**: tipo di muro demolito, doccia o vasca, bagni ciechi, carta da
   parati.
4. **Range per incertezza**: oggi il range è un ±% fisso. L'obiettivo è una banda stretta sulle
   quantità risposte e larga su quelle di default.
5. **Debito ereditato** (in `.planning/milestones/v2.0-ROADMAP.md`):
   - IN-01..07;
   - il seed con descrizioni duplicate (gres 30x60, parquet wengè), che dà il coefficiente
     sbagliato su un DB nuovo;
   - due test che creano un `dev.db` vuoto invece di saltare;
   - nessun test runner per il frontend.
6. **Pulizia manuale**: il vecchio `stima-db` sospeso su Render va cancellato a mano.

## Note di contesto

- `.planning/STATE.md` è indietro: dice ancora "v2.0 non in produzione" e "fase 11 in
  implementazione". Va aggiornato quando si chiude la fase 11 con la taratura.
- Il **prezzo impresa** (prezzo × 0,65/0,6/0,55/0,5) resta server-side. I computi in
  `docs/casi-reali/` hanno le colonne "TOTALE IMPRESA" e "Guadagno": sono dati di test, non
  vanno mai copiati in fixture lette dal frontend, nei PDF o nelle risposte API.
- I test girano con `backend/.venv/Scripts/python.exe -m pytest` (suite completa ~11 minuti).
- Allineamento dei due repo: procedura in `CLAUDE.md`, sezione "Ambiente di sviluppo".
