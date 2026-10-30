# Nota di sessione — 2026-10-30 — taratura sui computi reali (TAR-01)

Sessione cloud su `claude/great-wozniak-1ysani`, partita da `HANDOVER.md`. Il branch era fermo
a `5bd42d0`, prima del merge della PR #4 e del commit con i computi reali: l'ho portato in
avanti su `main` (`1effb73`, solo avanzamento). Risultati e tabelle: `README.md` in questa
cartella.

## Cosa ho fatto, in ordine

1. **Letto l'handover e la proposta** (`docs/proposta-computo-parametrico.md`, in particolare
   §7 e Appendice A) e il motore (`backend/app/services/computo.py`). Ho poi letto
   `seed-computo.json`: 87 grandezze, 192 regole, 33 preset.
2. **Ispezionato i quattro xlsx**: riepilogo, A-EDILE e fogli B/C/D. Ho trovato quattro cose:
   - i file 2025-26 hanno ancora lo smaltimento come `A.9.5`;
   - il tecnico riscrive alcune righe con lavori suoi (porte, caldaia, nicchie, detentori);
   - nel caso 01 i totali di B e C sono a corpo nel riepilogo;
   - nel caso 03 la quantità della movimentazione è scritta a parole ("T").
3. **Scritto `backend/scripts/estrai_casi_reali.py`**: produce
   `backend/tests/fixtures/casi_reali/caso-0N.json`.
   - Riusa la macchina a stati del seed per i codici, e li verifica sulla descrizione.
   - Riconosce B/C/D per descrizione e prezzo.
   - Non legge le colonne impresa.
4. **Dedotto gli input del wizard** per ogni caso dalle quantità e scritto la motivazione di
   ogni deduzione nella fixture: m², piano, bagni, locali, porte, muri, e le risposte alle
   domande d'intervento.
5. **Scritto `backend/scripts/confronta_casi_reali.py`**: confronta il motore con il computo
   per categoria, voce per voce (anche a prezzi del file) e sul range. Produce il report
   Markdown, e lo riusano i test.
6. **Prima misura con la bozza.** L'edile era già nell'ordine giusto: +16%, +2%, +21%, 0%.
   Però voce per voce c'era una sovrastima sistematica della tinteggiatura, in tutti e quattro
   i casi: 2-8 k€ a cantiere. Nei casi 02 e 04 copriva voci sottostimate.
7. **Tarato i dati** in `seed-computo.json`, con la migrazione `0029_taratura_casi_reali.py`
   per i DB già seminati:
   - tinteggiatura;
   - fondo e rasatura;
   - battiscopa;
   - punti acqua;
   - linee idriche a corpo;
   - impermeabilizzazione;
   - montaggio sanitari;
   - lampadari e foro cappa a 0.

   Ho cambiato solo valori con almeno due casi concordi. Nessuna riga di codice del motore.
8. **Non tarato**, perché sono punti aperti del §7 (si segnalano, non si tarano via):
   - A.9.1;
   - A.9.2;
   - A.0.18.

   Ho calcolato a parte uno scenario con i valori che i dati suggeriscono, per la decisione.
9. **Casi d'oro** in `backend/tests/test_casi_reali.py`:
   - soglia ±15% sull'edile;
   - totale reale nel range;
   - voci obbligatorie col bagno rifatto;
   - andata e ritorno della 0029, che non tocca una regola curata dall'admin;
   - nessun dato impresa nelle fixture.
10. **Rigenerato `frontend/src/data/guide-costi.json`** da un DB seminato col seed tarato.
    Aggiornati i numeri di riferimento in `docs/proposta-computo-parametrico.md` §10,
    `docs/stato-progetto.md` e `.planning/STATE.md`, e il test di testa delle migrazioni
    (`0029`).

## Findings principali

1. **Il motore regge.** Numeri della prima passata, prima delle decisioni sotto:
   - l'edile sta entro ±12% sui tre appartamenti: 0%, −9%, −12%.
   - Il negozio sta a +2%.
   - L'errore voce per voce scende del 29% (110 → 78 k€ sommati sui quattro casi); del 34%
     dopo le decisioni sotto.
2. **La tinteggiatura era la sovrastima più grossa.** Il tecnico usa una sola voce (A.11.3,
   ~6,5-8 €/m²) per pareti e soffitti, circa 3,2 m² per m² calpestabile. Il motore metteva
   pareti a parte con la lavabile a 10 €/m², più fondo su tutto e rasatura gonfiata
   dall'intonaco nuovo.
3. **Le assistenze murarie e la movimentazione** sono le voci che oggi tengono il motore
   sotto il reale nei lavori totali. Il tecnico le scrive a corpo:
   - A.9.1 al 39-45% degli impianti;
   - A.9.2 al 47-55% dell'elettrico;
   - movimentazione circa 2.000 € al primo piano, cioè il 10-12% di A.6 × (piano + 1).

   Con A.9.1 al 40%, A.9.2 al 45% e A.0.18 al 12% (minimo 100 €), tutti e quattro i casi
   cadono nel range e l'edile sta entro ±8%. **Serve la conferma del tecnico.**
4. **Prezzi del listino diversi dai computi**:
   - massetto 40 contro 30 €/m² in tutti i casi;
   - punto elettrico 65 contro 47-60 €;
   - sicurezza e allestimento molto variabili.

   È un tema di listino, non di motore.
5. **Domande che mancano**, emerse dai casi:
   - bagno nuovo o rifatto;
   - clima con sola predisposizione;
   - bagno cieco;
   - carta da parati;
   - nicchie e varchi;
   - impermeabilizzazione grande o terrazzo;
   - porte fornite fuori contratto.

   Spiegano quasi tutto lo scarto residuo dei casi 02 e 04.
6. **Il caso 02 era fuori range del 2%** con la prima passata (parziale, range ±10%, circa
   2.100 € di lavori a corpo non chiesti). Rientra con le decisioni sotto.
7. **IVA dei serramenti**: i computi reali la calcolano al 10%, l'app al 22%. Da chiarire.

## Decisioni di Riccardo (stessa sessione) e cosa ne è seguito

1. **Deduzioni degli input**: confermate.
2. **A.9.1 / A.9.2 / A.0.18**: adottati i valori dello scenario, cioè 40% e 45% degli impianti,
   e movimentazione al 12% di A.6 × (piano + 1) con minimo 100 €. Sono nel seed e nella
   migrazione `0029`. Il caso 02 rientra nel range e il suo `xfail` è stato tolto.
3. **IVA dei serramenti**: la regola dei beni significativi dà il 10% sulla manodopera e sul
   bene fino al valore del lavoro, e il 22% sull'eccedenza. C-SERRAMENTI passa al **10%**, che
   è esatto finché i beni significativi non superano il resto dei lavori: è il caso di ogni
   ristrutturazione con un po' di edile.

   **Non modellata l'eccedenza al 22%**, che serve per i lavori di soli serramenti. Richiede:
   - il valore del bene per voce;
   - il calcolo nella stima Free e nel dettaglio Pro;
   - la riga IVA nel riepilogo, backend e frontend.

   È proposta come lavoro a sé (README, sezione "IVA dei serramenti").

   L'oracolo v1 passa da 47.985–70.575 € a 47.251–69.473 €; i test che lo fissano sono
   aggiornati.
4. **Listino**: massetto sabbia-cemento da 40 a **30 €/m²**, punto elettrico ex novo da 65 a
   **60 €**. Il file `docs/computo-base-reggio-emilia.xlsx` ha ancora i prezzi vecchi.
5. **Range**: la leggera passa da ±10% a **±15%**; moderata e totale restano invariate.
6. **Voci a corpo**: si può fare meglio, soprattutto con domande Pro mirate su voci che il
   listino ha già. Coprirebbero circa due terzi dello scarto residuo dei casi 02 e 04. Per le
   voci di cantiere (allestimento, sicurezza) servono più computi, non più regole. Analisi nel
   README, sezione "Voci a corpo".

Esito finale:

- edile 0% / −7% / +2% (negozio) / −11%;
- tutti e quattro i casi nel range;
- errore voce per voce −34% rispetto alla bozza.

Durante la sessione ho corretto anche il report: per le voci in percentuale la colonna "a
prezzi del file" moltiplicava la quantità per un importo a corpo.

## Terza passata: domande Pro e clima (richiesta di Riccardo)

Riccardo ha chiesto le domande Pro per i lavori a corpo e l'opzione clima, con una preferenza:
**meglio una stima leggermente più alta del reale, ma dentro il range**.

1. **Sei domande Pro** nel gruppo `configuratore_pro`, quindi solo nel pannello Pro:
   - bagni nuovi;
   - bagni ciechi;
   - varchi;
   - velette;
   - carta da parati;
   - terrazzi.

   Collegano voci che il listino aveva già, con la regola a zero.
2. **"Solo predisposizione"** come opzione di `interv_clima` nel Free, con una domanda gemella
   "Quanti split vuoi predisporre?". La visibilità condizionata accetta una sola opzione, e
   la domanda sugli split montati resta legata a "split".
3. **Una riga di codice**: `domande_configuratore` mostra anche le domande attive del gruppo
   `configuratore_pro` senza effetti Pro, che il computo legge come grandezze.
4. **Rivestimenti in formato grande (A.6.4)** con finitura base e media, come il tecnico in 2
   computi su 3. **Punti elettrici a 0,65 per m²**, media dei due casi utilizzabili.
5. **Migrazione `0030`** per i DB già seminati, con le stesse garanzie della 0029: scrive solo
   sui valori del seed precedente, è reversibile e testata in andata e ritorno.
6. **Test**: domande nel pannello, ogni risposta Pro porta la sua voce, un bagno nuovo non
   smonta niente, il clima predisposto non monta né fornisce split.

7. **Un bug trovato dai test e corretto prima del push finale.** Il primo modo di passare ad
   A.6.4 spostava gli effetti di finitura: A.6.3 restava senza un'opzione che la includesse,
   quindi usciva dall'asse ed entrava sempre, e la posa dei rivestimenti si sommava. Rompeva
   anche gli invarianti della migrazione 0023. Ora è fatto con effetti nuovi (includi A.6.4,
   escludi A.6.3) su base e medio, e i numeri sono quelli veri. Il commit `583810c` aveva
   ancora la versione col bug, e i numeri +3 / +6% della prima stesura di questa nota
   venivano da lì.

Esito:

- edile 0% / +5% / 0% (negozio) / −7%;
- totale lavori +4% / 0% / 0% / −6%;
- tutti e quattro i casi nel range;
- errore voce per voce −43% rispetto alla bozza.

Il caso 04 resta sotto per lavori che il file non spiega, soprattutto l'impermeabilizzazione a
corpo da 4.000 € senza m².

Sulla preferenza "meglio un po' sopra", i dati non giustificano altri aumenti voce per voce:
il motore sta sul reale. Per spostare la stima verso l'alto senza inventare quantità serviva
un range asimmetrico: è la quarta passata.

## Quarta passata: range asimmetrico −10% / +15%

Riccardo ha scelto un range asimmetrico, −10% / +15%, per tutti e tre i tipi.

- **Dati**: nuova colonna `tipo_ristrutturazione.range_pct_sotto` (migrazione `0031`).
  `range_pct` resta l'ampiezza sopra. NULL vuol dire range simmetrico, così un DB non ancora
  riseminato si comporta come prima. Il seed scrive −10% / +15% a ogni avvio.
- **Calcolo**: stima Free e dettaglio Pro usano le due ampiezze.
- **Pannello Città**: mostra "−10% / +15%" e permette di modificare tutte e due le ampiezze.
- **Compatibilità**: la colonna è `deferred` con `server_default` NULL. Così il seed gira anche
  su un DB fermo prima della 0031, come succede nei test della 0023.
- **Test**: gli oracoli sono aggiornati. Ogni valore nuovo è controllato sul rapporto col
  vecchio (×1,125 sotto, ×0,958 sopra per la totale).
  - Oracolo v1: 52.807–66.696 €.
  - Casi reali: edile +3% / +8% / +2% / −5%, misurato sul centro del range; tutti nel range.

## Punti ancora aperti

1. Eccedenza IVA al 22% dei beni significativi (proposta, non fatta).
2. Limite di 99 sugli stepper del pannello Pro: basta per varchi, velette e terrazzi, ma una
   casa grande può avere più di 99 m² di carta da parati.
3. Il 7% senza etichetta su (B+C+D) nel riepilogo del file (§7).
4. Altri computi reali per le voci di cantiere e per rivedere l'ampiezza del range.
5. PR della taratura e allineamento `stima` dopo il merge.

## Stato

- TAR-01 è fatto. La fase 11 si chiude con il merge della taratura.
- I commit sono sul branch `claude/great-wozniak-1ysani`. Nessuna PR aperta: non è stata
  chiesta.
- Al deploy la migrazione `0029` e il seed cambiano i numeri mostrati agli utenti: 85 m²
  totale da 69,3 a 68,3 k€ imponibili, e IVA dei serramenti al 10%.
