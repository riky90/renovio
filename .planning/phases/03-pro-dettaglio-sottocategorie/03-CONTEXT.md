# Phase 3: Pro & dettaglio sottocategorie - Context

**Gathered:** 2026-08-26
**Status:** Ready for planning

<domain>
## Phase Boundary

L'utente **Pro** sblocca, **dietro paywall**, l'apertura per **sottocategorie (a.1/a.2…) con voci e quantità stimate** dal motore parametrico bottom-up, e scarica un **PDF dettagliato** brandizzato. Requisiti in scope: **PRO-01** (Pro vede il dettaglio sottocategorie, Free no), **PRO-02** (dettaglio dietro paywall), **PRO-03** (gestione stato Pro sull'account), **PDF-02** (PDF Pro dettagliato).

**In scope:** motore parametrico Pro bottom-up sulle voci del computo; nuove tabelle/seed per sottocategorie/voci (prezzi RE); stato Pro come tessera abbonamento + attivazione stub "production-shaped"; paywall server-side; PDF Pro esteso.

**Non include:** pagamento reale / prezzo abbonamento definito (stub in v1); **upload Excel multi-città + CRUD admin** su listini/voci/coefficienti (→ Fase 4); lead/contatto professionista (→ Fase 4).
</domain>

<decisions>
## Implementation Decisions

### Motore Pro — bottom-up, NON riconcilia col Free
- **D-01:** Il dettaglio Pro è ricostruito **bottom-up** dalle voci del computo ed è una stima **più precisa** del Free. **Non deve riconciliare** con il totale di categoria della Fase 1: sono misure diverse, il Free è volutamente più grezzo, è accettabile e atteso che i due numeri differiscano. *(Questa decisione sostituisce il criterio di successo #2 originale della ROADMAP, riscritto di conseguenza in data 2026-08-26.)*
- **D-02:** **Fonte dati = i fogli di dettaglio dell'Excel** (`docs/computo-base-reggio-emilia.xlsx`), prezzi Reggio Emilia. Struttura non uniforme (vedi `docs/computo-struttura-dettaglio.md`):
  - **A-EDILE**: gerarchia a codici — 11 macro-sottocategorie (A.1 Demolizioni … A.11 Opere da pittore), 91 voci `X.n.m` con UM + prezzo unitario cliente; alcune voci con varianti a/b/c.
  - **B-FINITURE / C-SERRAMENTI / D-PRODOTTI**: **cataloghi piatti** di materiali/prodotti raggruppati per intestazione (no sotto-codici) — il "dettaglio" qui è *scelta prodotto + quantità*.
- **D-03:** I dati Pro vivono nello **stesso seed idempotente** (estensione di `backend/scripts/seed.py` + `docs/seed-coefficienti-base.json`), con nuove tabelle + nuova migrazione Alembic. Prezzi = RE; le altre città arriveranno via **upload admin** (Fase 4) sullo stesso schema.

### Quantità — approccio ibrido (le quantità NON sono nel file, vanno stimate)
- **D-04:** Nel computo la colonna **Qta è sempre 0** (si riempie per cantiere). I **prezzi unitari esistono già**; il motore Pro deve **stimare le quantità** da `(mq, tipo)`. Approccio scelto: **ibrido**.
  - **Base preimpostata (admin):** coefficienti *quantità-per-m²* per voce, editabili (Fase 4).
  - **+ poche domande mirate all'utente** solo sulle voci a conteggio ad alto impatto (es. numero bagni, numero porte, numero condizionatori) — il minimo che sposta davvero il conto.
- **D-05:** Regola dall'utente sulle unità di misura: dove **UM = mq il prezzo è al metro quadro** → quantità = *frazione dei mq dell'appartamento* (coefficiente per-m²). Le altre UM si gestiscono di conseguenza: `cad` (a pezzo) → conteggio (domanda mirata o preset per mq), `ml` (metro lineare) → proporzionale ai mq (proxy perimetro), `ac`/a corpo (forfait: allestimento cantiere, apertura varchi) → importo fisso o per tipo.

### Stato Pro & paywall (PRO-02 / PRO-03)
- **D-06:** Stato Pro modellato come **tessera abbonamento** (record subscription: stato + data scadenza *nullable*), **non** come semplice flag booleano — così i pagamenti/rinnovi futuri non richiedono migrazioni.
- **D-07:** Attivazione in v1: **flusso completo "production-shaped"** con step di pagamento **stub** (nessun addebito reale) che attiva la tessera. Obiettivo esplicito: in produzione basterà **accendere il pagamento reale**, tutto il resto è già pronto. L'admin può inoltre attivare Pro a mano.
- **D-08:** **Paywall lato server**: il dettaglio Pro è protetto sull'**endpoint** in base allo stato Pro dell'account, non solo nascosto nella UI (altrimenti un Free smaliziato aggira la schermata e prende gratis il prodotto a pagamento).

### PDF Pro (PDF-02)
- **D-09:** **Estensione del generatore PDF esistente** (WeasyPrint, `app/services/pdf_service.py`) con le sottocategorie/voci/quantità. Calcolo **on-demand dagli input dello snapshot** salvato (città, mq, tipo — conservati apposta in Fase 2, D-09) — non serve congelare un secondo snapshot. Output sempre a **range**, anti-leak.

### Regole di dominio (portate avanti — non ri-discusse)
- **D-10:** **Anti-leak esteso al Pro.** `coefficiente_impresa` / `base_eur_mq` / prezzi impresa / margini restano server-side e **non compaiono** in nessuna risposta API del dettaglio né nel PDF Pro. La colonna `J`=0.65 del computo (foglio `listini`) è margine interno.
- **D-11:** Output **sempre a range**, anche nel dettaglio Pro e nel PDF Pro.

### 🔒 Guardrail database (avvertimento esplicito dell'utente — BLOCCANTE)
- **D-12:** L'incidente della Fase 2 (STATE.md:51): un ciclo di migrazioni azzera `dev.db` e, se il seed idempotente non viene rieseguito, il motore risponde `NoResultFound`. Regole per Fase 3 **e fasi successive**:
  1. Ogni **nuova migrazione** della Fase 3 deve **preservare o rieseguire** il seed del listino (idempotente) — mai lasciare il DB senza listino di default.
  2. **Free e Pro leggono lo STESSO listino per città** (stessa fonte dati, stesso record `Listino`): non devono esistere due basi-prezzi divergenti. *(Nota: "stesso listino" ≠ "stessi totali" — vedi D-01: i totali possono differire perché il metodo di calcolo è diverso.)*
  3. Propagare il vincolo alla **Fase 4** (admin che edita listini/voci e carica altre città): ogni edit/upload deve restare idempotente e non azzerare i dati esistenti.

### Claude's Discretion
- Schema esatto delle nuove tabelle (sottocategoria / voce / coefficiente-quantità), purché estenda lo schema esistente `Listino`/`ListinoCategoria`/`Categoria` senza romperlo e resti predisposto al multi-città (Fase 4).
- Meccanica UI precisa del paywall e della schermata dettaglio (accordion per sottocategoria vs tabella), coerente coi componenti Fase 1 (`CategoryCard`, `TotalCard`).
- Scelta esatta di come rappresentare lo stub di pagamento (bottone/modale/pagina) e il record subscription, purché D-06/D-07 siano rispettati.
- Set esatto delle "domande mirate" sulle quantità (D-04) e dei coefficienti quantità-per-m² iniziali — proposta in planning/research, taratura successiva da admin.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Dominio e decisioni di progetto
- `CLAUDE.md` — regole di dominio non negoziabili (prezzo/coefficiente impresa mai esposto, output a range, città=listino, IVA, multi-referente).
- `.planning/PROJECT.md` — Core Value, Key Decisions (motore Ibrido C, Free=totali/Pro=sottocategorie).
- `.planning/REQUIREMENTS.md` — Fase 3 = PRO-01, PRO-02, PRO-03, PDF-02.
- `.planning/ROADMAP.md` — confini e success criteria Fase 3 (**criterio #2 riscritto il 2026-08-26**: dettaglio Pro bottom-up, indipendente dal totale Free).
- `.planning/phases/01-stima-free-end-to-end/01-CONTEXT.md` — motore Free, listino a livello categoria, anti-leak.
- `.planning/phases/02-account-pdf/02-CONTEXT.md` — **D-09 (snapshot congela anche gli input, apposta per l'upgrade Pro)**, D-11 (PDF server-side riusabile per il Pro).

### Fonte dati Pro (NUOVO — leggere prima di modellare il motore)
- `docs/computo-struttura-dettaglio.md` — **mappa della struttura dei fogli di dettaglio** (gerarchia A-EDILE, cataloghi B/C/D, quantità=0, UM, coeff. impresa). Punto di partenza obbligato per il motore Pro.
- `docs/computo-base-reggio-emilia.xlsx` — sorgente reale (fogli `A-EDILE`, `B-FINITURE`, `C- SERRAMENTI PORTE `, `D- PRODOTTI`, `listini`).
- `docs/seed-coefficienti-base.json` — seed attuale (livello categoria) da **estendere** con i dati Pro.

### Codice esistente da integrare
- `backend/app/models/listino.py`, `backend/app/models/catalogo.py` — schema da estendere (sottocategorie/voci); NON esiste ancora dato sub-categoria.
- `backend/app/services/estimation.py` — motore Free (`EstimationService.compute`), riferimento per il pattern del motore Pro (Decimal puro, anti-leak, range).
- `backend/scripts/seed.py` — seed idempotente da estendere (upsert per chiave naturale).
- `backend/app/models/user.py`, `backend/app/models/stima_salvata.py` — user (per stato Pro/subscription) e snapshot salvato (input conservati per l'upgrade on-demand).
- `backend/app/services/pdf_service.py` + `backend/app/templates/pdf_stima.html` — generatore PDF da estendere per il Pro.
- `backend/alembic/versions/0003_stima_salvata.py` — ultima migrazione (catena 0001→0002→0003); la migrazione Fase 3 parte da qui.
- `frontend/src/components/SoftWallCta.tsx`, `frontend/src/pages/EstimatePage.tsx`, `frontend/src/pages/LeMieStimePage.tsx` — punti d'innesto per "Passa a Pro", schermata dettaglio, download PDF Pro.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Motore Free** (`EstimationService`): pattern Decimal puro + anti-leak a campi chiusi + output a range da replicare nel motore Pro.
- **Seed idempotente** (`seed.py`, upsert per chiave naturale): da estendere, non duplicare, con i dati sottocategorie/voci.
- **Generatore PDF** (`pdf_service.py`, WeasyPrint lazy import per il limite GTK3 Windows): da estendere con la sezione dettaglio.
- **Snapshot con input conservati** (`stima_salvata.risultato_json` + colonne scalari `citta/mq/tipo`): abilita il calcolo Pro on-demand senza ri-chiedere gli input (D-09 Fase 2).
- **Guard/sessione** (`get_current_user`, `require_admin`, cookie httpOnly): base per il gate paywall server-side.

### Established Patterns
- **Anti-leak con schemi a campi chiusi** (mai `model_validate` su ORM verso il client) — obbligatorio anche per il dettaglio Pro e il PDF Pro.
- **Prezzi/coefficienti in DB via seed** (ENG-02) — i coefficienti quantità-per-m² del Pro seguono la stessa regola (in DB, non nel codice, editabili in Fase 4).
- **Migrazione Alembic + seed idempotente**: attenzione al ciclo di vita che ha causato l'incidente Fase 2 (D-12).

### Integration Points
- Nuove tabelle sottocategoria/voce/coefficiente-quantità + migrazione sopra `0003`.
- Record **subscription/stato Pro** collegato a `user`; endpoint dettaglio protetto dal gate Pro.
- Endpoint dettaglio Pro che calcola on-demand dagli input dello snapshot; PDF Pro che consuma lo stesso calcolo.
- Predisposizione multi-città per l'upload admin (Fase 4).

</code_context>

<specifics>
## Specific Ideas

- **"Production-shaped stub":** costruire l'intero flusso di attivazione Pro come se il pagamento fosse reale, con lo step di pagamento come stub — in produzione si accende solo il pagamento vero.
- **Regola UM=mq → prezzo al m²** (dall'utente): la quantità delle voci in mq è una frazione dei mq dell'appartamento.
- Il Pro è **volutamente scollegato** dal numero Free: "più preciso" è il messaggio di valore del passaggio a Pro.
- Solo **A-EDILE** ha la struttura a sotto-codici pulita; per Finiture/Serramenti/Prodotti il "dettaglio" è selezione da catalogo — il motore deve gestire due forme diverse.

</specifics>

<deferred>
## Deferred Ideas

- **Pagamento reale + prezzo abbonamento Pro definito** → post-v1 (in v1 solo lo stub production-shaped).
- **Upload Excel multi-città + CRUD admin** su listini/voci/coefficienti/quantità → Fase 4 (in Fase 3 solo seed RE).
- **Taratura fine dei coefficienti quantità-per-m²** e del set di domande mirate → iterazione post-lancio via pannello admin (Fase 4).
- **Lead / contatto professionista dal livello Pro** → Fase 4.

### Reviewed Todos (not folded)
None — discussione rimasta nello scope della fase.

</deferred>

---

*Phase: 3-Pro & dettaglio sottocategorie*
*Context gathered: 2026-08-26*
