# ristruttura-stima

## What This Is

App web che trasforma un computo metrico estimativo Excel (usato oggi manualmente per i preventivi di ristrutturazione) in uno strumento self-service. L'utente si registra (email o Google), indica **città, mq dell'appartamento e tipo di ristrutturazione (leggera / moderata / totale)** e riceve una **stima dei costi** divisa nelle 4 categorie **Edile, Finiture, Serramenti/Porte, Prodotti**. Con abbonamento **Pro** ottiene il dettaglio per sottocategorie (a.1/a.2…). A ogni livello può **scaricare un PDF** e **contattare un professionista** per il preventivo dettagliato.

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
30 piani su 4 fasi, 21/21 requisiti consegnati. Archivio:
`.planning/milestones/v1.0-ROADMAP.md`.

**In corso:** v2.0 — *domande e motore parametrico*, fasi **05-10**. Le fasi 05 e 06
(catalogo domande in database, motore Free parametrico, wizard unico) sono complete e
committate; la 07 (arredo) e' la prossima. 27 requisiti mappati in
`.planning/REQUIREMENTS.md`.

**Obiettivi della v2:** la v1 risponde a `(citta, mq, tipo)`; la v2 risponde a *com'e' fatta
questa casa e cosa vuoi farci* — e lo fa senza che aggiungere una domanda costi un deploy.
Il catalogo di domande, le opzioni e i loro effetti sono **dati amministrabili**. La fine
della milestone chiude il bug dei cataloghi alternativi nel motore Pro, che oggi somma voci
che sono alternative fra loro.

**Debito noto portato dentro la v2:** i coefficienti sono una bozza e non una taratura; la
curatela di `voce.livello` esiste solo nel `dev.db` locale; le cinque variabili `R2_*` non
sono configurate su Render (upload avatar a 503).

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Registrazione/login con email e Google
- [ ] Input guidato: città, mq, tipo di ristrutturazione (leggera/moderata/totale)
- [ ] Stima Free: 4 totali di categoria + IVA differenziata + extra (CSE/CSP, pratiche), output a range
- [ ] Stima Pro: apertura sottocategorie a.1/a.2 con voci e quantità stimate
- [ ] Motore parametrico Ibrido C con coefficienti €/m² e quantità-per-m²
- [ ] Listini prezzi per città con fallback + disclaimer
- [ ] Pannello admin per gestire listini, coefficienti, città, referenti, testi
- [ ] Export PDF brandizzato a ogni livello (Free e Pro)
- [ ] Contatto professionista (aperto a tutti) con lead via email + dashboard admin
- [ ] Abbonamento Pro (paywall sul dettaglio sottocategorie)

### Out of Scope

- Simulazione finanziamento a rate — presente nel file, escluso da v1
- Moltiplicatori prezzo per zona geografica — fase 2, servono i dati
- Portale completo rete professionisti (assegnazione, gestione partner) — visione futura
- Prezzo esatto abbonamento Pro — da definire prima del go-live

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Motore Ibrido C (€/m² Free, parametrico Pro), output a range | Free istantaneo, Pro credibile senza modellare 300 righe; range protegge legalmente pre-sopralluogo | — Pending |
| Utente vede solo prezzo cliente | Il coefficiente impresa è margine interno | — Pending |
| Città = selettore listino, non moltiplicatore | Prezzi realmente diversi per città; RE è l'unico listino iniziale | — Pending |
| Prezzi/coefficienti gestiti da pannello admin, non nel codice | L'utente deve aggiornarli senza sviluppatore | — Pending |
| Free = 4 totali categoria; Pro = sottocategorie | Taglio naturale del valore percepito | — Pending |
| Contatto professionista aperto a tutti | È il vero obiettivo di business (acquisizione lavori) | — Pending |
| Modello dati multi-referente dal giorno 1, v1 con un solo referente | Non bloccare la rete futura senza costruire il portale ora | — Pending |
| Extra sì, finanziamento no in v1 | Preventivo completo ma senza variabili di credito | — Pending |

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
*Last updated: 2026-09-21 — milestone v1.0 archiviata, v2.0 aperta (fasi 05-10).*
