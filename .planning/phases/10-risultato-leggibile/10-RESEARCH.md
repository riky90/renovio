# Phase 10: Risultato leggibile e tetto di budget - Research

**Researched:** 2026-09-29
**Domain:** presentazione del risultato (React + Tailwind 4 + shadcn) e un parametro utente nuovo (budget) su FastAPI/SQLAlchemy/Alembic/Jinja+WeasyPrint. Nessuna libreria nuova.
**Confidence:** HIGH sul codice esistente (letto in questa sessione); MEDIUM sulle scelte di progetto marcate `[ASSUMED]` (vedi Assumptions Log).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Ereditate (non si ridiscutono)**
- Output sempre a range; mai prezzo o coefficiente impresa verso il client o nel PDF (`test_no_leak.py`, `test_no_leak_admin.py` su ogni endpoint e schema nuovo o toccato).
- **Il budget non muove il prezzo** (criterio 5 della roadmap, REQUIREMENTS §v3): due assi distinti, *finiture* muove il numero, *budget* no.
- L'arredo sta **accanto** al totale, non dentro (`ArredoOut`).
- Prezzi e coefficienti in database: nessuna soglia o percentuale del confronto cablata come prezzo nel codice.
- Snapshot congelato: cio' che il PDF e "Le mie stime" mostrano viene da `risultato_json`. Le stime salvate prima di questa fase non hanno budget: nessun avviso, nessun errore.

**Raccolta del budget**
- **D-01:** Il budget e' una **domanda del wizard nello step 3 "La ristrutturazione"**, con testo "Qual e' il tuo budget per la ristrutturazione?": l'utente scrive la cifra che ha in mente.
- **D-02:** **Facoltativo.** Senza budget non compare nessun avviso e nessuna tacca sulla barra.
- **D-03:** **Importo libero in euro, IVA inclusa**, confrontato con il totale IVA inclusa.
- **D-04:** **Salvato con la stima e riportato nel PDF** (Free e Pro): riaprendo da "Le mie stime" l'avviso e' ancora li'.
- **D-05:** Il budget si puo' **cambiare dalla pagina risultato**, con un campo nel box dell'avviso: l'avviso si ricalcola subito e il valore nuovo si salva sulla stima. Il prezzo non cambia.

**Avviso di sforamento**
- **D-06:** Tre stati rispetto al range del totale lavori: budget **sotto il minimo** -> avviso "fuori budget" con il confronto (D-07); budget **dentro il range** -> nota morbida "al limite: dipende dalle scelte"; budget **sopra il massimo** -> conferma positiva.
- **D-07:** Il confronto si ricalcola **un livello sotto** quello scelto (alte->medie, medie->economiche), mostrando il nuovo range e la differenza. Con finiture gia' economiche non c'e' confronto: l'avviso dice che per rientrare nel budget servono meno lavori.
- **D-08:** Il budget si confronta con il **solo totale lavori**, senza l'arredo.
- **D-09:** Il confronto e' un **ricalcolo vero lato server** con il livello inferiore, non una stima proporzionale lato client.
- **D-10:** L'avviso vale **anche nel dettaglio Pro**: stesso comportamento, con il confronto ricalcolato sull'asse `finitura` del motore Pro (un livello sotto l'opzione scelta in "Affina la stima").

**Barra proporzionale (RIS-01)**
- **D-11:** La `RangeBar` del totale si disegna **su un asse da 0 a un tetto** (circa 1,2 volte il massimo, oppure il budget se piu' alto): il segmento colorato e' largo quanto l'incertezza reale.
- **D-12:** Se il budget e' dichiarato, compare sulla barra una **tacca verticale "Il tuo budget"**.
- **D-13:** Nelle card di categoria non c'e' una RangeBar, ma una **mini-barra orizzontale del peso %** della categoria sul totale.

**Card e riepilogo (RIS-02, RIS-03)**
- **D-14:** Incidenza €/m² per categoria **a range e su imponibile** (IVA esclusa), es. "310–380 €/m²", sui m² calpestabili della stima.
- **D-15:** Il peso relativo della categoria e' **un solo numero sul valore medio** (es. "34%").
- **D-16:** Il riepilogo **imponibile / IVA / extra** sta **dentro la `TotalCard`, sotto il totale**: imponibile lavori, IVA divisa per aliquota (10% / 22%), extra, totale. Sostituisce la lista degli extra oggi separata in `EstimatePage` e `SavedEstimateDetail`.
- **D-17:** Tutto questo (€/m², peso, riepilogo, budget e avviso) va **anche nei PDF** `pdf_stima.html` e `pdf_stima_pro.html`, con la barra statica.

### Claude's Discretion
- Forma tecnica del budget: nuovo `tipo_controllo` di catalogo (es. `importo`) o campo dedicato di `StimaInput` fuori dal catalogo, e dove persisterlo (colonna su `stima` o dentro `risultato_json`), purche' D-01..D-05 reggano e il budget resti fuori dal calcolo del prezzo.
- Forma dell'endpoint del confronto (campo calcolato nella risposta della stima o endpoint a parte) e come il campo di D-05 salva il budget sulla stima.
- Arrotondamento del tetto della scala (D-11), testi esatti dell'avviso, layout su mobile.
- Come si calcola l'IVA per aliquota nel riepilogo (raggruppando `CategoriaOut.iva_pct`).

### Deferred Ideas (OUT OF SCOPE)
- Nessuna idea fuori perimetro emersa. Restano nel backlog v3 i punti gia' noti in REQUIREMENTS §"v3 / Deferred".
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RIS-01 | `RangeBar` proporzionale ai valori reali | §Pattern 1 (geometria pura `scalaBarra`), tetto e larghezza minima; stessa funzione mirror in Python per il PDF |
| RIS-02 | Incidenza €/m² per categoria e peso relativo | §Pattern 2: derivati da `CategoriaOut` + `input.mq`, calcolati lato client (servono anche agli snapshot vecchi) e in un modulo Python per il PDF |
| RIS-03 | Riepilogo imponibile / IVA / extra | §Pattern 3: raggruppo `CategoriaOut.iva_pct`; riconciliazione con `TotaleOut.iva_*` con la riga IVA "ultima" che assorbe l'arrotondamento |
| RIS-04 | Avviso superamento budget con confronto a finiture inferiori | §Pattern 4-6: budget = colonna su `stima` fuori dal motore; `confronto_finiture` calcolato server-side alla creazione (indipendente dal budget); PUT budget; Pro con base IVA-inclusa |
</phase_requirements>

## Summary

La fase e' per l'80% presentazione, ma ha **un punto architetturale vero**: il budget. Il codice oggi non lo conosce (nessuna domanda, nessun campo, nessuna colonna) e va introdotto senza che possa toccare il prezzo. La scelta che regge tutte le decisioni D-01..D-10 e il vincolo dello snapshot congelato e': **il budget e' un parametro utente fuori dal catalogo domande e fuori da `risposte`**, persistito in una **colonna nullable `budget_eur` su `stima`** (come `risposte_pro_json`/`livelli_pro_json`: parametri di ricalcolo, non risultato). Il **confronto a finiture inferiori non dipende dal budget** (e' "il totale con un livello sotto"), quindi si calcola **una volta sola, lato server, in `POST /stima`**, e viaggia congelato nello snapshot. Lo stato dell'avviso (fuori / al limite / dentro) e' un semplice confronto tra `budget_eur` e il range gia' calcolato. Conseguenze: cambiare il budget dalla pagina risultato (D-05) e' un `PUT` che scrive una colonna, senza ricalcoli; il PDF Free resta letto dallo snapshot (nessun motore nel PDF, contratto di `pdf_service.py`); "il budget non muove il prezzo" e' vero per costruzione (il campo non entra mai in `EstimationService`).

Il secondo punto delicato e' il **Pro** (D-10): `DettaglioProService` non modella IVA ne' extra (somma prezzi voce a prezzo cliente, tutte le categorie) mentre il budget e' IVA inclusa. Confrontare il budget con il totale Pro "cosi' com'e'" darebbe un avviso sbagliato. Va calcolata lato server una versione IVA-inclusa del totale Pro (per categoria con `Categoria.iva_pct`, piu' gli extra come nel Free) e usata sia per lo stato sia per il confronto (ricalcolo con `livelli` un livello sotto per ogni categoria). E' la parte da confermare con l'utente (A2).

Il resto e' aritmetica pura e ben delimitata: geometria della barra (tetto, percentuali, larghezza minima), €/m² su imponibile, peso su valore medio, IVA per aliquota. Va in funzioni pure testabili (Python per pytest e per il PDF; TypeScript in `lib/` per il web). Trappola ricorrente del repo: `normalizeResponse()` in `frontend/src/api/stima.ts` ricostruisce l'oggetto campo per campo e **scarta in silenzio** tutto cio' che non elenca (e' successo con `bonus`): ogni campo nuovo va aggiunto li', altrimenti sparisce dallo snapshot.

**Primary recommendation:** colonna `budget_eur` (migrazione 0024, additiva) + `confronto_finiture` in `StimaResponse` calcolato in `POST /stima` con `livello_finiture` un gradino sotto (ordine da `opzione_domanda.ordine`) + `PUT /me/stime/{id}/budget`; per il Pro calcolare server-side totale e confronto IVA-inclusi nel `DettaglioProOut`; derivati di presentazione (barra, €/m², peso, IVA per aliquota) in funzioni pure, duplicate in Python per il PDF con gli stessi vettori di test.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Geometria proporzionale RangeBar (tetto, %, tacca) | Browser / Client | API (PDF: Python) | Puro layout; nessun prezzo nuovo. Nel PDF la stessa geometria si calcola server-side (nessun JS) |
| Incidenza €/m², peso %, IVA per aliquota | Browser / Client | API (PDF) | Derivati da campi gia' nello snapshot; devono funzionare anche sugli snapshot pre-fase (che non hanno campi nuovi) |
| Confronto a finiture inferiori (Free) | API / Backend | — | D-09: ricalcolo vero col motore, mai proporzione lato client. Fatto in `POST /stima`, congelato nello snapshot |
| Confronto a finiture inferiori (Pro) | API / Backend | — | Motore Pro (`DettaglioProService`) con `livelli` inferiori; IVA inclusa calcolata server-side |
| Stato dell'avviso (fuori/limite/dentro) | Browser / Client | — | Confronto di un intero utente con un range gia' calcolato: nessuna stima di prezzo |
| Persistenza budget | Database / Storage | API | Colonna `stima.budget_eur`; `PUT` con ownership 404 (anti-IDOR) |
| Raccolta budget nel wizard / modifica nell'avviso | Browser / Client | API | `ImportoField`; validazione autoritativa lato server (Pydantic bounds) |
| Render PDF budget/avviso | API / Backend | — | `PdfService` legge snapshot + colonna; Pro `render_pro` resta LIVE |

## Standard Stack

Nessuna dipendenza nuova (UI-SPEC: "Nessuna nuova dipendenza, nessun `npx shadcn add`"). Tutto quello che serve e' gia' nel repo:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI + Pydantic v2 | gia' installati | `PUT budget`, campi nuovi negli schemi | Pattern del repo: DTO chiusi, mapping campo-per-campo [VERIFIED: codebase grep `routers/stima.py`] |
| SQLAlchemy + Alembic | gia' installati | colonna `budget_eur`, migrazione 0024 | Ultima migrazione = 0023 [VERIFIED: `backend/alembic/versions`] |
| Jinja2 + WeasyPrint | gia' installati | PDF con barra statica a `div` percentuali | Gia' in uso in `pdf_service.py` [VERIFIED: codebase] |
| React 19 + Tailwind 4 + shadcn (`Alert`, `Input`, `InputGroup`, `Separator`, `Label`, `Button`) | gia' installati | `BudgetAlert`, `ImportoField`, riepilogo | UI-SPEC [CITED: 10-UI-SPEC.md] |
| `@tanstack/react-query` | ^5.102 (gia' in `package.json`) | mutation `PUT budget`, invalidazione dettaglio Pro | Pattern di `EstimatePage` [VERIFIED: codebase] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Budget come campo dedicato | Nuovo `tipo_controllo` `importo` nel catalogo | Il catalogo alimenta il **layer effetti** (`risposte`, `ValoreRisposta` limitato a `int <= 10_000`, effetti validati da `valida_effetto`): far passare il budget da li' lo mette nella stessa pipeline che muove il prezzo, e richiede tipo di controllo nuovo in `CONTROLLI`, `DomandaField`, `catalogo_domande`, import/export Excel (08.1). Piu' superficie, e il rischio (budget che muove il prezzo) diventa un errore di configurazione possibile. **Scartato** (A1: il testo della domanda resta stringa fissa, come consente UI-SPEC riga "Domanda wizard") |
| Budget dentro `risultato_json` | Colonna dedicata | Lo snapshot e' "scritto UNA volta, mai ricalcolato" (`models/stima_salvata.py`): D-05 (modifica dalla pagina risultato) lo violerebbe. Colonna = stesso trattamento di `risposte_pro_json` |

**Installation:** nessuna. Migrazione: `alembic revision -m "budget_eur su stima"` (scritta a mano, additiva).

## Package Legitimacy Audit

Nessun pacchetto esterno nuovo in questa fase. Audit non applicabile (slopcheck non eseguito perche' non c'e' nulla da installare).

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
WIZARD (step 3)                                   PAGINA RISULTATO (Free / Salvata / Pro)
 ImportoField --budget (client state)--+
 livello_finiture (risposte) ----------+--> POST /stima {citta,mq,tipo,risposte}
                                             |  (budget NON parte qui: non serve al calcolo)
                                             v
                                   EstimationService.compute(risposte)   -> totale, categorie, extra
                                   EstimationService.compute(risposte con livello_finiture = livello-1)
                                             |         (solo se esiste livello inferiore e delta>0)
                                             v
                                   StimaResponse { ..., confronto_finiture | null }
                                             |
                    +------------------------+-----------------------------+
                    v                                                      v
        anonimo: stato in memoria                              loggato: POST /me/stime
        (pendingStima = result + budget_eur                     {…StimaResponse, budget_eur}
         attraversa login/registrazione)                        -> risultato_json (congelato, con confronto)
                                                                -> colonna stima.budget_eur (modificabile)
                    |                                                      |
                    v                                                      v
   BudgetAlert: stato = f(budget_eur, totale.min/max)          PUT /me/stime/{id}/budget {budget_eur|null}
   ("Aggiorna il confronto" = cambia solo budget_eur;           (ownership 404, bounds Pydantic)
    il confronto e' gia' nello snapshot)                                  |
                    |                                                      v
                    +----------------------> PdfService.render(row, user): snapshot + row.budget_eur
                                             render_pro(): DettaglioProService LIVE + budget_eur + confronto Pro live

PRO: GET dettaglio-pro -> _compute_dettaglio (unico punto) -> DettaglioProService.compute(livelli scelti)
                                                           -> DettaglioProService.compute(livelli - 1 per categoria)
     -> DettaglioProOut { …, totale_ivato_min/max, confronto_finiture, budget_eur }   (IVA per categoria + extra, server-side)
```

### Recommended Project Structure
```
backend/app/
├── models/stima_salvata.py        # + budget_eur (Integer, nullable)
├── alembic/versions/0024_budget_eur_su_stima.py
├── schemas/stima.py               # + ConfrontoFinitureOut, StimaResponse.confronto_finiture
├── schemas/stima_salvata.py       # + StimaSalvataCreate.budget_eur, StimaSalvataOut.budget_eur, BudgetIn/Out
├── schemas/dettaglio_pro.py       # + totale_ivato_*, confronto_finiture, budget_eur
├── services/risultato.py          # NUOVO: funzioni pure (livello_inferiore, scala_barra, incidenza, peso, iva_per_aliquota, stato_budget)
├── services/estimation.py         # invariato (il confronto lo orchestra il router chiamando compute due volte)
├── routers/stima.py               # calcolo confronto_finiture
├── routers/stime_salvate.py       # salva budget_eur; PUT /stime/{id}/budget; dettaglio_stima ricostruisce confronto
├── routers/dettaglio_pro.py       # _compute_dettaglio esteso (confronto Pro + IVA)
├── services/pdf_service.py        # passa budget e derivati ai template
└── templates/pdf_stima.html, pdf_stima_pro.html
frontend/src/
├── lib/risultato.ts               # NUOVO: scalaBarra, incidenzaEurMq, pesoPct, ivaPerAliquota, statoBudget (+ formato tetto)
├── components/RangeBar.tsx, TotalCard.tsx, CategoryCard.tsx (modificati)
├── components/BudgetAlert.tsx, ImportoField.tsx (nuovi)
├── api/stima.ts                   # normalizeResponse: + confronto_finiture; PUT budget
└── pages/EstimatePage.tsx, components/SavedEstimateDetail.tsx, pages/DettaglioProPage.tsx, components/EstimateWizard.tsx
```

### Pattern 1: Geometria della barra (RIS-01, D-11/12)
**What:** funzione pura `scalaBarra(min, max, budget?) -> { tetto, leftPct, rightPct, budgetPct }`.
- `tetto = roundUp(max(1.2 * max, budget ?? 0))`; arrotondamento per eccesso al migliaio sotto 100.000, alle 5.000 sopra (UI-SPEC A.1, a discrezione ma tetto >= max sempre).
- `leftPct = min/tetto*100`, `rightPct = max/tetto*100`; se `rightPct - leftPct < 4`, allarga simmetricamente attorno al centro a 4 punti (clamp 0..100).
- `budgetPct = budget/tetto*100` (con budget > tetto il tetto sale a budget, quindi <= 100).
- Verifica di RIS-01: min/max con ±10% e ±20% sullo stesso centro producono `rightPct-leftPct` diversi. Con tetto = 1.2*max la larghezza e' ~ (2r/(1+r))/1.2 (r = 0.10 -> ~15%, r = 0.20 -> ~28%): distinguibili a occhio [derivato dalla formula, verificabile con test].
**Example:**
```typescript
// frontend/src/lib/risultato.ts (derivato da 10-UI-SPEC §A)
export function scalaBarra(min: number, max: number, budget?: number | null) {
  const grezzo = Math.max(1.2 * max, budget ?? 0);
  const passo = grezzo < 100_000 ? 1_000 : 5_000;
  const tetto = Math.ceil(grezzo / passo) * passo;
  let left = (min / tetto) * 100;
  let right = (max / tetto) * 100;
  if (right - left < 4) {
    const c = (left + right) / 2;
    left = Math.max(0, c - 2);
    right = Math.min(100, c + 2);
  }
  return { tetto, left, right, budgetPct: budget ? (budget / tetto) * 100 : null };
}
```
`RangeBar` prende `min`, `max`, `budget?`; i pallini stanno a `left%` / `right%` (sostituiscono `left-[12%]`/`right-[12%]`), la tacca a `budgetPct%`. Etichetta "Il tuo budget" con clamp ai bordi (es. `left: clamp(0%, budgetPct%, 100%)` con `translate-x` dinamico o `transform` condizionato: se `budgetPct < 15` allinea a sinistra, se `> 85` a destra). La barra non deve piu' avere il caso "legacy senza min/max": migrare tutti i chiamanti (solo `TotalCard`).

### Pattern 2: Incidenza e peso (RIS-02, D-14/15)
- Incidenza: `imponibile_min / mq` – `imponibile_max / mq`, arrotondati all'euro (`Math.round`), `mq = input.mq` ("calpestabili": e' l'unico mq della stima [VERIFIED: `StimaRequest.mq`]). Nota: SavedEstimateDetail ha `stima.input.mq`; `CategoryCard` deve ricevere `mq` e `totaleLavoriMedio` come props nuove (oggi riceve solo `categoria`).
- Peso: `round(((cat.min+cat.max)/2) / somma_categorie(medio) * 100)`. **Denominatore = somma dei medi delle categorie** (senza extra e senza arredo), non `totale.totale_*` che contiene gli extra fissi: cosi' i pesi delle card sommano ~100. UI-SPEC dice "sul totale lavori (senza arredo)": questa lettura la rispetta (A3). `< 1%` -> testo "<1%" e fill 2%.
- Tutti i numeri finiscono in cifre a `tabular-nums`; `formatEurRange` produce "310 € – 380 €": per "€/m²" serve un formatter dedicato (es. `formatRangeEurMq(min,max)` -> "310–380 €/m²") in `lib/currency.ts`, non una concatenazione ad hoc.

### Pattern 3: Riepilogo imponibile / IVA / extra (RIS-03, D-16)
- Dati gia' nello snapshot: `totale.imponibile_min/max` (include extra), `totale.iva_min/max`, `categorie[].iva_pct/iva_min/iva_max`, `extra[].importo/iva_pct` [VERIFIED: `routers/stima.py`].
- Attenzione: `TotaleOut.imponibile_*` **include gli extra**, ma D-16 vuole "Imponibile lavori" separato da "Costi extra". Imponibile lavori = `somma(categorie[].imponibile_*)` (non `totale.imponibile_*`); extra = `somma(extra[].importo)`.
- IVA per aliquota: raggruppa `categorie` per `iva_pct` sommando `iva_min/iva_max`; per gli extra aggiungi `importo * iva_pct` all'aliquota di ciascuno. **Riconciliazione:** il server calcola l'IVA extra dal lordo arrotondato (`ex.totale - ex.importo`), quindi `importo*iva_pct` puo' differire di 1 €. Regola: l'ultima riga IVA (aliquota piu' alta) e' `totale.iva_* - somma(altre righe)`, cosi' le righe sommano esattamente al totale mostrato (in caso contrario "Totale IVA inclusa" non torna con imponibile + IVA + extra). Nota: se gli extra sono esposti come "importo" (imponibile) e le righe IVA li includono, il totale = imponibile lavori + extra + IVA totale [ricavato da `_split_imponibile_iva`/`totale_out`].
- Le aliquote presenti sono dati (`iva_pct`), mai un elenco 10/22 cablato. Formato "IVA 10%": `Math.round(iva_pct*100)`.
- Elimina il blocco extra separato in `EstimatePage.tsx` (~riga 249) e `SavedEstimateDetail.tsx`; ordine dell'`EstimatePage` oggi e' categorie -> extra -> `TotalCard`: UI-SPEC §E vuole `TotalCard` -> `BudgetAlert` -> categorie. **Va riordinato**, non solo modificato.

### Pattern 4: Budget - modello e persistenza (RIS-04, D-01..D-05) [ASSUMED A1]
- `StimaSalvata.budget_eur: Mapped[int | None] = mapped_column(Integer, nullable=True)` + migrazione 0024 `op.add_column` nullable (regola additiva SQLite, D-24 citata nel modello). Intero in euro: D-03 "importo libero in euro"; UI-SPEC: intero positivo max 9 cifre.
- Validazione: `budget_eur: int | None = Field(default=None, ge=1, le=999_999_999)` (ASVS V5, stesso criterio di `mq`). Niente float, niente Decimal.
- **Non** entra in `StimaRequest` ne' in `risposte`: `EstimationService` non lo vede mai -> criterio 5 vero per costruzione. Test: stessa richiesta, `POST /stima` identico con/senza budget e `salva` con budget non cambia `totale_min/max`.
- `StimaSalvataCreate` (mirror di `StimaResponse` + `preferenze_pro`) guadagna `budget_eur: int | None = None`. **Trappola dello snapshot:** `salva_stima` fa `payload.model_dump(...)` e lo congela in `risultato_json`; per il budget serve `exclude={"preferenze_pro", "budget_eur"}` (parametro, non risultato: se restasse nello snapshot ci sarebbero due verita' dopo un `PUT`). `confronto_finiture` invece **resta** nello snapshot (e' risultato).
- `PUT /api/v1/me/stime/{id}/budget` body `{budget_eur: int | null}`, `Depends(get_current_user)` (non `require_pro`: vale anche per Free), stesso `select(...).where(id, user_id)` con **404** se non e' dell'utente (anti-IDOR, come `dettaglio_stima`). Risposta `{budget_eur}`. Nome/metodo a discrezione; `PUT` (idempotente, sostituisce) e' coerente.
- `StimaSalvataOut` e `dettaglio_stima` (ricostruzione manuale campo-per-campo) aggiungono `budget_eur=row.budget_eur` e `confronto_finiture=snapshot.get("confronto_finiture")` con `.get()` (gli snapshot pre-fase non hanno la chiave: un `KeyError` romperebbe tutto lo storico, commento gia' presente nel router).
- Anonimo: il budget vive nello stato React; `SoftWallCta` passa `{ pendingStima: result }` in `location.state` a `/registrati`/`/accedi`, che chiamano `postSalvaStima(pendingStima)`. Perche' il budget sopravviva, il valore va **dentro l'oggetto** passato (`{...result, budget_eur}`) e `postSalvaStima` lo inoltra. `StimaResponse` (TS) puo' guadagnare `budget_eur?: number | null` **solo lato client**; `normalizeResponse` non lo produce (il server non lo restituisce da `POST /stima`).

### Pattern 5: Confronto a finiture inferiori - Free (D-07, D-09)
- In `crea_stima`, dopo il calcolo principale: se `payload.risposte is not None` e c'e' un livello inferiore, richiama `EstimationService.compute(session, listino, mq, tipo, risposte={**risposte, "livello_finiture": livello_inferiore})` e costruisce `ConfrontoFinitureOut(livello_code, livello_nome, totale_min, totale_max)`. Nessuna modifica a `EstimationService` (oracolo 85 mq -> 47.985-70.575 intatto).
- **Livello scelto:** `risposte.get("livello_finiture")` oppure l'opzione `is_default` della domanda. **Livello inferiore:** opzione attiva con `ordine` immediatamente minore nella stessa domanda (`OpzioneDomanda.ordine`, dati DB: base=1, medio=2, alto=3 [VERIFIED: `seed-domande.json` riga ~1414]). Niente lista `["base","medio","alto"]` nel codice (regola 3). Costante per convenzione `DOMANDA_LIVELLO_FINITURE = "livello_finiture"` in `services/effetti.py` accanto a `DOMANDA_FINITURA`.
- `confronto_finiture = None` quando: `risposte is None` (layer spento), gia' al livello piu' basso (D-07, testo "meno lavori"), domanda/opzione mancante, **oppure quando `confronto.totale_max >= totale.totale_max`** (es. l'utente ha escluso serramenti/finiture con `non_rifare`, i moltiplicatori di finitura non spostano nulla: mostrare "costerebbe X, Y in meno" con delta <= 0 sarebbe falso). Mai zero, mai negativo (regola "sezioni opzionali `None`").
- Delta: `ora.min - conf.min` e `ora.max - conf.max` (range di risparmio); e' aritmetica di presentazione. Se `delta_min > delta_max` scambia; se entrambi <= 0 non mostrare.
- Costo: una `compute` in piu' per richiesta (solo quando serve). Endpoint limitato `20/minute` [VERIFIED: `@limiter.limit`]; accettabile.
- Arredo: il livello di finiture governa anche il forfait arredo (`ArredoService`, stesso `livello_finiture`): il confronto guarda **solo** `EstimationService` (totale lavori), l'arredo non si tocca (D-08).

### Pattern 6: Pro (D-10) [ASSUMED A2 — da confermare]
- `DettaglioProService.compute(...)` somma **tutte** le categorie con voci a prezzo cliente, senza IVA e senza extra [VERIFIED: `services/dettaglio_pro.py`, nessuna occorrenza di IVA]; il commento di `DettaglioProPage` lo dice ("il Pro non modella l'IVA"). Il budget e' IVA inclusa. Quindi l'alert Pro non puo' usare `DettaglioProOut.totale_*`.
- Proposta: in `_compute_dettaglio` (unico punto condiviso da GET, POST risposte e PDF, per parita' by-construction) calcola `totale_ivato = sum(cat.totale * (1 + Categoria.iva_pct))` sulle sole categorie con `nel_totale_lavori=True`, **piu' gli extra attivi** lordi come nel Free (cosi' Free e Pro sono confrontabili con lo stesso budget), a range. Aggiungi a `DettaglioProOut`: `totale_ivato_min/max`, `budget_eur` (da `row.budget_eur`), `confronto_finiture` (Pro).
- Confronto Pro: per ogni categoria con `livello_scelto` calcola il livello inferiore (ordine da `LivelloFinitura.ordine`, tabella DB), ricomponi `livelli` (e `risposte_motore["finitura"]` se il default e' su `finitura`) e richiama `DettaglioProService.compute` una seconda volta. Se nessuna categoria ha un livello inferiore -> `None` (stato "meno lavori"). Il cambio livello Pro avviene per categoria (`livelli_pro_json`), quindi "un livello sotto quello scelto" e' per categoria: documentarlo nel testo dell'avviso non serve (mostra solo il nome del livello: con livelli misti usa l'etichetta del livello della categoria con `livello_scelto` piu' alto / o "un livello in meno" – A4).
- **Categorie non nel totale lavori:** oggi il ciclo Pro non filtra `nel_totale_lavori` (E-ARREDO viene scartata solo perche' non ha sottocategorie). Nel calcolo IVA-inclusa Pro filtra esplicitamente `nel_totale_lavori=True`, cosi' l'arredo non entra mai nel confronto (D-08) quando arriveranno le sue voci.
- Costo: `compute` Pro fa query per voce (N+1) e ora gira 2 volte per richiesta di GET/POST/PDF. Accettabile per volumi attuali; segnalato come rischio prestazionale.
- PDF Pro (`render_pro`, LIVE per design, non riformare): il router passa gia' `DettaglioProResult`; aggiungere `budget_eur` e `confronto` calcolati nello stesso `_compute_dettaglio`. `PdfService.render_pro` non deve chiamare il motore.

### Pattern 7: PDF (D-17)
- Barra statica: `div` con `width`/`left` in `%` calcolati **in Python** (`services/risultato.py::scala_barra`, stesso algoritmo del TS) e passati al template; niente JS, niente ombre; WeasyPrint gestisce `position:absolute` in un contenitore `position:relative` e `linear-gradient` semplici [ASSUMED: verificare col rendering reale, vedi Pitfall 6; gia' esistono barre/box nel template]. 
- Riepilogo, €/m², peso, riquadro budget si scrivono con gli stessi derivati (funzioni Python) sul solo snapshot + `row.budget_eur`. Nessun budget -> la sezione non viene emessa (`{% if budget %}`).
- `PdfService.render(stima, user)` riceve la riga: aggiungere `budget_eur=stima.budget_eur` e i derivati al `template.render(...)`. Non importare il motore (contratto del modulo).
- Il testo dell'avviso (titolo/corpo per stato) va definito in un posto: i template Jinja non possono importare TS. Tenere le stringhe in `services/risultato.py` (dict per stato) e nel componente TS, con test di parita' su un vettore di casi. [ASSUMED A5: duplicazione accettata; alternativa "testi da DB" (`testo_service`/`get_testo`) e' possibile ma allarga la fase]

### Anti-Patterns to Avoid
- **Budget dentro `risposte`/catalogo:** lo mette nella pipeline effetti e nei limiti `ValoreRisposta <= 10_000` (budget 40.000 verrebbe rifiutato con 422).
- **Ricalcolo proporzionale lato client** del confronto (vietato da D-09).
- **Riordinare a mano i livelli** in una lista cablata: usare `ordine` da DB.
- **Passare `totale.imponibile_*` come "imponibile lavori":** include gli extra (v. Pattern 3).
- **Usare `formatEurRange` per "€/m²"** (produce "min € – max €").
- **`model_dump` dello snapshot con `budget_eur` dentro** (due verita').
- **Aggiungere un campo a `StimaResponse` senza aggiornare `normalizeResponse`** (sparisce dallo snapshot in silenzio).
- **Rosso per il "fuori budget":** UI-SPEC vieta il destructive (solo errore di input).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Contenitore avviso | un `div` con classi custom | `Alert` shadcn con classi `bg-amber-bg border-amber-border text-amber-fg` (token gia' in `index.css`) | Token e accessibilita' esistenti; `role` corretto (`status`, non `alert`, per UI-SPEC) |
| Campo importo con suffisso | input + span posizionato | `InputGroup` shadcn (gia' in `components/ui`) | Focus ring e altezza coerenti |
| Formattazione migliaia it-IT | regex sulle stringhe | `Intl.NumberFormat("it-IT")` come `lib/currency.ts` (attenzione a `useGrouping: "always"`, gia' gestito li) | Sotto 10.000 il locale non raggruppa senza `always` |
| Parsing importo incollato | replace ad hoc | una funzione `parseImporto(str) -> number | null` che tolga `.`/spazi/`€` e accetti solo cifre, testata | Punti/spazi incollati sono il caso reale |
| Ordine dei livelli | lista `base/medio/alto` | `OpzioneDomanda.ordine` / `LivelloFinitura.ordine` | Regola 3: dati in DB, l'admin puo' aggiungere livelli |
| Validazione input server | `if` manuali | `Field(ge=1, le=999_999_999)` | ASVS V5; pattern del repo |
| Riconciliazione IVA | ricalcolare l'IVA extra da zero | resto = `totale.iva - somma(altre aliquote)` | Un euro di arrotondamento non deve rompere il riepilogo |

**Key insight:** nessuna libreria da aggiungere; il rischio non e' "cosa installare" ma "dove vive ogni numero" (un solo calcolo autoritativo per ogni cifra, il resto e' aritmetica pura su dati gia' presenti).

## Runtime State Inventory

Non e' una fase di rename/refactor/migrazione: sezione omessa. Nota di compatibilita' dati: le righe `stima` esistenti ricevono `budget_eur = NULL` e gli snapshot esistenti non hanno `confronto_finiture` -> nessun avviso, nessun errore (Locked). Verificare con un test che `dettaglio_stima` e i PDF reggano uno snapshot v2 senza le chiavi nuove.

## Common Pitfalls

### Pitfall 1: `normalizeResponse` scarta il campo nuovo
**What goes wrong:** `confronto_finiture` arriva dal server ma `postSalvaStima` rimanda l'oggetto normalizzato: se il campo non e' elencato, la stima si salva senza confronto e il PDF/"Le mie stime" non mostrano mai il confronto.
**Why:** `normalizeResponse` ricostruisce campo per campo (commento "ATTENZIONE" nel file; gia' successo con `bonus`).
**Avoid:** aggiungere `confronto_finiture` (con `toNumber` sui due totali) sia in `RawStimaResponse` sia nell'output. Test manuale: salva, riapri da "Le mie stime", confronto presente.

### Pitfall 2: totale Pro IVA esclusa vs budget IVA inclusa
**What goes wrong:** l'avviso Pro dice "rientri" con un budget di 40.000 € contro un totale Pro (imponibile) di 38.000 € che e' in realta' ~42.000 IVA compresa.
**Avoid:** Pattern 6; mostrare nell'avviso la riga "Ora" con la cifra IVA-inclusa usata. Test con budget a cavallo di `totale_ivato` ma non di `totale`.

### Pitfall 3: confronto "in meno" falso
**What goes wrong:** utente con `non_rifare` = finiture/serramenti: passare a un livello sotto non cambia (o cambia poco) il totale; il testo "circa 0–0 € in meno" e' assurdo.
**Avoid:** `confronto_finiture=None` se `confronto.totale_max >= totale.totale_max`; il client in quel caso cade sul testo "meno lavori" (stesso ramo di D-07) — chiarire nel piano quale testo (A6).

### Pitfall 4: `risposte=None` e layer spento
**What goes wrong:** client vecchi/test che non mandano `risposte`: nessun `livello_finiture` scelto, il confronto non ha senso. **Avoid:** `None` in quel caso (non default "medio"->"base"); e test di retrocompatibilita' esistenti (`test_risposte_assenti_lasciano_loracolo_intatto`) restano verdi: il campo nuovo ha default `None` in `StimaResponse`.

### Pitfall 5: pesi che non sommano 100 / peso su totale con extra
**Avoid:** denominatore = somma medi categorie (Pattern 2); nessuna correzione visibile (UI-SPEC), ma il test deve fissare la scelta.

### Pitfall 6: WeasyPrint e geometria
**What goes wrong:** WeasyPrint non supporta tutto il CSS (flex/grid parziali storicamente, `translate`); una tacca centrata con `transform: translateX(-50%)` puo' non rendersi. **Avoid:** usare `position:absolute; left: X%` con `margin-left` negativo in px sulla tacca, niente `transform`/`calc` misto; verificare renderizzando un PDF vero (`test_pdf.py` esiste; su Windows il runtime GTK/Pango puo' mancare — vedi docstring di `pdf_service.py`: import lazy, il test PDF puo' essere skip in locale). Piano: aggiungere un test che verifichi almeno l'HTML renderizzato da Jinja (larghezze percentuali attese), non solo i byte del PDF.

### Pitfall 7: label della tacca fuori dal contenitore su mobile
**Avoid:** clamp/allineamento condizionato (Pattern 1); nessuno spazio riservato sopra la barra quando non c'e' budget (UI-SPEC A.3).

### Pitfall 8: stato dell'avviso su confini
`budget < min` fuori; `min <= budget <= max` al limite; `budget > max` dentro (D-06, UI-SPEC §G). Implementare `statoBudget` con questi operatori esatti (uguale a min/max = "al limite") e testare i bordi. Budget `null` -> nessuno stato.

### Pitfall 9: PUT su stima non propria / Pro-only per errore
Usare `get_current_user`, non `require_pro`; 404 e non 403 per stima altrui. Il budget di una stima Free storica deve poter essere aggiunto ("Aggiungi il tuo budget" su stima salvata pre-fase).

### Pitfall 10: riordino della pagina e tipi del wizard
`EstimateWizard` oggi produce `risposte` da catalogo; la domanda budget e' fuori catalogo, quindi va aggiunta come blocco fisso in coda allo step 3 (`step === 3`), lo stato `budget` sale a `onSubmit` (nuovo campo in `EstimateWizardSubmit`) e `EstimatePage`/`NuovaStimaProPage` lo custodiscono e lo inoltrano a `postSalvaStima`. Non deve bloccare l'avanzamento (`baseValid`) quando vuoto; importo non valido (0/non numerico) blocca solo l'invio del valore (messaggio UI-SPEC), non lo step.

## Code Examples

### Stato dell'avviso (puro, testabile)
```typescript
// frontend/src/lib/risultato.ts — regole D-06
export type StatoBudget = "fuori" | "limite" | "dentro";
export function statoBudget(budget: number | null | undefined, min: number, max: number): StatoBudget | null {
  if (!budget) return null;
  if (budget < min) return "fuori";
  if (budget <= max) return "limite"; // min <= budget <= max
  return "dentro";
}
```

### Livello inferiore da dati DB (Free)
```python
# backend/app/services/risultato.py  (derivato da models/domanda.py: OpzioneDomanda.ordine/attiva/is_default)
def livello_inferiore(opzioni: list[tuple[str, int, bool]], scelto: str | None) -> str | None:
    """opzioni = [(code, ordine, is_default)] attive; scelto=None -> default."""
    ordinate = sorted(opzioni, key=lambda o: o[1])
    corrente = scelto or next((c for c, _o, d in ordinate if d), None)
    codici = [c for c, _o, _d in ordinate]
    if corrente not in codici:
        return None
    i = codici.index(corrente)
    return codici[i - 1] if i > 0 else None
```

### Migrazione additiva
```python
# backend/alembic/versions/0024_budget_eur_su_stima.py
def upgrade() -> None:
    op.add_column("stima", sa.Column("budget_eur", sa.Integer(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table("stima") as batch:   # SQLite dev
        batch.drop_column("budget_eur")
```
(Verificare lo stile delle migrazioni precedenti e `tests/test_migrazioni_sqlite.py`.)

### Schema
```python
class ConfrontoFinitureOut(BaseModel):
    livello_code: str
    livello_nome: str
    totale_min: Decimal
    totale_max: Decimal

class StimaResponse(BaseModel):
    ...
    confronto_finiture: ConfrontoFinitureOut | None = None  # default None: snapshot vecchi e client vecchi

class BudgetIn(BaseModel):
    budget_eur: int | None = Field(default=None, ge=1, le=999_999_999)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pallini fissi 12%/88% | Scala 0..tetto proporzionale | questa fase | l'incertezza (±10% vs ±20%) e' leggibile |
| Lista extra separata | Riepilogo dentro `TotalCard` | questa fase | una sola fonte del "da dove viene il numero" |
| Budget assente | Colonna `stima.budget_eur` + confronto congelato | questa fase | avviso ricostruibile da "Le mie stime" e PDF |

**Deprecated/outdated:** la riga "Comprende i costi extra..." in `TotalCard` (UI-SPEC §C: puo' accorciarsi; il disclaimer pre-sopralluogo resta).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Budget come campo dedicato fuori dal catalogo (colonna `stima.budget_eur`, non in `risposte`), testo domanda come stringa fissa nel wizard | Pattern 4 | Se l'utente vuole il testo curabile da admin (D-41), serve un controllo `importo` di catalogo: piu' lavoro e rischio di contaminare i limiti di `ValoreRisposta` |
| A2 | Pro: totale e confronto IVA-inclusi (IVA per categoria + extra) calcolati server-side per confrontarli col budget | Pattern 6 | Il totale Pro mostrato a schermo e' IVA esclusa; se si preferisce confrontare col totale Free dello snapshot (piu' semplice, ma non e' il "ricalcolo sull'asse `finitura` del motore Pro" letto da D-10), va deciso prima del piano |
| A3 | Peso categoria = medio categoria / somma medi categorie (extra esclusi, arredo escluso) | Pattern 2 | Se atteso sul `totale` con extra, le % cambiano di pochi punti |
| A4 | Con livelli Pro misti per categoria l'etichetta del livello inferiore nell'avviso segue la categoria col livello piu' alto scelto | Pattern 6 | Testo dell'avviso impreciso; alternativa: "un livello in meno" generico |
| A5 | Testi degli avvisi duplicati (TS + Python) invece che da DB | Pattern 7 | Divergenza web/PDF se si modifica un lato solo; mitigata da test di parita' |
| A6 | Confronto non calcolabile/nullo (delta <= 0) cade sul testo "meno lavori" dell'avviso | Pitfall 3 | Copy non esattamente quella di UI-SPEC per quel caso limite |
| A7 | WeasyPrint rende barra a `div` percentuali senza `transform` | Pattern 7 / Pitfall 6 | Barra PDF storta: verificabile solo con rendering reale (GTK spesso assente su Windows locale) |

## Open Questions (RESOLVED)

1. **Base IVA del confronto Pro (A2)**
   - Known: il motore Pro non ha IVA ne' extra; il budget e' IVA inclusa (D-03).
   - Unclear: se l'utente accetta che nell'avviso Pro la riga "Ora" sia un totale IVA-inclusa diverso dal "Totale generale stimato" (IVA esclusa) mostrato nella stessa pagina.
   - Recommendation: procedere con Pattern 6 ed esporre chiaramente "IVA inclusa" nella riga "Ora"; chiedere conferma in fase di plan-check.
   - RESOLVED: A2 confermata dall'utente il 2026-09-29 (vedi "Decisioni confermate").

2. **Dove mostrare il budget nel PDF Pro**
   - Known: `render_pro` e' live e non ha `risultato_json`.
   - Recommendation: budget da colonna + confronto Pro dallo stesso `_compute_dettaglio`; sezione omessa se `budget_eur is None`.
   - RESOLVED: implementato cosi' nel piano 10-07.

3. **Testo dell'avviso quando il confronto e' `None` per delta <= 0 ma finiture non economiche (A6)** — proposta: usare la variante "meno lavori"; confermare col design.
   - RESOLVED: A6 alla discrezione del planner; piani 10-04 (`finiture_al_minimo`) e 10-07 usano il testo "meno lavori" quando il confronto e' nullo per altri motivi.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `backend/.venv` + pytest | test backend | ✓ | (da CLAUDE.md) | — |
| Node/npm (`npm run build`, `oxlint`) | verifica frontend | ✓ (presente `frontend/node_modules`) | — | — |
| WeasyPrint native (GTK/Pango) | test PDF reale su Windows | non verificato in sessione | — | verificare l'HTML Jinja senza WeasyPrint (Pitfall 6); render reale su Render/CI |

**Missing dependencies with no fallback:** nessuna identificata.

## Validation Architecture

`workflow.nyquist_validation` e' `false` in `.planning/config.json`: sezione formale omessa. Indicazioni pratiche per il planner:
- **Backend** (pytest, `backend/.venv/Scripts/python.exe -m pytest <file>`; la suite completa dura ~11 min: eseguire solo i file toccati per commit, la suite intera a fine wave): `tests/test_stima_api.py` (confronto, invarianza del prezzo col budget, oracolo 85 mq intatto), `tests/test_stime_salvate.py` (budget salvato, PUT, 404 altrui, snapshot senza chiavi nuove), `tests/test_dettaglio_pro.py`/`test_dettaglio_pro_livelli.py` (confronto Pro, IVA), `tests/test_pdf.py`/`test_pdf_pro.py` (sezione budget presente/assente), `tests/test_no_leak.py` esteso ai campi nuovi (chiavi vietate: `base_eur_mq`, `moltiplicatore`, `coefficiente_impresa`, `prezzo_impresa`; nota: `test_no_leak` fa il match sulla parola `moltiplicatore`, quindi **nessun nome di campo o testo nuovo** deve contenerla), nuovo `tests/test_risultato.py` per le funzioni pure (`livello_inferiore`, `scala_barra`, `incidenza`, `peso`, `iva_per_aliquota`, `stato_budget` con i bordi).
- **Frontend:** non c'e' un test runner (`package.json`: solo `dev`, `build`, `lint`). Verifica: `npm run build` (tsc) + `npm run lint` (oxlint) + checklist manuale (regola CLAUDE.md globale: verifiche come checklist spuntabile con Note per voce). Non introdurre vitest in questa fase (dipendenza nuova, fuori scope UI-SPEC).
- Wave 0: nessun framework da installare.

## Security Domain

### Applicable ASVS Categories (livello 1, `security_block_on: high`)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (riusa sessione esistente) | `get_current_user` |
| V3 Session Management | no | esistente |
| V4 Access Control | **yes** | `PUT budget` filtrato per `user_id`, 404 su stima altrui (IDOR), come `dettaglio_stima` |
| V5 Input Validation | **yes** | `Field(ge=1, le=999_999_999)` su `budget_eur`; server autoritativo, il client ripulisce ma non fa fede |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR su `PUT /me/stime/{id}/budget` | Tampering / Info disclosure | query con `user_id == current_user.id`, 404 |
| Leak prezzo impresa nei campi nuovi | Info disclosure | DTO chiusi, mapping manuale, `test_no_leak*.py` esteso; il confronto usa solo i totali gia' pubblici; niente `model_validate` su ORM |
| Budget usato per inferire il coefficiente | Info disclosure | il budget non entra mai nel calcolo; il confronto restituisce solo i totali cliente |
| Import di valori enormi/negativi | Tampering / DoS | limiti Pydantic; `Integer` colonna (max 999.999.999 entra in int32) |
| Rate limit | DoS | `POST /stima` e' `20/minute`: il secondo `compute` non lo cambia; considerare lo stesso limite sul `PUT` se il repo lo applica ad altri endpoint auth [ASSUMED] |
| XSS nel PDF | Tampering | Jinja `autoescape=True` gia' attivo; il budget e' un intero |

## Project Constraints (from CLAUDE.md)

- Mai esporre il prezzo impresa/coefficiente (client e PDF utente); il confronto e i derivati usano solo prezzi cliente.
- Output sempre a range; unica eccezione dichiarata: peso % (D-15) e budget dell'utente (dato suo, UI-SPEC "Regole di copy").
- Prezzi/coefficienti in DB: livelli e ordine dei livelli da DB; nessuna soglia di confronto cablata come prezzo. Il fattore 1,2 del tetto e' geometria di presentazione, non un prezzo (D-11 lo fissa).
- IVA differenziata per categoria: il riepilogo raggruppa per `iva_pct` dei dati, mai 10/22 cablati.
- Backend test: `backend/.venv/Scripts/python.exe -m pytest` (il python di sistema non ha le dipendenze); suite completa ~11 min.
- Git: ramo `master`, push `git push origin master:main` (deploya su Render); identita' git per-repo, mai `--global`. Da MEMORY: push solo a fine Fase 10.
- Verifiche manuali sempre come checklist con casella e riga `Note:`.
- Script/commit/documentazione (fuori chat) in prosa normale; risposte in italiano.

## Sources

### Primary (HIGH confidence — codice del repo letto in questa sessione)
- `.planning/phases/10-risultato-leggibile/10-CONTEXT.md`, `10-UI-SPEC.md`, `.planning/REQUIREMENTS.md`, `.planning/config.json`
- `backend/app/schemas/stima.py`, `schemas/stima_salvata.py`, `routers/stima.py`, `routers/stime_salvate.py`, `routers/dettaglio_pro.py`, `services/estimation.py`, `services/dettaglio_pro.py`, `services/effetti.py` (costanti `CONTROLLI_NUMERICI`, `DOMANDA_FINITURA`), `services/pdf_service.py`, `models/stima_salvata.py`, `models/domanda.py`, `models/catalogo.py`, `seed_data/seed-domande.json` (`livello_finiture`), `tests/test_no_leak.py`
- `frontend/src/components/RangeBar.tsx`, `TotalCard.tsx`, `CategoryCard.tsx`, `SavedEstimateDetail.tsx`, `DomandaField.tsx`, `EstimateWizard.tsx`, `pages/EstimatePage.tsx`, `pages/DettaglioProPage.tsx`, `api/stima.ts`, `lib/currency.ts`, `index.css` (token `amber-*`)

### Secondary / Tertiary
- Nessuna fonte web usata: la fase non introduce librerie o API esterne. Le affermazioni su WeasyPrint (A7) sono da conoscenza di training e vanno verificate con un rendering reale.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — nessuna dipendenza nuova, tutto verificato nel codice.
- Architecture: MEDIUM-HIGH — flusso budget/confronto ricavato dai vincoli reali (snapshot immutabile, PDF senza motore, `normalizeResponse`); le scelte A1/A2 restano da confermare.
- Pitfalls: HIGH per quelli ricavati dal codice (1, 2, 3, 5, 8, 9), MEDIUM per il rendering WeasyPrint (6).

**Research date:** 2026-09-29
**Valid until:** 2026-10-29 (stack stabile; rivedere se cambia lo schema `stima` o il motore Pro prima dell'esecuzione)

## Decisioni confermate dall'utente (2026-09-29, prima del planner)

- **A1 — CONFERMATA.** Il budget vive in una colonna dedicata `stima.budget_eur`, fuori dal catalogo e dal motore. Il testo della domanda nel wizard resta una stringa fissa, non curabile da admin.
- **A2 — CONFERMATA.** Nel Pro il budget si confronta con un totale Pro IVA inclusa (IVA per categoria sulle sole categorie `nel_totale_lavori`, più gli extra attivi) calcolato server-side in `_compute_dettaglio`, insieme al confronto con un livello sotto per categoria. Nell'avviso la riga "Ora" riporta esplicitamente "IVA inclusa".
- A3–A7 restano alla discrezione del planner, con le raccomandazioni di questo documento.
