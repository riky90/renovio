# ristruttura-stima

## What This Is

App web (marchio **Renovio**) che trasforma un computo metrico estimativo Excel in uno strumento self-service. L'utente si registra (email o Google) e, con un **wizard a quattro step**, descrive città, m², tipo di ristrutturazione e com'è fatta la casa (domande servite dal database, ambienti da arredare, livello di finiture, budget). Riceve una **stima a range** divisa nelle 4 categorie **Edile, Finiture, Serramenti/Porte, Prodotti**, con IVA, extra, detrazioni e forfait arredo accanto al totale lavori. Con abbonamento **Pro** ottiene il computo per sottocategorie, configurabile su finitura e pavimento. A ogni livello può **scaricare un PDF** e **contattare un professionista**. Il pannello admin cura listini, coefficienti, catalogo domande ed effetti, anche via Excel.

## Core Value

Da `(città, mq, tipo)` a una **stima credibile a range** in pochi secondi, senza sopralluogo — e da lì generare un **lead qualificato** per il professionista. Il valore vive nel motore di coefficienti (l'IP dell'app), non nella UI.

## Context

- **Fonte**: `2025_Computo Base_ER_PREZZI IMPRESE DEFINITI (2).xlsx`. È un computo bottom-up dove un tecnico inserisce quantità esatte. I prezzi sono di **Reggio Emilia**.
- **Salto di modello**: il file parte da quantità esatte; l'app parte da mq+tipo → serve un **modello parametrico** che stimi quantità/costi. Approccio scelto: **Ibrido C** (€/m² per il Free, quantità parametriche sulle voci-chiave per il Pro), output sempre a **range**.
- **Due livelli di prezzo** nel file: prezzo cliente (mostrato) e prezzo impresa via coefficiente 0.65/0.6/0.55/0.5 (interno, mai esposto).
- **Città = selettore del listino**: prezzi in DB per città; RE è il primo. Città senza listino → fallback con disclaimer.
- **Rete di professionisti**: visione a più referenti per città; v1 con l'utente come unico referente.
- Brief completo della discussione: `BRIEF-DISCUSSIONE.md` (root del progetto).

## Current State

**Shipped:** v1.0 (MVP) — 2026-09-09, in produzione. Backend su Render, frontend su Vercel.
Archivio: `.planning/milestones/v1.0-ROADMAP.md`.

**Completata, non ancora in produzione:** v2.0 — *domande e motore parametrico*, fasi 05-10,
53 piani, 30/30 requisiti, audit `passed` (2026-10-01). Archivio:
`.planning/milestones/v2.0-ROADMAP.md`. Il push (circa 350 commit, migrazioni 0014-0024) e'
in attesa di: prova delle migrazioni su Postgres, taratura A.6.11, `BACKEND_PUBLIC_URL` su
Render. Dopo il push, collaudo dei PDF in produzione.

**Stack:** FastAPI + SQLAlchemy/Alembic (SQLite in sviluppo, Postgres in produzione),
WeasyPrint per i PDF; React + Vite + Tailwind/shadcn. Suite backend 1008 test.

**Debito noto:** coefficienti Pro in bozza finche' l'Excel di taratura non e' compilato;
`domanda_mirata_key` e `Voce.livello` curabili ma non lette dal motore; effetti legati agli id
di voce (fragili con un secondo listino); snapshot della stima fornito dal client; anteprima
admin solo Free; nessun test runner frontend.

## Next Milestone Goals

Da definire con `/gsd:new-milestone`. Candidati: go-live della v2.0 e taratura vera dei
coefficienti, secondo listino (altra città), progetti come contenitore di piu' stime,
indirizzo e geocoding, AI come parser del testo libero.

## Requirements

### Validated

- ✓ Registrazione/login con email e Google — v1.0
- ✓ Input guidato: città, mq, tipo di ristrutturazione — v1.0 (wizard a quattro step dalla v2.0)
- ✓ Stima Free: 4 totali di categoria + IVA differenziata + extra, output a range — v1.0
- ✓ Stima Pro: sottocategorie con voci e quantità stimate — v1.0, senza alternative sommate dalla v2.0
- ✓ Motore parametrico Ibrido C — v1.0; parametrico sulle risposte del catalogo — v2.0
- ✓ Listini prezzi per città con fallback + disclaimer — v1.0
- ✓ Pannello admin per listini, coefficienti, città, referenti, testi — v1.0; catalogo domande ed export/import Excel — v2.0
- ✓ Export PDF brandizzato Free e Pro — v1.0 (lettura completa, bonus e arredo dalla v2.0, collaudo PDF al go-live)
- ✓ Contatto professionista con lead via email + dashboard admin — v1.0
- ✓ Abbonamento Pro (paywall sul dettaglio) — v1.0
- ✓ Catalogo domande/opzioni/effetti in database, curabile senza deploy — v2.0
- ✓ Forfait arredo a range accanto al totale lavori, Bonus Mobili — v2.0
- ✓ Configuratore Pro su finitura e pavimento — v2.0
- ✓ Risultato leggibile (RangeBar proporzionale, €/m², peso, riepilogo IVA) e budget dichiarato — v2.0

### Active

- [ ] Go-live della v2.0 in produzione
- [ ] Taratura vera dei coefficienti Pro (Excel di taratura → migrazione 0025)

### Out of Scope

- Simulazione finanziamento a rate — presente nel file, escluso da v1
- Moltiplicatori prezzo per zona geografica — fase 2, servono i dati
- Portale completo rete professionisti (assegnazione, gestione partner) — visione futura
- Prezzo esatto abbonamento Pro — da definire prima del go-live

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Motore Ibrido C (€/m² Free, parametrico Pro), output a range | Free istantaneo, Pro credibile senza modellare 300 righe; range protegge legalmente pre-sopralluogo | ✓ Good |
| Utente vede solo prezzo cliente | Il coefficiente impresa è margine interno | ✓ Good (test anti-leak su tutte le route) |
| Città = selettore listino, non moltiplicatore | Prezzi realmente diversi per città; RE è l'unico listino iniziale | ✓ Good |
| Prezzi/coefficienti gestiti da pannello admin, non nel codice | L'utente deve aggiornarli senza sviluppatore | ✓ Good (anche via Excel dalla v2.0) |
| Free = 4 totali categoria; Pro = sottocategorie | Taglio naturale del valore percepito | ✓ Good |
| Contatto professionista aperto a tutti | È il vero obiettivo di business (acquisizione lavori) | — Pending (serve traffico in produzione) |
| Modello dati multi-referente dal giorno 1, v1 con un solo referente | Non bloccare la rete futura senza costruire il portale ora | — Pending |
| Extra sì, finanziamento no in v1 | Preventivo completo ma senza variabili di credito | ✓ Good |
| Domande, opzioni ed effetti come dati, con un insieme chiuso di tipi di effetto | Aggiungere una domanda non deve costare un deploy, ma niente formule libere in tabella | ✓ Good — v2.0 (otto tipi) |
| Arredo accanto al totale lavori, mai dentro | L'oracolo dei lavori non deve muoversi | ✓ Good — v2.0 |
| Assi Pro (finitura, pavimento) come effetti del catalogo | Chiude il bug delle alternative sommate con un test che conta le voci | ✓ Good — v2.0 |
| Budget come asse separato dalle finiture | Il budget avvisa e confronta, non muove il prezzo | ✓ Good — v2.0 |
| Push solo a fine milestone | Il push deploya e migra la produzione | ⚠️ Revisit — 350 commit accumulati rendono il go-live un salto grande |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-01 — milestone v2.0 completata e archiviata, push in attesa.*
