# Checklist — dialog scrollabili, Documentazione, fix Info

Data: 2026-09-25 · Commit: `db15e33`, `5e5e5ad` · Server locali: backend `:8000`, frontend `:5173`

Prima di iniziare: accedi con l'account admin su http://localhost:5173/accedi.
Spunta `[x]` le voci che vanno e scrivi nella riga `Note:` quello che non torna.

## Dialog scrollabili

- [ X] **1. Modifica domanda, finestra bassa.** Riduci l'altezza della finestra del browser,
  apri `/admin/domande` e clicca la matita su una domanda.
  Atteso: il popup si ferma dentro lo schermo, scorre con la rotellina e raggiungi i
  bottoni «Annulla modifica» / «Salva domanda» in fondo.
  Note:

- [X ] **2. Aggiungi effetto.** Dentro una domanda apri un'opzione e poi «Aggiungi effetto».
  Atteso: puoi scorrere fino al bottone Salva; con la finestra alta il popup non ha una
  barra di scorrimento inutile.
  Note: non trovo la voce effetto. controlla. cosi come nelle altre Listini, Coefficienti e Bonus non trovo tutte le voci della tabella da moficare se clicco su modifica.

- [ X] **3. Altri popup.** Apri un popup di modifica in Listini, Coefficienti e Bonus.
  Atteso: si comportano come sopra e niente appare tagliato o spostato.
  Note:

- [X ] **4. Da telefono (facoltativo).** Rifai la voce 1 con la vista mobile del browser.
  Atteso: il popup scorre e la pagina sotto resta ferma.
  Note:

## Pagina Documentazione

- [ X] **5. Voce di menu.** Nella barra laterale admin, in fondo, c'è «Documentazione».
  Atteso: apre `/admin/documentazione`.
  Note:

- [ X] **6. Contenuto.** Leggi «Come ragiona la stima», «Come sono collegate le tabelle» e
  «Modificare tanti valori con Excel», poi apri la sezione di ciascuna pagina.
  Atteso: ogni campo che vedi nelle pagine admin è spiegato. Segna nelle note quello che è
  poco chiaro, sbagliato o mancante.
  Note:

- [X ] **7. Link.** In una sezione clicca «Apri la pagina».
  Atteso: porta alla pagina admin giusta.
  Note:

## Import Excel (fix delle Info della review)

- [ x] **8. Round-trip a vuoto.** In Coefficienti: «Scarica parametri», poi ricarica lo stesso
  file senza modificarlo e conferma.
  Atteso: il messaggio dice 0 righe applicate. Prima diceva il numero di tutte le righe del
  file.
  Note: ok, pero non mi fa cliccare su conferma import, che mi va bene eh, epro e' corretto?

- [ X] **9. Una modifica.** Cambia un solo moltiplicatore nel file, ricaricalo e conferma.
  Atteso: 1 riga applicata, e il valore nuovo si vede in Coefficienti → Moltiplicatori.
  Note:

## Anteprima

- [ X] **10. Oracolo nel pannello.** In Coefficienti → Anteprima: Reggio Emilia, 85 m², tipo
  **totale**.
  Atteso: 47.985 – 70.575 €. Via API è già verificato; qui si controlla la schermata.
  Note:
