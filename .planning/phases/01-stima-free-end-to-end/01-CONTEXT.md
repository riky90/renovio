# Phase 1: Stima Free end-to-end - Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Da `(città, mq, tipo di ristrutturazione)` a una **stima Free a range** con i 4 totali di categoria (Edile, Finiture, Serramenti/Porte, Prodotti), IVA differenziata ed extra inclusi, alimentata da un **listino Reggio Emilia in database**. La stima è **anonima** (nessun login richiesto per vederla). Non include: autenticazione/salvataggio (Fase 2), PDF (Fase 2), dettaglio sottocategorie Pro (Fase 3), invio lead (Fase 4). Le CTA verso quelle funzioni sono presenti nella schermata risultato ma rimandano alle fasi successive.
</domain>

<decisions>
## Implementation Decisions

### Motore Free (€/m²) e i 3 tipi
- **D-01:** Modello Free = **€/m² base per categoria × moltiplicatore per tipo**. Un valore €/m² base per ciascuna delle 4 categorie (dal listino RE), poi un moltiplicatore per `leggera` / `moderata` / `totale`. Alcune categorie possono avere moltiplicatore ~0 in `leggera`.
- **D-02:** Definizioni di riferimento dei 3 tipi (affinabili in taratura, non vincolanti per il codice):
  - *Leggera*: tinteggiature, sostituzione pavimenti/rivestimenti e sanitari, piccole opere; peso su Finiture + Prodotti; Edile e impianti minimi.
  - *Moderata*: rifacimento bagno/cucina, alcune demolizioni tramezzi, impianti parziali, alcuni serramenti; 4 categorie a intensità media.
  - *Totale*: demolizioni diffuse, tutti gli impianti, tutti i pavimenti/rivestimenti/serramenti/porte/sanitari; categorie al massimo.
- **D-03:** €/m² base e moltiplicatori vivono in **database**, editabili da admin (pannello completo in Fase 4). In Fase 1 basta il **seed** con i valori di RE estratti dal file computo.

### Range (min–max)
- **D-04:** Il range nasce da una **percentuale ± configurabile per tipo** (gestita da admin), più ampia dove c'è più incertezza (es. leggera ±10%, moderata ±15%, totale ±20% — valori di partenza). Non due tabelle di coefficienti.
- **D-05:** L'output all'utente è **sempre un range**, mai un numero secco, a ogni livello (categoria e totale).

### Città & fallback
- **D-06:** Selezione città a **campo libero con autocomplete**; l'utente può digitare qualsiasi città.
- **D-07:** Se la città non ha un listino proprio (in Fase 1: tutte tranne RE), la stima usa il **listino RE come fallback** e mostra un **disclaimer trasparente** ("stima basata su listino Reggio Emilia, non ancora tarata su <città>"). Nessun utente resta escluso.

### Schermata risultato Free
- **D-08:** Layout: **riepilogo input in alto** + **4 card categoria** (ognuna col proprio range) + **totale complessivo IVA inclusa in evidenza**. No grafico in Fase 1.
- **D-09:** CTA presenti: **Passa a Pro**, **Contatta un professionista**, **Scarica PDF**, **Salva / crea account**. In Fase 1 queste CTA rimandano alle funzioni delle fasi successive (soft wall) — non sono ancora operative.

### Account gate (soft wall)
- **D-10:** La stima Free è **visibile senza login**. L'account serve solo per **salvare, scaricare il PDF e contattare**; il salvataggio è **automatico all'atto della registrazione**. L'autenticazione vera resta in **Fase 2** — in Fase 1 le CTA che la richiedono rimandano lì.

### Regole di dominio (portate avanti dal progetto — non ri-discusse)
- **D-11:** L'utente vede **solo il prezzo cliente**; il prezzo/coefficiente impresa (0.65/0.6/0.55/0.5) resta server-side, mai inviato al client.
- **D-12:** **IVA differenziata per categoria**: Edile 10%, Finiture 22%, Prodotti 10%, Serramenti/Porte = da confermare l'aliquota esatta (il file la marca "iva inc" senza % chiara) → default provvisorio 22%, esposta come parametro admin.
- **D-13:** **Extra inclusi** nel totale (CSE/CSP, pratiche amministrative). **Finanziamento a rate escluso**.

### Claude's Discretion
- Scelta dello stack tecnico e dell'architettura (delegata a researcher/planner). Candidato dai progetti dell'utente: FastAPI + React, deploy Railway. Nessun vincolo imposto in questa fase.
- Struttura del data model dei listini/coefficienti, purché rispetti: prezzi in DB, seed RE, prezzo impresa non esposto, predisposizione multi-città e multi-referente.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Dominio e decisioni di progetto
- `CLAUDE.md` — regole di dominio non negoziabili (prezzo impresa mai esposto, range, città=listino, IVA, multi-referente).
- `BRIEF-DISCUSSIONE.md` — analisi del file computo + le 7 decisioni fondanti.
- `.planning/PROJECT.md` — Core Value, Key Decisions, scope.
- `.planning/REQUIREMENTS.md` — requisiti v1 (Fase 1 = EST-01..06, ENG-01..03).
- `.planning/ROADMAP.md` — confini di fase e success criteria.

### Dati sorgente
- `docs/computo-base-reggio-emilia.xlsx` — listino RE. Fogli rilevanti: `A-EDILE`, `B-FINITURE`, `C- SERRAMENTI PORTE`, `D- PRODOTTI` (voci, UM, prezzi unitari), `listini` (coefficienti impresa 0.65/0.6/0.55/0.5), `Analisi preliminareTOTALI` (IVA per categoria, extra). Da qui si estrae il seed dei €/m² base per categoria.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Nessuno: progetto greenfield, nessun codice esistente.

### Established Patterns
- Nessun pattern di codice pregresso. Da stabilire nella pianificazione.

### Integration Points
- Nessuno esistente. Il data model dei listini/coefficienti creato qui sarà la base delle Fasi 3 (Pro) e 4 (Admin), quindi va progettato per essere esteso (sottocategorie/voci, più città, più referenti).

</code_context>

<specifics>
## Specific Ideas

- La struttura del file computo è il riferimento diretto: 4 categorie = 4 fogli; il livello sottocategorie a.1/a.2 (Fase 3) esiste già nel foglio A-EDILE (105 codici). Il seed dei €/m² per categoria va derivato dai totali/voci del listino RE.
- Il coefficiente impresa (foglio `listini`) è margine interno: modellarlo nel DB ma non esporlo mai.
</specifics>

<deferred>
## Deferred Ideas

- **Autenticazione email+Google, salvataggio stime, ruolo admin** → Fase 2.
- **Export PDF sintetico** → Fase 2 (in Fase 1 la CTA è solo un rimando).
- **Dettaglio sottocategorie Pro + paywall** → Fase 3.
- **Invio lead / contatto professionista + pannello admin CRUD (listini, coefficienti, città, referenti, testi)** → Fase 4. In Fase 1 i valori sono seed, non editabili da UI.
- **Moltiplicatori prezzo per zona geografica** → fase 2 di prodotto (post-v1).
- **Conferma aliquota IVA Serramenti/Porte** → da chiarire con dati reali; per ora parametro admin con default 22%.

### Reviewed Todos (not folded)
Nessun todo pendente incrociato con questa fase.

</deferred>

---

*Phase: 1-Stima Free end-to-end*
*Context gathered: 2026-08-24*
