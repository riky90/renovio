---
status: pending
phase: 10-risultato-leggibile
requirement: RIS-01, RIS-02, RIS-03, RIS-04
source: [10-09-PLAN.md]
started: 2026-09-29T00:00:00Z
---

# Collaudo Fase 10: risultato leggibile e tetto di budget

Checklist per Riccardo. Ogni voce ha un passo da fare e il risultato atteso. Spunta la casella
e scrivi nella riga `Note:` cosa non torna; le note tornano come input per
`/gsd:plan-phase 10 --gaps`. Nessun esecutore spunta le caselle al posto tuo.

## Controlli automatici gia' eseguiti

Vedi la tabella nel SUMMARY del piano 10-09 (suite backend completa, `npm run build`,
`npm run lint`). Il rendering reale dei PDF non e' coperto: WeasyPrint non e' installato su
questo PC Windows, quindi i test sui byte del PDF sono saltati e i PDF vanno guardati a occhio
nella sezione "PDF" (o su un ambiente con GTK3).

## Come si avvia

- Backend (da `backend/`): `.venv/Scripts/python.exe -m uvicorn app.main:app --reload` su http://127.0.0.1:8000
- Frontend (da `frontend/`): `npm run dev` su http://localhost:5173
- Un utente registrato per le voci "da loggato"; per le voci Pro serve una stima Pro (tier pro) gia' salvata o un account con abbonamento Pro attivo.
- Nota sui dati: nel seed attuale le finiture "base" costano piu' delle "medio". Il confronto a finiture inferiori dalle "medio" non esiste (voce attesa: nessuna riga "Con finiture..."); si vede partendo da finiture "alto". Non e' un difetto di questa fase.

## Avvio

- [ ] **Avvia backend e frontend come indicato sopra e apri la home** — la home si apre senza errori in console e senza schermata bianca.
  Note:

## Criterio 1: la RangeBar e' proporzionale ai valori reali

- [ ] **Fai una stima Free: 85 mq, Reggio Emilia, ristrutturazione totale, nessun budget** — la barra sotto il totale ha un segmento colorato che NON e' fisso a filo dei bordi (non piu' i pallini a 12% e 88%); nessuna tacca; sotto il totale solo il link "Aggiungi il tuo budget".
  Note:
- [ ] **Rifai la stima con un altro tipo di intervento (es. leggera) e confronta la barra a occhio** — posizione e larghezza del segmento cambiano rispetto alla totale; il segmento piu' stretto resta comunque visibile (larghezza minima).
  Note:
- [ ] **Guarda gli estremi della barra** — le etichette di minimo e massimo sono sotto gli estremi del segmento, leggibili, e corrispondono al range mostrato nel totale.
  Note:
- [ ] **Apri il pannello Bonus (detrazioni) se presente nella stima** — la barra del bonus si vede ancora correttamente (secondo chiamante della RangeBar, corretto nel piano 10-01).
  Note:

## Criterio 2: incidenza €/m² e peso per categoria

- [ ] **Nella stima Free 85 mq guarda ogni card di categoria** — ogni card mostra "€/m² IVA esclusa" e "% del totale" con una mini-barra.
  Note:
- [ ] **Somma a mano le percentuali "% del totale" di tutte le categorie** — la somma e' circa 100 (scarto da arrotondamento); nelle percentuali non entrano extra ne' arredo.
  Note:
- [ ] **Controlla un €/m² a mano su una categoria: importo categoria / 85** — coincide con il valore mostrato (range min-max, IVA esclusa).
  Note:
- [ ] **Riapri una stima salvata prima della Fase 10 da "Le mie stime"** — le card mostrano comunque €/m² e peso (derivati dallo snapshot), nessun errore.
  Note:

## Criterio 3: il riepilogo espone imponibile, IVA ed extra

- [ ] **Guarda la TotalCard della stima Free** — righe in ordine: Imponibile lavori, una riga IVA per ogni aliquota (10% e 22%), Costi extra con sotto-elenco delle voci, Totale IVA inclusa.
  Note:
- [ ] **Confronta "Totale IVA inclusa" con la cifra sopra la barra** — sono lo stesso importo.
  Note:
- [ ] **Cerca una lista extra separata sotto o accanto alla TotalCard** — non c'e': gli extra compaiono solo nel riepilogo.
  Note:
- [ ] **Somma a mano Imponibile + righe IVA + Costi extra** — il risultato coincide con il Totale IVA inclusa (scarto al massimo di 1 euro da arrotondamento).
  Note:

## Criterio 4: avviso quando si supera il budget, con confronto a finiture inferiori

- [ ] **(4a) Rifai la stima dal wizard con budget 30.000 EUR (step 3), finiture "alto"** — sulla barra compare la tacca "Il tuo budget" a sinistra del segmento; sotto il totale compare l'avviso "La stima supera il tuo budget" con le righe "Ora" e "Con finiture medie" e la differenza a range.
  Note:
- [ ] **(4b) Budget dentro il range della stima (un valore tra minimo e massimo)** — avviso "Il tuo budget è al limite" con il testo su finiture come leva; tacca dentro il segmento.
  Note:
- [ ] **(4c) Budget sopra il massimo, poi budget maggiore di 1,2 x massimo** — avviso "Rientri nel tuo budget"; la tacca si sposta a destra del segmento; oltre 1,2 x massimo il tetto della barra si allarga e la tacca resta nel contenitore.
  Note:
- [ ] **(4d) Finiture economiche ("base") con budget basso** — testo "Hai già scelto finiture economiche. Per stare nel tuo budget servono meno lavori..." senza righe di confronto.
  Note:
- [ ] **(4e) Finiture "medio" con budget basso** — nessuna riga "Con finiture..." (il livello sotto non costa meno nel seed); compare il testo "Per stare nel tuo budget servono meno lavori..." senza errori.
  Note:
- [ ] **(4f) Scrivi "0" nel campo budget del box e premi "Aggiorna il confronto"** — messaggio in rosso "Scrivi un importo in euro maggiore di zero."; la stima resta calcolata, senza tacca e senza avviso.
  Note:
- [ ] **(4g) Premi "Togli il budget", poi "Aggiungi il tuo budget"** — il primo elimina tacca e avviso; il secondo riapre il campo; totale e categorie non cambiano.
  Note:
- [ ] **(4h) Da anonimo con budget nel wizard: calcola, registrati, apri la stima salvata** — la stima salvata ha il budget e l'avviso relativo.
  Note:
- [ ] **(4i) Da loggato: cambia il budget dal box, poi ricarica la pagina e apri "Le mie stime"** — il budget nuovo e l'avviso sono ancora li'; non ricompare il budget vecchio.
  Note:
- [ ] **(4j) Stima salvata prima della Fase 10, aperta da "Le mie stime"** — nessun avviso, solo "Aggiungi il tuo budget"; nessun errore in pagina o in console.
  Note:
- [ ] **(4k) Sincronizzazione budget/auto-save: da loggato, appena compare il risultato (entro 1-2 secondi, mentre l'auto-salvataggio e' appena partito) cambia il budget dal box, poi apri "Le mie stime" e riapri quella stima** — il budget mostrato e' quello nuovo, non quello del wizard, e l'avviso corrisponde.
  Note:
- [ ] **(4l) Pro web: apri una stima Pro e guarda sotto "Totale generale stimato"** — c'e' il blocco "Totale stimato · IVA inclusa" con barra proporzionale sul totale IVA inclusa e, se c'e' un budget, la tacca "Il tuo budget".
  Note:
- [ ] **(4m) Pro web: nello stesso blocco guarda il riepilogo** — Imponibile lavori, IVA per aliquota, Costi extra con sotto-elenco, Totale IVA inclusa; il Totale IVA inclusa e' uguale alla cifra della barra.
  Note:
- [ ] **(4n) Pro web: apri l'accordion di ogni categoria nel totale lavori** — sotto la riga "Totale {categoria}" compaiono "€/m² IVA esclusa" e "% del totale" con mini-barra; la voce arredo NON li mostra.
  Note:
- [ ] **(4o) Pro web: guarda l'avviso budget sotto il blocco** — la riga "Ora (IVA inclusa)" e' sempre visibile; nello stato fuori budget c'e' il confronto col livello inferiore, se il seed lo permette (parti da finiture "alto").
  Note:
- [ ] **(4p) Pro web: cambia il budget dal box** — tacca e avviso cambiano; totale, riepilogo, €/m² e peso restano identici. Riapri da "Le mie stime": il budget nuovo e' ancora li'.
  Note:
- [ ] **(4q) Pro web contro PDF Pro della stessa stima** — totale IVA inclusa, righe IVA, €/m² e peso di due categorie a tua scelta coincidono cifra per cifra.
  Note:
- [ ] **(4r) Free: confronta TotalCard e CategoryCard con l'aspetto di prima dell'estrazione dei componenti condivisi (piano 10-07)** — nessuna regressione visiva: spaziature, font, colori invariati.
  Note:

## Criterio 5: il budget non muove il prezzo

- [ ] **Stessa stima Free con budget 30.000, poi 90.000, poi nessun budget; annota totale, cifre delle categorie e forma della barra** — totale, categorie e segmento della barra sono identici in tutti e tre i casi; cambiano solo tacca e avviso.
  Note:
- [ ] **Cambia le finiture (es. da "alto" a "medio") mantenendo lo stesso budget** — il prezzo cambia (le finiture muovono il prezzo) mentre il budget da solo no: due assi distinti.
  Note:
- [ ] **Leggi la nota sotto l'avviso** — compare "Il budget non cambia il prezzo della stima."
  Note:
- [ ] **Confronta il "Con finiture medie" dell'avviso con una stima rifatta da zero a finiture medie** — l'importo del confronto coincide con quello della stima rifatta (ricalcolo vero, non proporzione).
  Note:

## PDF (rendering reale, da guardare a occhio)

Richiede WeasyPrint/GTK3 funzionante; se il download del PDF da' errore su questo PC annotalo
in `Note:` e prova su un ambiente con GTK3 (Render).

- [ ] **PDF Free senza budget: scarica dalla stima salvata** — barra proporzionale statica, €/m² e peso per categoria con mini-barra, riepilogo Imponibile / IVA per aliquota / Costi extra / Totale IVA inclusa; nessuna tacca; nessun riquadro budget.
  Note:
- [ ] **PDF Free con budget sotto il minimo** — tacca "Il tuo budget" sulla barra e riquadro avviso con gli stessi testi del web (titolo, righe Ora / Con finiture, nota); il riquadro non ha campi ne' bottoni.
  Note:
- [ ] **PDF Free con budget dentro il range e con budget sopra il massimo** — stati "al limite" e "Rientri nel tuo budget" con testi corretti.
  Note:
- [ ] **PDF Pro senza budget e con budget** — barra sul totale IVA inclusa, tacca se c'e' budget, €/m² e peso per categoria (non per arredo), riepilogo IVA, riquadro avviso su base IVA inclusa; nessun campo o bottone.
  Note:
- [ ] **PDF di una stima salvata prima della Fase 10** — si genera senza errori; niente avviso budget, nessuna riga extra inventata.
  Note:
- [ ] **Cerca nei PDF (Free e Pro) le parole "coefficiente", "prezzo impresa", "impresa"** — non compaiono (T-10-25, regola di dominio 1). Usa la ricerca testo del lettore PDF.
  Note:
- [ ] **Guarda nelle schermate web (Free e Pro) e nei dettagli di rete del browser (tab Rete, risposta di POST /stima e GET dettaglio Pro)** — nessun campo con nomi coefficiente / prezzo impresa / effettivo.
  Note:

## Mobile 360px

- [ ] **Free a 360px di larghezza (DevTools, modalita' dispositivo)** — le righe del riepilogo, le card e l'etichetta "Il tuo budget" della tacca non escono dal contenitore; niente scroll orizzontale.
  Note:
- [ ] **Vista Pro web a 360px** — riepilogo IVA, barra con tacca e avviso non escono dal contenitore; nessuno scroll orizzontale.
  Note:
- [ ] **Budget molto alto (oltre 1,2 x massimo) a 360px** — l'etichetta della tacca resta interamente visibile, senza tagli.
  Note:

## Scelte di Claude da confermare

Decisioni di discrezione prese durante l'esecuzione. Conferma o correggi.

- [ ] **Budget salvato con PATCH `/me/stime/{id}/budget`** (non PUT), in colonna `stima.budget_eur` (migrazione 0024) e fuori da `risultato_json`, per evitare una doppia verita' dopo la modifica — ok?
  Note:
- [ ] **Peso della categoria calcolato solo sul totale delle categorie**, senza extra ne' arredo (denominatore del peso, scelta A3) — ok?
  Note:
- [ ] **Etichetta del livello nel confronto Pro: il livello inferiore della categoria col livello piu' alto** (scelta A4), es. "Con finiture medie" — ok?
  Note:
- [ ] **Testo "meno lavori" (A6)**: quando non esiste un livello inferiore che costa meno, l'avviso dice "Per stare nel tuo budget servono meno lavori: prova a togliere qualche intervento." — ok il tono e la formulazione?
  Note:
- [ ] **Budget come campo fisso allo step 3 del wizard** (non domanda di catalogo, A1): facoltativo, IVA inclusa, non passa dal layer effetti — ok?
  Note:
- [ ] **Confronto a finiture inferiori dal seed attuale**: da "medio" non compare (perche' "base" costa piu' di "medio" nei dati non curati). Accettabile finche' il listino non viene curato, o va sistemato prima del rilascio?
  Note:
- [ ] **Tetto della barra 1,2 x massimo, passi 1000/5000, larghezza minima del segmento 4%** — valori scelti da noi; ok o da cambiare?
  Note:
- [ ] **Totale Pro IVA inclusa = IVA per categoria sulle sole categorie nel totale lavori + extra lordi** — coerente con quello che ti aspetti dal Pro?
  Note:

## Esito

- [ ] **Tutte le voci sopra sono spuntate senza note bloccanti** — rispondi "approvato"; altrimenti incolla le voci con le Note.
  Note:
