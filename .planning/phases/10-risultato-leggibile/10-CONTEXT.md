# Phase 10: Risultato leggibile e tetto di budget - Context

**Gathered:** 2026-09-29
**Status:** Ready for planning

<domain>
## Phase Boundary

La schermata risultato smette di essere un numero: la barra min–max diventa proporzionale ai
valori reali, ogni categoria mostra incidenza €/m² e peso sul totale, il totale si scompone in
imponibile / IVA / extra, e se l'utente ha dichiarato un budget compare un avviso con il
confronto ricalcolato a un livello di finiture inferiore. Requisiti: RIS-01..04.

Stato misurato sul codice il 2026-09-29, da cui parte la fase:
- **Il budget non esiste da nessuna parte**: nessuna `Domanda`, nessun campo in `StimaInput`,
  nessuna colonna su `stima`. Va introdotto in questa fase (RIS-04 lo presuppone).
- `RangeBar` (`frontend/src/components/RangeBar.tsx`) ha i pallini fissi a `left-[12%]` /
  `right-[12%]`: non e' una scala, e' una decorazione.
- `CategoryCard` mostra solo `totale_min`–`totale_max` (IVA inclusa).
- Il backend calcola gia' `imponibile_*`, `iva_*`, `totale_*` per categoria (`CategoriaOut`) e
  per il totale (`TotaleOut`), e gli extra (`ExtraOut`, importo fisso + `iva_pct`). Il
  riepilogo RIS-03 e' quindi in gran parte lavoro di presentazione.
- Il livello di finiture Free e' la domanda `livello_finiture` (gruppo `ristrutturazione`,
  opzioni `base` "Economiche" / `medio` "Medie" (default) / `alto` "Alte"). Il Pro ha l'asse
  `finitura` (base/medio/alto) nel gruppo `configuratore_pro` (Fase 09).
- Il wizard ha quattro step: 1 "Dove", 2 "L'immobile", 3 "La ristrutturazione", 4 "Le finiture"
  (`EstimateWizard.tsx`). I tipi di controllo oggi sono `stepper`, `toggle`, `scelta_singola`,
  `scelta_multipla`: non c'e' un input numerico libero in euro.

</domain>

<decisions>
## Implementation Decisions

### Ereditate (non si ridiscutono)
- Output sempre a range; mai prezzo o coefficiente impresa verso il client o nel PDF
  (`test_no_leak.py`, `test_no_leak_admin.py` su ogni endpoint e schema nuovo o toccato).
- **Il budget non muove il prezzo** (criterio 5 della roadmap, REQUIREMENTS §v3): due assi
  distinti, *finiture* muove il numero, *budget* no.
- L'arredo sta **accanto** al totale, non dentro (`ArredoOut`).
- Prezzi e coefficienti in database: nessuna soglia o percentuale del confronto cablata come
  prezzo nel codice.
- Snapshot congelato: cio' che il PDF e "Le mie stime" mostrano viene da `risultato_json`.
  Le stime salvate prima di questa fase non hanno budget: nessun avviso, nessun errore.

### Raccolta del budget
- **D-01:** Il budget e' una **domanda del wizard nello step 3 "La ristrutturazione"**, con
  testo "Qual e' il tuo budget per la ristrutturazione?": l'utente scrive la cifra che ha in
  mente.
- **D-02:** **Facoltativo.** Senza budget non compare nessun avviso e nessuna tacca sulla barra.
- **D-03:** **Importo libero in euro, IVA inclusa**, confrontato con il totale IVA inclusa.
- **D-04:** **Salvato con la stima e riportato nel PDF** (Free e Pro): riaprendo da "Le mie
  stime" l'avviso e' ancora li'.
- **D-05:** Il budget si puo' **cambiare dalla pagina risultato**, con un campo nel box
  dell'avviso: l'avviso si ricalcola subito e il valore nuovo si salva sulla stima. Il prezzo
  non cambia.

### Avviso di sforamento
- **D-06:** Tre stati rispetto al range del totale lavori:
  - budget **sotto il minimo** → avviso "fuori budget" con il confronto (D-07);
  - budget **dentro il range** → nota morbida "al limite: dipende dalle scelte";
  - budget **sopra il massimo** → conferma positiva.
- **D-07:** Il confronto si ricalcola **un livello sotto** quello scelto (alte→medie,
  medie→economiche), mostrando il nuovo range e la differenza. Con finiture gia' economiche non
  c'e' confronto: l'avviso dice che per rientrare nel budget servono meno lavori.
- **D-08:** Il budget si confronta con il **solo totale lavori**, senza l'arredo (la domanda
  parla di budget "per la ristrutturazione").
- **D-09:** Il confronto e' un **ricalcolo vero lato server** con il livello inferiore, non una
  stima proporzionale lato client.
- **D-10:** L'avviso vale **anche nel dettaglio Pro**: stesso comportamento, con il confronto
  ricalcolato sull'asse `finitura` del motore Pro (un livello sotto l'opzione scelta in "Affina
  la stima").

### Barra proporzionale (RIS-01)
- **D-11:** La `RangeBar` del totale si disegna **su un asse da 0 a un tetto** (circa 1,2 volte
  il massimo, oppure il budget se piu' alto): il segmento colorato e' largo quanto l'incertezza
  reale, cosi' una stima ±10% e una ±20% si distinguono a colpo d'occhio.
- **D-12:** Se il budget e' dichiarato, compare sulla barra una **tacca verticale "Il tuo
  budget"**.
- **D-13:** Nelle card di categoria non c'e' una RangeBar, ma una **mini-barra orizzontale del
  peso %** della categoria sul totale.

### Card e riepilogo (RIS-02, RIS-03)
- **D-14:** Incidenza €/m² per categoria **a range e su imponibile** (IVA esclusa), es.
  "310–380 €/m²", sui m² calpestabili della stima.
- **D-15:** Il peso relativo della categoria e' **un solo numero sul valore medio** (es. "34%"):
  e' un'indicazione di composizione, non un prezzo, e non viola la regola del range.
- **D-16:** Il riepilogo **imponibile / IVA / extra** sta **dentro la `TotalCard`, sotto il
  totale**: imponibile lavori, IVA divisa per aliquota (10% / 22%), extra, totale. Sostituisce
  la lista degli extra che oggi e' separata in `EstimatePage` e `SavedEstimateDetail`.
- **D-17:** Tutto questo (€/m², peso, riepilogo, budget e avviso) va **anche nei PDF**
  `pdf_stima.html` e `pdf_stima_pro.html`, con la barra statica.

### Claude's Discretion
- Forma tecnica del budget: nuovo `tipo_controllo` di catalogo (es. `importo`) o campo dedicato
  di `StimaInput` fuori dal catalogo, e dove persisterlo (colonna su `stima` o dentro
  `risultato_json`), purche' D-01..D-05 reggano e il budget resti fuori dal calcolo del prezzo.
- Forma dell'endpoint del confronto (campo calcolato nella risposta della stima o endpoint a
  parte) e come il campo di D-05 salva il budget sulla stima.
- Arrotondamento del tetto della scala (D-11), testi esatti dell'avviso, layout su mobile.
- Come si calcola l'IVA per aliquota nel riepilogo (raggruppando `CategoriaOut.iva_pct`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisiti e vincoli
- `.planning/ROADMAP.md` §"Phase 10: Risultato leggibile e tetto di budget" — goal e 5 criteri
- `.planning/REQUIREMENTS.md` §"Risultato leggibile (RIS)", §"Vincoli permanenti", §"v3 / Deferred" (budget senza effetto sul prezzo)
- `CLAUDE.md` — regole di dominio (niente prezzo impresa, output a range, IVA per categoria)

### Fasi precedenti da rispettare
- `.planning/phases/09-configuratore-pro/09-CONTEXT.md` — assi Pro `finitura`/`tipo_pavimento`, pannello "Affina la stima", `risposte_pro_json`
- `.planning/phases/08.1-catalogo-domande-pagina-crud-e-file-excel/08.1-CONTEXT.md` — catalogo domande, tipi di controllo, effetti validati da `valida_effetto`

### Codice toccato
- `frontend/src/components/RangeBar.tsx`, `TotalCard.tsx`, `CategoryCard.tsx`
- `frontend/src/pages/EstimatePage.tsx`, `frontend/src/components/SavedEstimateDetail.tsx`, `frontend/src/pages/DettaglioProPage.tsx`
- `frontend/src/components/EstimateWizard.tsx` — step 3 "La ristrutturazione"
- `backend/app/schemas/stima.py` — `StimaResponse`, `CategoriaOut`, `TotaleOut`, `ExtraOut`
- `backend/app/services/estimation.py`, `effetti.py`, `dettaglio_pro.py` — motore Free e Pro, applicazione di `livello_finiture` / `finitura`
- `backend/app/routers/stima.py`, `stime_salvate.py`, `dettaglio_pro.py`
- `backend/app/templates/pdf_stima.html`, `pdf_stima_pro.html`, `backend/app/services/pdf_service.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CategoriaOut` / `TotaleOut` gia' con imponibile, IVA e totale a range: il riepilogo non
  richiede calcoli nuovi lato server.
- `formatEur` / `formatEurRange` (`frontend/src/lib/currency`) per tutte le cifre nuove.
- Gradiente `--gold` → `--primary` della `RangeBar`: il motivo-firma resta, cambia solo la
  geometria.
- `POST /me/stime/{id}/dettaglio-pro/risposte` e `risposte_pro_json`: il ricalcolo Pro con
  finitura diversa passa dallo stesso motore.

### Established Patterns
- Le domande del wizard vengono dal catalogo (`domanda` + `opzione_domanda`), con testi
  curabili dal pannello: una domanda nuova si semina senza riscrivere la curatela (D-41).
- Le sezioni opzionali della risposta sono `None`, mai a zero (`bonus`, `arredo`): il
  confronto col budget segue la stessa regola.
- Il disclaimer viaggia dentro lo snapshot, cosi' finisce nel PDF e non e' rimovibile dal client.

### Integration Points
- La risposta della stima Free (`StimaResponse`) e il dettaglio Pro devono portare il budget e
  il confronto; lo snapshot `risultato_json` li congela.
- `test_no_leak*.py` va esteso a ogni schema nuovo o modificato.

</code_context>

<specifics>
## Specific Ideas

- Testo della domanda voluto da Riccardo: "Qual e' il tuo budget per la ristrutturazione?",
  risposta = la cifra che l'utente ha in mente.
- Sulla barra la tacca del budget si chiama "Il tuo budget".

</specifics>

<deferred>
## Deferred Ideas

- Nessuna idea fuori perimetro emersa. Restano nel backlog v3 i punti gia' noti in
  REQUIREMENTS §"v3 / Deferred".

</deferred>

---

*Phase: 10-risultato-leggibile*
*Context gathered: 2026-09-29*
