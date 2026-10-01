---
phase: 10-risultato-leggibile
reviewed: 2026-10-01T12:00:00Z
depth: standard
files_reviewed: 53
files_reviewed_list:
  - backend/alembic/versions/0024_budget_eur_su_stima.py
  - backend/app/models/stima_salvata.py
  - backend/app/routers/dettaglio_pro.py
  - backend/app/routers/stima.py
  - backend/app/routers/stime_salvate.py
  - backend/app/schemas/dettaglio_pro.py
  - backend/app/schemas/stima.py
  - backend/app/schemas/stima_salvata.py
  - backend/app/services/bonus_stima.py
  - backend/app/services/effetti.py
  - backend/app/services/pdf_service.py
  - backend/app/services/risultato.py
  - backend/app/templates/pdf_stima.html
  - backend/app/templates/pdf_stima_pro.html
  - backend/tests/test_bonus_stima.py
  - backend/tests/test_budget_stima.py
  - backend/tests/test_confronto_finiture.py
  - backend/tests/test_dettaglio_pro_bonus.py
  - backend/tests/test_dettaglio_pro_budget.py
  - backend/tests/test_migrazioni_sqlite.py
  - backend/tests/test_no_leak.py
  - backend/tests/test_pdf.py
  - backend/tests/test_pdf_pro.py
  - backend/tests/test_risultato.py
  - backend/tests/test_stima_tier.py
  - backend/tests/test_stime_salvate.py
  - frontend/scripts/check-richiesta-stima.ts
  - frontend/scripts/fixtures/catalogo-free-85.json
  - frontend/src/api/client.ts
  - frontend/src/api/dettaglio-pro.ts
  - frontend/src/api/domande.ts
  - frontend/src/api/stima.ts
  - frontend/src/components/ArredoCard.tsx
  - frontend/src/components/BonusPanel.tsx
  - frontend/src/components/BudgetAlert.tsx
  - frontend/src/components/CategoryCard.tsx
  - frontend/src/components/DettaglioProView.tsx
  - frontend/src/components/EstimateWizard.tsx
  - frontend/src/components/ImportoField.tsx
  - frontend/src/components/LetturaCategoria.tsx
  - frontend/src/components/RangeBar.tsx
  - frontend/src/components/RiepilogoIvaRighe.tsx
  - frontend/src/components/SavedEstimateDetail.tsx
  - frontend/src/components/SottocategoriaAccordion.tsx
  - frontend/src/components/TotalCard.tsx
  - frontend/src/lib/currency.ts
  - frontend/src/lib/domande.ts
  - frontend/src/lib/richiestaStima.ts
  - frontend/src/lib/risultato.ts
  - frontend/src/pages/DettaglioProPage.tsx
  - frontend/src/pages/EstimatePage.tsx
  - frontend/src/pages/NuovaStimaProPage.tsx
  - frontend/src/routes/LeMieStimePage.tsx
findings:
  critical: 0
  warning: 6
  info: 7
  total: 13
status: issues_found
---

# Fase 10: Code Review Report

**Reviewed:** 2026-10-01T12:00:00Z
**Depth:** standard
**Files Reviewed:** 53
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

Revisione del diff `5ed4a5c^..HEAD` sui 53 file della fase 10 (risultato leggibile: riepilogo IVA, EUR/m2 e peso, budget con PATCH, confronto finiture, bonus Pro, PUT `/me/stime/{id}` e macchina a stati auto-save/PUT di `EstimatePage`).

Controlli mirati richiesti, con esito:

- **Leak coefficiente / prezzo impresa:** nessun leak trovato. I nuovi DTO (`ConfrontoFinitureOut`, `RiepilogoIvaOut`, `LetturaCategoriaOut`, `BudgetOut`, campi bonus G5/G10) espongono solo valori lato cliente. I template PDF non leggono campi impresa e `test_no_leak.py` copre i nuovi endpoint (POST /stima con confronto, GET/PATCH budget, dettaglio-pro con confronto e bonus).
- **Output a range:** tutti gli importi di stima, IVA, detrazioni, confronto e delta sono a range. Restano a cifra singola solo gli extra (importi fissi da DB, scelta preesistente) e il budget dichiarato dall'utente: nessuna violazione della regola 2.
- **PUT /me/stime/{id}:** l'anti-IDOR è corretto (filtro `id + user_id`, 404 su stima altrui, testato). Anche l'immutabilità del tier è corretta: la colonna `tier` non viene mai toccata, testato in `test_stima_tier.py`. Il paywall Pro resta doppio (`require_pro` + `tier`), quindi un PUT non apre il dettaglio Pro a un utente Free. Restano due punti deboli: manca la validazione di `input.mq`/`input.citta`, che ora pilotano il ricalcolo Pro (WR-06), e l'ultimo PUT arrivato vince senza controllo di versione (WR-01).
- **Auto-save/PUT in `EstimatePage.tsx`:** ho percorso a mano gli scenari "POST in volo + Modifica", "POST fallito + Modifica" e "cambio utente". In questi non ci sono doppi POST né PUT verso la stima di un altro utente: `ultimoSalvataggio` è legato a `userId` e il server protegge comunque. Ci sono però una race tra PUT concorrenti (WR-01), errori silenziosi di salvataggio con la CTA Pro bloccata (WR-03) e la sovrascrittura senza scelta della stima salvata (WR-02).

Nessun BLOCKER: non ho trovato difetti che espongano dati riservati o corrompano lo storico di altri utenti.

## Warnings

### WR-01: PUT concorrenti sulla stessa stima, l'ultimo ad arrivare vince (snapshot salvato diverso da quello mostrato)

**File:** `frontend/src/pages/EstimatePage.tsx:181-190`, `frontend/src/pages/EstimatePage.tsx:244-246`, `backend/app/routers/stime_salvate.py:147-193`
**Issue:** `handleModifica` chiama `updateMutation.reset()`, che stacca l'observer ma **non annulla** il PUT in volo. Se l'utente fa "Modifica" e ricalcola prima che il PUT precedente finisca, parte un secondo `updateMutation.mutate` sullo stesso `id` mentre il primo è ancora pendente. Le due richieste viaggiano in parallelo, anche su connessioni HTTP diverse, e il backend applica "last commit wins" senza versione né `If-Match`. Se il PUT di R2 arriva dopo quello di R3, il DB conserva R2 mentre lo schermo mostra R3: PDF e "Le mie stime" non corrispondono a ciò che l'utente ha visto, cioè proprio l'invariante D-09 che lo snapshot dovrebbe garantire.
**Fix:** serializzare i PUT lato client: non inviare il nuovo PUT finché il precedente è pendente e mettere in coda l'ultimo risultato. In alternativa, aggiungere una versione ottimistica lato server:
```ts
// EstimatePage: come per il POST, attendi se un PUT e' in volo
const putInVolo = useRef(false);
// in mutationFn: putInVolo.current = true; onSettled: putInVolo.current = false; setPostConclusi(n => n + 1)
if (azione === "put" && putInVolo.current) return; // l'effetto riparte a onSettled
```
Oppure lato backend una colonna `revisione` e `PUT` con `revisione_attesa`, che risponde 409 se non coincide.

### WR-02: dopo il primo "Modifica" ogni ricalcolo sovrascrive la stima salvata, senza modo di crearne una nuova

**File:** `frontend/src/pages/EstimatePage.tsx:105-109`, `frontend/src/pages/EstimatePage.tsx:239-243`, `frontend/src/lib/richiestaStima.ts:83-91`
**Issue:** `modificaDiUtente` resta impostato "per tutta la vita della pagina" e `azioneSalvataggio` non torna mai a `post`. Se l'utente cambia città, m² o tipo (cioè stima un altro immobile), la stima salvata in precedenza viene sostituita per intero da `PUT` senza conferma: snapshot, totali, budget e un PDF già scaricato non più riproducibile. Non c'è un percorso "salva come nuova" e nemmeno una cronologia (`created_at` resta invariato, vedi IN-04). La regola G14 è stata approvata in UAT, ma così com'è comporta una perdita silenziosa di dati salvati.
**Fix:** quando la nuova richiesta differisce negli input strutturali (città/mq/tipo, `stessaRichiesta` esiste già, vedi IN-03), chiedere conferma ("Aggiorna la stima salvata" / "Salva come nuova"). In alternativa, mostrare almeno un avviso esplicito "Stai aggiornando la stima del <data>" con un link "Salva come nuova", che riporti `modificaDiUtente` a `null`.

### WR-03: fallimenti di salvataggio silenziosi, CTA Pro bloccata su "Salvataggio in corso…" e budget non persistito

**File:** `frontend/src/pages/EstimatePage.tsx:193-198`, `frontend/src/pages/EstimatePage.tsx:203-224`, `frontend/src/pages/EstimatePage.tsx:374-380`, `frontend/src/pages/EstimatePage.tsx:428-434`
**Issue:**
1. Se l'auto-save POST fallisce (`saveMutation.isError`), la pagina non mostra nessun errore: viene renderizzato solo `updateMutation.isError`. `idSalvato` resta `undefined`, quindi per un utente Pro il bottone resta per sempre disabilitato con "Salvataggio in corso…" e "Scarica PDF" resta disabilitato.
2. In modalità Modifica, se il PUT fallisce, `idSalvato` (`updateMutation.data?.id ?? saveMutation.data?.id`, entrambi azzerati da `reset()`) resta `undefined`, con lo stesso blocco della CTA. Il messaggio dice "Riprova a ricalcolare", ma un id valido esiste (`ultimoSalvataggio.id`).
3. `handleSalvaBudget` con `idSalvato === undefined` fa solo `setBudget`: l'utente vede il budget "aggiornato" ma, se il salvataggio è fallito, non verrà mai persistito. La PATCH dell'effetto (righe 210-212) inghiotte l'errore (`.catch(() => { budgetSalvato.current = null })`) senza segnalarlo né riprovare.
**Fix:** mostrare un `Alert` anche su `saveMutation.isError`, con un bottone "Riprova a salvare". In modalità Modifica usare `ultimoSalvataggio?.id` come fallback di `idSalvato`, così PDF e CTA Pro restano utilizzabili sull'ultima versione salvata con successo. Esporre l'errore della PATCH dell'effetto, per esempio con uno stato `erroreBudget` passato a `BudgetAlert`:
```ts
const idSalvato = stimaInModifica
  ? (updateMutation.data?.id ?? saveMutation.data?.id ?? ultimoSalvataggio?.id)
  : saveMutation.data?.id;
```
Va valutato se, dopo un PUT fallito, si preferisce disabilitare il PDF finché lo snapshot non è allineato. In ogni caso serve uno stato esplicito, non "Salvataggio in corso…" infinito.

### WR-04: il PDF Pro non riporta bonus né arredo, che la schermata Pro ora mostra (parità schermata/PDF rotta)

**File:** `backend/app/templates/pdf_stima_pro.html:526-601`, `backend/app/services/pdf_service.py:194-220`, `frontend/src/components/DettaglioProView.tsx:441-456`
**Issue:** con 10-14 (G6) e G11 `DettaglioProView` mostra `BonusPanel` (bonus calcolati sui totali Pro da `_compute_dettaglio`) e `ArredoCard` con le detrazioni su arredo. `render_html_pro` riceve `calcolo.bonus` ma non lo passa al template, e il template Pro non ha sezioni bonus né arredo. Il docstring del modulo (`dettaglio_pro.py:4-7`, `pdf_service.py:10-17`) promette "schermata e PDF non possono divergere": oggi il PDF Pro omette detrazioni e arredo che l'utente vede a schermo, mentre il PDF Free li include.
**Fix:** passare `bonus_pdf=_bonus_pdf(calcolo.bonus.model_dump(mode="json") if calcolo.bonus else None)` e l'arredo dello snapshot (`stima.risultato_json.get("arredo")`) a `pdf_stima_pro.html`. Poi riusare i blocchi `bonus-block` del template Free, estraendoli in una macro Jinja comune, e aggiungere in `test_pdf_pro.py` un test di parità sulle stringhe dei range bonus.

### WR-05: "Rata annua (10 anni)" cablato nel PDF Free, mentre il numero di rate è un dato per bonus

**File:** `backend/app/templates/pdf_stima.html:536`
**Issue:** la durata è scritta nel template, ma ogni voce bonus porta il suo `rate_annuali`, modificabile dall'admin: `ArredoCard.tsx:71` lo legge correttamente (`in {voce.rate_annuali} rate annue`). Se l'admin cambia le rate di un bonus, o due bonus hanno durate diverse, il PDF dichiara una durata sbagliata accanto a una rata calcolata su un'altra durata. Viola lo spirito della regola 3 (dati in DB, non cablati) su un'informazione fiscale. In più, la rata aggregata `rata_annua_lavori_*` è una somma di rate con durate potenzialmente diverse, quindi un'unica durata in etichetta può essere fuorviante.
**Fix:** derivare l'etichetta dai dati, per esempio in `_bonus_pdf`:
```python
durate = {v.get("rate_annuali") for v in lavori if v.get("rate_annuali")}
"etichetta_rata": f"Rata annua ({durate.pop()} anni)" if len(durate) == 1 else "Rata annua (primi anni)",
```
e mostrare `rate_annuali` anche sulle singole righe bonus, come fa il web.

### WR-06: `input.mq` / `input.citta` non validati nel payload salvato, ma ora pilotano il ricalcolo Pro via PUT

**File:** `backend/app/schemas/stima.py:65-75` (usato da `backend/app/schemas/stima_salvata.py:74`), `backend/app/routers/stime_salvate.py:180-187`
**Issue:** `StimaSalvataCreate.input` è uno `StimaInputEcho` senza vincoli (`citta: str`, `mq: int`). Il PUT riscrive `row.mq`, `row.citta` e `row.tipo` "perché il dettaglio Pro ricalcola da quelle" (docstring righe 161-162). Un client può quindi impostare `mq = 0`, negativo o enorme. Con valore negativo il dettaglio Pro e il PDF Pro producono totali negativi. Oltre i 2^31 l'`Integer` su Postgres solleva `DataError`, quindi 500. Una `citta` più lunga di 200 caratteri supera `String(200)` e su Postgres dà 500. Il problema esisteva già per il POST, ma il PUT lo rende un percorso di mutazione ripetibile su stime Pro esistenti, e `_compute_dettaglio` lavora su quei valori senza ricontrollarli.
**Fix:** riusare nello schema di salvataggio gli stessi vincoli di `StimaRequest`:
```python
class StimaInputEcho(BaseModel):
    citta: str = Field(min_length=1, max_length=200)
    mq: int = Field(ge=<min di StimaRequest>, le=<max di StimaRequest>)
```
Gli snapshot storici vengono riletti con `StimaInputEcho(**snapshot["input"])`: se si teme che vecchi dati violino i vincoli, conviene definire uno schema `StimaInputSalvataIn` dedicato all'ingresso POST/PUT e lasciare l'eco permissivo in lettura.

## Info

### IN-01: `deltaConfronto` / `avviso_budget` possono produrre un delta con estremo negativo ("circa −300 € – 2.000 € in meno")

**File:** `frontend/src/lib/risultato.ts:242-252`, `backend/app/services/risultato.py:367-377`
**Issue:** il null scatta solo se *entrambi* i delta sono <= 0. Se `confronto.totale_min >= totale_min` ma `confronto.totale_max < totale_max`, il range "in meno" parte da un valore negativo. Con i dati attuali è improbabile, ma la funzione non lo esclude.
**Fix:** clampare a zero (`Math.max(0, a)` e `max(Decimal(0), a)`) e trattare come null il caso in cui il massimo clampato sia 0. Va mantenuta la parità TS/Python.

### IN-02: fallback `_imp()` nel PDF Free incoerente: l'incidenza legge comunque `c["imponibile_min"]`

**File:** `backend/app/services/pdf_service.py:144-159`
**Issue:** il commento dice che gli snapshot senza `imponibile_*` "ricadono su totale_*", ma `incidenza_eur_mq(c["imponibile_min"], c["imponibile_max"], mq)` alla riga 155 accede direttamente alle chiavi e solleva `KeyError`. Oggi è codice morto, perché `imponibile_*` esiste dal piano 01-03 e `dettaglio_stima` fallirebbe comunque. Resta però un fallback ingannevole.
**Fix:** usare `_imp(c)` anche per l'incidenza oppure eliminare il fallback e il commento.

### IN-03: `stessaRichiesta` / `normalizzaRisposte` non sono più usate nel codice di produzione

**File:** `frontend/src/lib/richiestaStima.ts:8-25`
**Issue:** dopo G14 la regola "input diversi = record nuovo" è stata superata e le funzioni sono usate solo da `scripts/check-richiesta-stima.ts`.
**Fix:** rimuoverle, oppure riutilizzarle per la conferma suggerita in WR-02.

### IN-04: dopo un PUT `created_at` resta quello originale e non c'è `updated_at`

**File:** `backend/app/routers/stime_salvate.py:153-163`, `backend/app/models/stima_salvata.py:69`
**Issue:** "Le mie stime" ordina e data le stime per `created_at`. Anche il filename del PDF (`build_filename`) usa `created_at`. Una stima riscritta oggi appare con la data e la posizione di quella originale, e il PDF scaricato ora porta nel nome la data vecchia.
**Fix:** aggiungere una colonna `updated_at` nullable con migrazione additiva, valorizzarla nel PUT e usarla per ordinamento e filename, oppure mostrare "aggiornata il".

### IN-05: invalidazione cache incompleta dopo le PATCH del budget

**File:** `frontend/src/pages/EstimatePage.tsx:206-224`, `frontend/src/components/SavedEstimateDetail.tsx:74-77`, `frontend/src/components/DettaglioProView.tsx:436-439`
**Issue:** la PATCH da `EstimatePage` non invalida `["stima-dettaglio", id]` / `["dettaglio-pro", id]`. Quella in `SavedEstimateDetail` non invalida `["dettaglio-pro", id]`, e quella in `DettaglioProView` non invalida `["stima-dettaglio", id]`, che pure espone `budget_eur`. Con `staleTime` di default il refetch al mount limita il danno, ma per un frame può comparire un budget obsoleto.
**Fix:** creare un helper `invalidaStima(queryClient, id)` che invalidi le tre chiavi (`stima-dettaglio`, `dettaglio-pro`, `storico-stime`) e usarlo in tutti i punti di salvataggio.

### IN-06: `_confronto_pro` tratta un livello sconosciuto come "già al minimo"

**File:** `backend/app/routers/dettaglio_pro.py:316-324`
**Issue:** `livello_inferiore` restituisce `None` sia per "già al minimo" sia per un "codice non tra le opzioni", per esempio un livello disattivato dall'admin dopo il salvataggio di `livelli_pro_json`. Se tutte le categorie ricadono nel secondo caso, `finiture_al_minimo=True` e l'avviso budget dice "Hai già scelto finiture economiche", che è falso.
**Fix:** distinguere i due casi con `livello_corrente(opzioni, scelto) == codici_ordinati[0]` prima di contare la categoria come "al minimo".

### IN-07: il PUT senza `preferenze_pro` conserva `risposte_pro_json` anche se mq/tipo cambiano

**File:** `backend/app/routers/stime_salvate.py:174-189`, `backend/app/routers/dettaglio_pro.py:439-442`
**Issue:** in `_compute_dettaglio` le risposte del pannello Pro prevalgono su quelle del wizard. Su una stima Pro aggiornata via PUT con mq diversi, valori come bagni o porte del pannello, dati per la superficie precedente, sovrascrivono le nuove risposte del wizard. Oggi è difficilmente raggiungibile dalla UI, perché `EstimatePage` fa PUT solo sulle stime che ha creato lei, ma il contratto del PUT lo permette.
**Fix:** se `input.mq` o `input.tipo` cambiano, azzerare `risposte_pro_json` (oppure solo le chiavi numeriche), oppure documentare esplicitamente il comportamento nel docstring del PUT.

---

_Reviewed: 2026-10-01T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
