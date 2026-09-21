# 07-01-SUMMARY — Arredo

**Status:** ✅ Complete (working tree, non ancora committato)
**Requirements:** ARR-01, ARR-02, ARR-03, ARR-04

## Consegnato

**Migrazione `0015`, additiva.** `categoria.nel_totale_lavori` (server_default `1`) e tabella
`forfait_arredo` (`opzione_id` FK → `opzione_domanda`, `livello_code` FK → `livello_finitura`,
`eur_min`/`eur_max`, unique sulla coppia).

**`E-ARREDO` esiste come categoria vera** (ordine 5, IVA 22%, `livello_selezionabile=True`)
ed è esclusa dal totale lavori **da un dato**: `EstimationService.compute()` filtra su
`nel_totale_lavori`. Non ha riga di `listino_categoria` né moltiplicatori, ed è corretto — il
Free non la calcola a €/m².

**`ArredoService`** non conosce il codice della domanda degli ambienti. Chiede a
`effetti.risolvi_scelte()` (estratta da `risolvi_effetti_free`, così la regola di visibilità
esiste in un posto solo) quali opzioni sono scelte, e cerca fra quelle le righe di
`forfait_arredo`. Un test rinomina la domanda e verifica che il totale non si muova.

**Il livello di finitura si riconosce per convenzione**: un'opzione il cui `code` è un
`livello_finitura.code`. Stessa natura di `OPZIONE_VALORE = "valore"`. Senza risposta, il
livello `is_default` (`medio`).

**`StimaResponse.arredo`** è fratello di `totale`, `None` quando non c'è nulla da mostrare,
con il disclaimer **dentro** il payload — quindi nello snapshot congelato e nel PDF.

**Bonus Mobili acceso da flag.** Il router passa al `BonusService` una pseudo-categoria
`E-ARREDO`; il seed aggiunge `bonus_categoria (MOBILI, E-ARREDO, 1)`. `BonusService` non è
stato toccato. Il bonus resta `attivo=False`: accenderlo è una decisione fiscale, e un test
lo accende e verifica base, tetto a 5.000 € e esclusione quando l'arredo manca.

**Frontend**: `ArredoCard` (volutamente più sobria del `TotalCard` — se somigliasse al
totale, l'utente sommerebbe i due numeri), montata in `EstimatePage` e `SavedEstimateDetail`;
`normalizeResponse()` aggiornata (la trappola nota); `arredo: 3` nella mappa
`GRUPPI_PER_STEP`. **PDF**: blocco arredo in `pdf_stima.html`.

## Deviazioni dal piano

Due, entrambe emerse dai test e nessuna delle due prevista:

1. **Il motore Pro scartava male le categorie vuote.** Aggiungendo `E-ARREDO` compariva nel
   dettaglio Pro come card a 0 €. Aggiunta la regola gemella di quella che già scarta le
   sottocategorie svuotate: una categoria **senza nessuna sottocategoria** si salta. Sparirà
   da sola quando la Fase 08 caricherà le voci dell'arredo.
2. **`GET /me/opzioni-pro` offriva il selettore di livello per `E-ARREDO`.** Filtrato anche
   su `nel_totale_lavori`: il selettore serve a scegliere le voci del dettaglio, e l'arredo
   nel dettaglio non c'è. Il suo livello lo sceglie la domanda del wizard.

## Test

Nuovo `tests/test_arredo.py`: **22 test**, verdi. Coprono i sette criteri del piano più il
rinominamento della domanda, l'ordine di catalogo, il forfait disattivato e l'anti-leak sul
nuovo schema.

Aggiornati **cinque oracoli di seed** che dicevano "esattamente 4 categorie" — a mano, uno per
uno, con la ragione scritta accanto. Non allentati a `>= 4`: un oracolo che si adatta da solo
non è più un oracolo.

## Verifica

- **Oracolo primario invariato**: 85 m² · totale · Reggio Emilia → `47.985 – 70.575 €`, con
  `E-ARREDO` seminata. Riconciliazione Σ categorie + extra = totale esatta.
- `npx tsc -b` pulito.
- **Dal vivo**, wizard reale contro il backend reale: cucina + camera a finiture medie →
  totale lavori `47.985 – 70.575 €` e, **accanto e non dentro**, arredo `11.400 – 18.800 €`
  (cucina 8.000–13.000, camera 3.400–5.800) col suo disclaimer.

## Lasciato aperto

- **I 18 forfait sono una bozza**, derivati da prezzi plausibili di mercato e non da listini
  di arredamento reali. Stessa natura dei 52 coefficienti: aggiungono risoluzione, non
  accuratezza, finché non sono confermati.
- **Nessun CRUD admin su `forfait_arredo`**: oggi si curano dal seed o a mano. Il posto
  naturale è la Fase 08, insieme all'export/import Excel.
- **`E-ARREDO` non ha voci Pro**: il dettaglio Pro non mostra l'arredo. È la Fase 08.
- **Bonus Mobili spento**: la riga di mappatura c'è, il flag è di Riccardo.
