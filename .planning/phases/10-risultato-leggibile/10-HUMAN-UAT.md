---
status: diagnosed
phase: 10-risultato-leggibile
requirement: RIS-01, RIS-02, RIS-03, RIS-04
source: [10-09-PLAN.md]
started: 2026-09-29T00:00:00Z
updated: 2026-09-29T12:00:00Z
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

- [X ] **Avvia backend e frontend come indicato sopra e apri la home** — la home si apre senza errori in console e senza schermata bianca.
  Note:

## Criterio 1: la RangeBar e' proporzionale ai valori reali

- [ X] **Fai una stima Free: 85 mq, Reggio Emilia, ristrutturazione totale, nessun budget** — la barra sotto il totale ha un segmento colorato che NON e' fisso a filo dei bordi (non piu' i pallini a 12% e 88%); nessuna tacca; sotto il totale solo il link "Aggiungi il tuo budget".
  Note: 
- [ X] **Rifai la stima con un altro tipo di intervento (es. leggera) e confronta la barra a occhio** — posizione e larghezza del segmento cambiano rispetto alla totale; il segmento piu' stretto resta comunque visibile (larghezza minima).
  Note:Nella versione free se faccio mdoifica mi riporta alla schermata iniziale con stima bianca, vorrei si poesse modificare quella gia inserita.
- [ X] **Guarda gli estremi della barra** — le etichette di minimo e massimo sono sotto gli estremi del segmento, leggibili, e corrispondono al range mostrato nel totale.
  Note:No, sono alla fine ma la barra non occupa tutto il box. 
- [X] **Apri il pannello Bonus (detrazioni) se presente nella stima** — la barra del bonus si vede ancora correttamente (secondo chiamante della RangeBar, corretto nel piano 10-01).
  Note:qui vorrei che si vedessa la barra del costo totale con evidenziazto l'impatto dei bonus. 

## Criterio 2: incidenza €/m² e peso per categoria

- [ X **Nella stima Free 85 mq guarda ogni card di categoria** — ogni card mostra "€/m² IVA esclusa" e "% del totale" con una mini-barra.
  Note:
- [ X **Somma a mano le percentuali "% del totale" di tutte le categorie** — la somma e' circa 100 (scarto da arrotondamento); nelle percentuali non entrano extra ne' arredo.
  Note:
- [x] **Controlla un €/m² a mano su una categoria: importo categoria / 85** — coincide con il valore mostrato (range min-max, IVA esclusa).
  Note:sembra che includa l'iva il valore totale mostrato.
- [X] **Riapri una stima salvata prima della Fase 10 da "Le mie stime"** — le card mostrano comunque €/m² e peso (derivati dallo snapshot), nessun errore.
  Note:si, epro nella versione pro non vedo il bonus e' da aggiungere.

## Criterio 3: il riepilogo espone imponibile, IVA ed extra

- [x] **Guarda la TotalCard della stima Free** — righe in ordine: Imponibile lavori, una riga IVA per ogni aliquota (10% e 22%), Costi extra con sotto-elenco delle voci, Totale IVA inclusa.
  Note:
- [x] **Confronta "Totale IVA inclusa" con la cifra sopra la barra** — sono lo stesso importo.
  Note:
- [x] **Cerca una lista extra separata sotto o accanto alla TotalCard** — non c'e': gli extra compaiono solo nel riepilogo.
  Note:
- [x] **Somma a mano Imponibile + righe IVA + Costi extra** — il risultato coincide con il Totale IVA inclusa (scarto al massimo di 1 euro da arrotondamento).
  Note:

## Criterio 4: avviso quando si supera il budget, con confronto a finiture inferiori

- [x] **(4a) Rifai la stima dal wizard con budget 30.000 EUR (step 3), finiture "alto"** — sulla barra compare la tacca "Il tuo budget" a sinistra del segmento; sotto il totale compare l'avviso "La stima supera il tuo budget" con le righe "Ora" e "Con finiture medie" e la differenza a range.
  Note:
- [x] **(4b) Budget dentro il range della stima (un valore tra minimo e massimo)** — avviso "Il tuo budget è al limite" con il testo su finiture come leva; tacca dentro il segmento.
  Note:
- [x] **(4c) Budget sopra il massimo, poi budget maggiore di 1,2 x massimo** — avviso "Rientri nel tuo budget"; la tacca si sposta a destra del segmento; oltre 1,2 x massimo il tetto della barra si allarga e la tacca resta nel contenitore.
  Note:
- [ x **(4d) Finiture economiche ("base") con budget basso** — testo "Hai già scelto finiture economiche. Per stare nel tuo budget servono meno lavori..." senza righe di confronto.
  Note:
- [x] **(4e) Finiture "medio" con budget basso** — nessuna riga "Con finiture..." (il livello sotto non costa meno nel seed); compare il testo "Per stare nel tuo budget servono meno lavori..." senza errori.
  Note:
- [ x **(4f) Scrivi "0" nel campo budget del box e premi "Aggiorna il confronto"** — messaggio in rosso "Scrivi un importo in euro maggiore di zero."; la stima resta calcolata, senza tacca e senza avviso.
  Note:
- [x] **(4g) Premi "Togli il budget", poi "Aggiungi il tuo budget"** — il primo elimina tacca e avviso; il secondo riapre il campo; totale e categorie non cambiano.
  Note:
- [x] **(4h) Da anonimo con budget nel wizard: calcola, registrati, apri la stima salvata** — la stima salvata ha il budget e l'avviso relativo.
  Note:
- [ x **(4i) Da loggato: cambia il budget dal box, poi ricarica la pagina e apri "Le mie stime"** — il budget nuovo e l'avviso sono ancora li'; non ricompare il budget vecchio.
  Note:
- [x] **(4j) Stima salvata prima della Fase 10, aperta da "Le mie stime"** — nessun avviso, solo "Aggiungi il tuo budget"; nessun errore in pagina o in console.
  Note:
- [ x **(4k) Sincronizzazione budget/auto-save: da loggato, appena compare il risultato (entro 1-2 secondi, mentre l'auto-salvataggio e' appena partito) cambia il budget dal box, poi apri "Le mie stime" e riapri quella stima** — il budget mostrato e' quello nuovo, non quello del wizard, e l'avviso corrisponde.
  Note:
- [x] **(4l) Pro web: apri una stima Pro e guarda sotto "Totale generale stimato"** — c'e' il blocco "Totale stimato · IVA inclusa" con barra proporzionale sul totale IVA inclusa e, se c'e' un budget, la tacca "Il tuo budget".
  Note:
- [ x **(4m) Pro web: nello stesso blocco guarda il riepilogo** — Imponibile lavori, IVA per aliquota, Costi extra con sotto-elenco, Totale IVA inclusa; il Totale IVA inclusa e' uguale alla cifra della barra.
  Note:
- [x] **(4n) Pro web: apri l'accordion di ogni categoria nel totale lavori** — sotto la riga "Totale {categoria}" compaiono "€/m² IVA esclusa" e "% del totale" con mini-barra; la voce arredo NON li mostra.
  Note:qui il totale riportato sembra senza iva. 
- [x] **(4o) Pro web: guarda l'avviso budget sotto il blocco** — la riga "Ora (IVA inclusa)" e' sempre visibile; nello stato fuori budget c'e' il confronto col livello inferiore, se il seed lo permette (parti da finiture "alto").
  Note:
- [x] **(4p) Pro web: cambia il budget dal box** — tacca e avviso cambiano; totale, riepilogo, €/m² e peso restano identici. Riapri da "Le mie stime": il budget nuovo e' ancora li'.
  Note:
- [x] **(4q) Pro web contro PDF Pro della stessa stima** — totale IVA inclusa, righe IVA, €/m² e peso di due categorie a tua scelta coincidono cifra per cifra.
  Note:
- [x] **(4r) Free: confronta TotalCard e CategoryCard con l'aspetto di prima dell'estrazione dei componenti condivisi (piano 10-07)** — nessuna regressione visiva: spaziature, font, colori invariati.
  Note:

## Criterio 5: il budget non muove il prezzo

- [x] **Stessa stima Free con budget 30.000, poi 90.000, poi nessun budget; annota totale, cifre delle categorie e forma della barra** — totale, categorie e segmento della barra sono identici in tutti e tre i casi; cambiano solo tacca e avviso.
  Note:
- [x] **Cambia le finiture (es. da "alto" a "medio") mantenendo lo stesso budget** — il prezzo cambia (le finiture muovono il prezzo) mentre il budget da solo no: due assi distinti.
  Note:
- [x] **Leggi la nota sotto l'avviso** — compare "Il budget non cambia il prezzo della stima."
  Note:
- [x] **Confronta il "Con finiture medie" dell'avviso con una stima rifatta da zero a finiture medie** — l'importo del confronto coincide con quello della stima rifatta (ricalcolo vero, non proporzione).
  Note:diverso, se faccio finiture media mi da ad esempio 336111 mentre se faccio lusso midice con opzione medie 337.923

## PDF (rendering reale, da guardare a occhio) — DIFFERITO al go-live su Render

Deciso da Riccardo il 2026-09-29: l'intera sezione si verifica al go-live su Render
(WeasyPrint/GTK3 assenti in locale). Non e' un fallimento: e' una verifica umana differita.

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
- [ ] **PDF Free e PDF Pro: le cifre min e max sotto la barra stanno sotto gli estremi del segmento, dentro il riquadro (G1)** — verifica a occhio al go-live. Vedi G8: nel web le cifre sono tornate ai bordi; decidere se allineare il PDF.
  Note:
- [ ] **PDF Free di una stima salvata con ambienti da arredare** — compare la sezione Arredo con gli stessi importi della card web (G9).
  Note:
- [ ] **PDF Free e PDF Pro: gli importi per categoria sono IVA esclusa e lo dicono in etichetta (Range (IVA esclusa), Totale <categoria> (IVA esclusa)) (G2)** — verifica a occhio al go-live.
  Note:
- [ ] **Cifre della barra ai bordi, Bonus Mobili nel blocco Arredo e stima modificata (G13, G10, G14)**: vedi checklist 2026-09-30-ricollaudo-10-g10-g14, sezione G13
  Note:
- [ ] **Cerca nei PDF (Free e Pro) le parole "coefficiente", "prezzo impresa", "impresa"** — non compaiono (T-10-25, regola di dominio 1). Usa la ricerca testo del lettore PDF.
  Note:
- [ ] **Guarda nelle schermate web (Free e Pro) e nei dettagli di rete del browser (tab Rete, risposta di POST /stima e GET dettaglio Pro)** — nessun campo con nomi coefficiente / prezzo impresa / effettivo.
  Note:

da verrificare con go live
## Mobile 360px

- [x] **Free a 360px di larghezza (DevTools, modalita' dispositivo)** — le righe del riepilogo, le card e l'etichetta "Il tuo budget" della tacca non escono dal contenitore; niente scroll orizzontale.
  Note:
- [ x **Vista Pro web a 360px** — riepilogo IVA, barra con tacca e avviso non escono dal contenitore; nessuno scroll orizzontale.
  Note:
- [x] **Budget molto alto (oltre 1,2 x massimo) a 360px** — l'etichetta della tacca resta interamente visibile, senza tagli.
  Note:

## Scelte di Claude da confermare

Decisioni di discrezione prese durante l'esecuzione. Conferma o correggi.

- [x] **Budget salvato con PATCH `/me/stime/{id}/budget`** (non PUT), in colonna `stima.budget_eur` (migrazione 0024) e fuori da `risultato_json`, per evitare una doppia verita' dopo la modifica — ok?
  Note:
- [x] **Peso della categoria calcolato solo sul totale delle categorie**, senza extra ne' arredo (denominatore del peso, scelta A3) — ok?
  Note:
- [x] **Etichetta del livello nel confronto Pro: il livello inferiore della categoria col livello piu' alto** (scelta A4), es. "Con finiture medie" — ok?
  Note:
- [ x **Testo "meno lavori" (A6)**: quando non esiste un livello inferiore che costa meno, l'avviso dice "Per stare nel tuo budget servono meno lavori: prova a togliere qualche intervento." — ok il tono e la formulazione?
  Note:
- [ x **Budget come campo fisso allo step 3 del wizard** (non domanda di catalogo, A1): facoltativo, IVA inclusa, non passa dal layer effetti — ok?
  Note:
- [x] **Confronto a finiture inferiori dal seed attuale**: da "medio" non compare (perche' "base" costa piu' di "medio" nei dati non curati). Accettabile finche' il listino non viene curato, o va sistemato prima del rilascio?
  Note:
- [ x **Tetto della barra 1,2 x massimo, passi 1000/5000, larghezza minima del segmento 4%** — valori scelti da noi; ok o da cambiare?
  Note:
- [ x **Totale Pro IVA inclusa = IVA per categoria sulle sole categorie nel totale lavori + extra lordi** — coerente con quello che ti aspetti dal Pro?
  Note:

## Esito

- [ x **Tutte le voci sopra sono spuntate senza note bloccanti** — rispondi "approvato"; altrimenti incolla le voci con le Note.
  Note:

## Esito del collaudo (2026-09-29)

Non approvato: 6 gap trovati. Tutto il resto e' passato; le "Scelte di Claude da confermare"
sono tutte confermate. Decisione di Riccardo sullo scope: G1-G6 si fanno ora, dentro la Fase 10,
con `/gsd-plan-phase 10 --gaps`.

## Differito

- PDF (intera sezione): da verificare al go-live su Render (WeasyPrint/GTK3 assenti in locale). Non fallito.

## Gaps

- truth: "Le etichette min/max della RangeBar stanno sotto gli estremi del segmento, dentro il contenitore"
  status: superseded
  reason: "Riccardo: le etichette sono ai bordi del box (flex justify-between in frontend/src/components/RangeBar.tsx), ma il segmento non occupa tutto il box."
  severity: major
  test: "Criterio 1, voce 'Guarda gli estremi della barra' (G1)"
  fix: piano 10-10
  superseded_by: G8 (ri-collaudo 2026-09-30: Riccardo preferisce le cifre ai bordi)
  retest: .planning/checklists/2026-09-29-ricollaudo-10.md

- truth: "Ogni importo per categoria e' IVA esclusa, uguale in Free e Pro (importo categoria, €/m², anche nei PDF); il riepilogo mantiene imponibile + IVA per aliquota + extra + Totale IVA inclusa; le etichette dicono chiaramente 'IVA esclusa'"
  status: resolved
  reason: "Riccardo: il totale della card Free sembra includere l'IVA (CategoryCard mostra totale_min/max IVA inclusa come titolo mentre €/m² usa l'imponibile); nel Pro 'Totale {categoria}' e' IVA esclusa. Base IVA incoerente."
  severity: major
  test: "Criterio 2 voce 'Controlla un €/m² a mano' e Criterio 4 voce 4n (G2)"
  fix: piano 10-10
  retest: .planning/checklists/2026-09-29-ricollaudo-10.md
  decision: "Decisione di Riccardo: tutto per categoria e' IVA ESCLUSA in Free e Pro e nei PDF."

- truth: "'Con finiture medie' dell'avviso coincide con una stima rifatta da zero a finiture medie (ricalcolo vero)"
  status: resolved
  reason: "Riccardo: partendo da 'lusso/alto' il confronto mostra 337.923, una stima nuova a 'medio' da' 336.111. Causa radice sconosciuta: da indagare (altri input/effetti diversi nel ricalcolo, extra calcolati su base diversa, arrotondamenti)."
  severity: major
  test: "Criterio 5, ultima voce (G3)"
  fix: piano 10-11
  fix_note: "G3 riprodotto lato client (wizard, default stepper per fascia di m2), non lato server: vedi 10-11-SUMMARY; caso numerico esatto non replicato"
  retest: .planning/checklists/2026-09-29-ricollaudo-10.md

- truth: "'Modifica' nella stima Free riapre il wizard precompilato con gli input correnti (budget incluso)"
  status: resolved
  reason: "Riccardo: 'Modifica' riporta a un wizard vuoto; vuole modificare la stima gia' inserita."
  severity: major
  test: "Criterio 1, voce 'Rifai la stima con un altro tipo di intervento' (G4, feature)"
  fix: piano 10-12
  retest: .planning/checklists/2026-09-29-ricollaudo-10.md

- truth: "Il pannello Bonus mostra la barra del costo totale con l'impatto di bonus/detrazioni evidenziato"
  status: superseded
  reason: "Riccardo: vuole vedere la barra del costo totale con evidenziato l'impatto dei bonus (al posto di, o in aggiunta a, la barra detrazione autonoma)."
  severity: minor
  test: "Criterio 1, voce 'Apri il pannello Bonus' (G5, feature)"
  fix: piano 10-13
  superseded_by: G7 (ri-collaudo 2026-09-30: solo la barra della detrazione)
  retest: .planning/checklists/2026-09-29-ricollaudo-10.md

- truth: "Il pannello Bonus e' presente anche nella versione Pro"
  status: resolved
  reason: "Riccardo: aprendo una stima Pro non compare il bonus; va aggiunto."
  severity: major
  test: "Criterio 2, voce 'Riapri una stima salvata prima della Fase 10' (G6, feature)"
  fix: piano 10-14
  retest: .planning/checklists/2026-09-29-ricollaudo-10.md

- truth: "Il pannello Bonus mostra una sola barra: il range del valore della detrazione (quanto si recupera), senza barra del costo totale e senza segmento 'Dopo le detrazioni'"
  status: resolved
  reason: "Riccardo (ri-collaudo 2026-09-30, G1d e G5a): due barre (totale e netto) non sono cio' che vuole; dopo averci ripensato: 'togli il totale, lascia la barra solo del valore del bonus'."
  severity: minor
  test: "Ri-collaudo G1(d), G5(a) (G7)"
  fix: piano 10-16
  retest: .planning/checklists/2026-09-30-ricollaudo-10-g7-g9.md

  resolved_note: "ri-collaudo 2026-09-30 pomeriggio: passa; il Bonus Mobili si sposta nella card Arredo (G10)"
- truth: "Le cifre min/max della RangeBar stanno ai bordi del contenitore, come prima di 10-10"
  status: resolved
  reason: "Riccardo (ri-collaudo 2026-09-30, G1a): 'lo preferivo prima'; confermato in chat: tornare ai bordi."
  severity: cosmetic
  test: "Ri-collaudo G1(a) (G8)"
  fix: piano 10-16
  retest: .planning/checklists/2026-09-30-ricollaudo-10-g7-g9.md

  resolved_note: "ri-collaudo 2026-09-30 pomeriggio: passa sul web; PDF in G13"
- truth: "Lo snapshot di una stima salvata contiene l'arredo (StimaSalvataCreate ha il campo), cosi' ArredoCard e la base Bonus Mobili del Pro usano dati reali"
  status: partial
  reason: "Difetto trovato in 10-14 e differito; Riccardo (2026-09-30): correggerlo ora, dentro la Fase 10."
  severity: major
  test: "Scelte di Claude, ultima voce del ri-collaudo (G9)"
  fix: piano 10-17
  retest: .planning/checklists/2026-09-30-ricollaudo-10-g7-g9.md
  resolved_note: "Free ok; Pro da Le mie stime no (G11); Modifica duplica la stima (G12)"

- truth: "Il Bonus Mobili compare dentro la card Arredo (range), non nel pannello Bonus; la barra del pannello Bonus mostra solo la detrazione sui lavori"
  status: failed
  reason: "Riccardo (ri-collaudo 2026-09-30 pomeriggio, G7c): 'metterlo non insieme agli altri bonus ma dopo gli arredi, essendo che gli arredi non sono inclusi'; in chat: dentro la card Arredo."
  severity: minor
  test: "Ri-collaudo G7(c) (G10)"
  fix: piani 10-19, 10-20, 10-21
  retest: .planning/checklists/2026-09-30-ricollaudo-10-g10-g14.md

- truth: "Con account Pro, la stima aperta da 'Le mie stime' mostra la card Arredo e il Bonus Mobili come /dettaglio-pro"
  status: failed
  reason: "Riccardo (G9b, G9d): con account free la card Arredo c'e', con account pro no; 'se faccio vedi dettaglio pro si, se lo guardo dalle mie stime no'."
  severity: major
  test: "Ri-collaudo G9(b), G9(d) (G11)"
  fix: piano 10-21
  retest: .planning/checklists/2026-09-30-ricollaudo-10-g10-g14.md

- truth: "Modifica + ricalcolo senza cambiare nulla non crea una seconda stima salvata (si riusa l'id)"
  status: failed
  reason: "Riccardo (G9c): 'se premo modifica poi vado a vedere le stime mi ha creato 2 stime'. Regressione rispetto a G4c. Causa radice da trovare (stessaRichiesta in EstimatePage.tsx, default del wizard dopo Modifica, arredo nella richiesta?)."
  severity: major
  test: "Ri-collaudo G9(c) (G12)"
  fix: piani 10-22, 10-23
  root_cause: "race su reset() in TanStack Query v5: il callback per-call di mutate non parte se Modifica e' premuto con il POST in volo, ultimoSalvataggio resta null e il ricalcolo salva due volte (10-22); sul percorso Modifica i doppioni sono esclusi per costruzione dal flusso G14, che fa PUT e mai POST"
  retest: .planning/checklists/2026-09-30-ricollaudo-10-g10-g14.md

- truth: "Nei PDF (Free e Pro) le cifre min/max della barra stanno ai bordi, come sul web"
  status: failed
  reason: "Riccardo (scelta G8 sul PDF): 'Si, ai bordi'. Verifica a occhio al go-live (WeasyPrint assente in locale)."
  severity: cosmetic
  test: "Ri-collaudo, scelta G8 (G13)"
  fix: piano 10-20
  retest: .planning/checklists/2026-09-30-ricollaudo-10-g10-g14.md

- truth: "'Modifica' seguita da ricalcolo aggiorna la stima salvata da cui si e' partiti (stesso id in 'Le mie stime'), anche con input cambiati; non nasce una stima nuova"
  status: failed
  reason: "Riccardo (chat 2026-09-30, chiarendo la nota G9c 'non modificato la mia attuale'): 'Aggiorna l'attuale'. Supera la regola di 10-12 (input diversi = stima nuova, la precedente resta), approvata il 2026-09-29."
  severity: major
  test: "Ri-collaudo G9(c) e chat (G14)"
  fix: piano 10-23
  retest: .planning/checklists/2026-09-30-ricollaudo-10-g10-g14.md

- truth: "Una stima salvata da Free, aperta da 'Le mie stime' da un utente diventato Pro, resta visibilmente Free: banner 'creata con il piano Free' e lucchetto 'Dettaglio con Pro' sulle card categoria"
  status: failed
  reason: "Riccardo (ri-collaudo 2026-10-01, G14f): 'quando la riapro dalle mie stime anche se era free la vedo pro, non va bene'. Chiarito in chat: la stima non aveva il badge Pro (tier in DB rimasto free), ma dentro mancava il lucchetto sulle card."
  severity: minor
  test: "Ri-collaudo G14(f) (G15)"
  root_cause: "LeMieStimePage passava a SavedEstimateDetail il piano dell'UTENTE (isPro={isUtentePro}) invece di quello della STIMA. Era il fix P5 del 2026-08-27, quando anche le stime Pro si aprivano nella vista snapshot; dalla Fase 03 le stime Pro aprono DettaglioProView, quindi la vista snapshot mostra solo stime Free e il teaser va sempre mostrato."
  fix: "inline 2026-10-01 (nessun piano): il lucchetto resta sempre; per un utente Pro il link diventa 'Rifai in versione Pro' (stessa destinazione del banner) invece di 'Passa a Pro'. Verificato nel browser con l'utente 9: stima Free con lucchetto e link a /nuova-stima, stima Pro sempre su DettaglioProView senza teaser."
  retest: "voce G14(f) della checklist 2026-09-30-ricollaudo-10-g10-g14"
