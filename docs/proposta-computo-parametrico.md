# Proposta — computo parametrico guidato dalle domande

> Studio di `2025_Computo Base_ER_PREZZI IMPRESE DEFINITI (2) (1).xlsx` (radice del repo)
> confrontato con il motore attuale (`effetti.py`, `dettaglio_pro.py`, seed e migrazioni fino alla 0024).
> Data: 2026-10-21.
>
> **Stato (2026-10-21):** approvata e implementata nella fase 11 (milestone v3.0). Decisioni di
> Riccardo: Free derivato dallo stesso motore, tutte le domande nuove nel Free, tipo come preset,
> computi reali per la taratura da cercare. Cosa è stato fatto e cosa resta: §10.

## 1. Cosa porta di nuovo il file

Rispetto a `docs/computo-base-reggio-emilia.xlsx` il file cambia in tre punti, tutti nel foglio `A-EDILE`:

- **Colonna U, "collegamento"**: per quasi ogni voce dice **da cosa dipende la quantità**. Può essere un
  dato della casa ("N. bagni", "metratura o vani", "n. porte", "n. finestre", "N. stanze"), una scelta
  dell'intervento ("Se canalizzato", "Tipo impianto raffrescamento", "Ristr. completa o parziale, con o
  senza cucina", "Tipo di mattonella scelto") oppure **un'altra voce** ("A.1.5" per i massetti,
  "A3.1, A3.2" per l'intonaco, "A.8, A.9.6" per le demolizioni).
- **Colonna T**: `Collegamento` / `Fisso` / **`Questa voce la toglierei`** (A.1.13 gradini, A.1.15 varco
  su solaio, A.1.16 scala interna, A.2.4 vespaio). In T48 c'è una nuova taratura della movimentazione:
  "circa 2000-2500 per app. da 100 m², per piano".
- **Correzioni**: il codice duplicato `A.9.5` dello smaltimento diventa `A.9.6`; sparisce la nota
  "assistenza per appartamento circa 3500 €" (ex T159).

Le colonne T e U, insieme alle note della colonna H ("deve essere presente se…", "calcolare così…"),
sono **il ragionamento del tecnico scritto in prosa**. Oggi l'app non ne usa quasi nulla.

## 2. Cosa fa oggi il motore e dove si discosta

### Il numero

Il motore Pro attuale, su DB costruito come in produzione (seed, poi migrazioni fino alla 0024), per
**85 m², ristrutturazione totale, risposte di default**, restituisce:

| | Pro attuale |
|---|---|
| A-EDILE | 293.031 – 439.549 € |
| C-SERRAMENTI | 84.584 – 126.876 € |
| **Totale** | **386.027 – 579.042 €** |

L'oracolo Free sullo stesso caso è 47.985 – 70.575 €. Ricostruendo a mano lo stesso appartamento con le
regole del file (1 bagno, 3 locali + cucina, 5 porte, piano 2, gres, radiatori, 2 split), l'**edile
imponibile viene circa 42.400 €**. Il Pro sovrastima di 7-10 volte. Il codice non ha bug: è la struttura
dati a non poter esprimere il ragionamento del file.

### Le cinque cause strutturali

1. **La quantità dipende solo da `(m², tipo)`.** `CoefficienteQuantitaVoce` dà a ogni voce un
   "quantità per m²" preso da nove classi generiche (pavimento, pareti_soffitti, demolizione…), scalato
   0,4/0,7/1 per leggera/moderata/totale. Una ristrutturazione leggera non è una totale fatta al 40%:
   **lavora su voci diverse**.
2. **Le alternative si sommano.** Gli assi esistono solo per finitura e pavimento. Tutto il resto si
   somma: tre demolizioni di muratura (pieni + forati + cartongesso), tre massetti, tre murature, tre
   taglie di radiatore, elettrico "modifica" + "ex novo", radiatori + pavimento radiante, split +
   canalizzato, tapparelle PVC + alluminio, porte a battente + scorrevoli.
3. **Voci "a corpo/cad" con coefficiente per m².** A.1.13-16, A.6.11, A.9.3, A.9.4 e A.0.13-15
   ricevono quantità come 42,5 o 72,25. Solo "assistenza singolo ambiente" (750 € × 72,25) fa 54.000 €,
   le quattro voci che il tecnico toglierebbe ne fanno altri 95.000.
4. **Le voci derivate valgono 0.** A.9.1 (30% degli impianti), A.9.2 (35% dell'elettrico), A.9.6 (20%
   delle demolizioni) e A.0.18 (movimentazione = 6% dei pavimenti × piano) hanno prezzo 0 nel seed:
   nel file sono formule su altre righe, e nel modello attuale una voce non può dipendere da un'altra.
5. **Le voci rare sono sempre incluse.** Scala, soppalco, vespaio, guaina, varco su solaio, pompa
   Sanitrit, blocco dell'impianto condominiale: nel file entrano solo "nel caso di…". Nel motore
   attuale entrano sempre.

Ci sono poi due fragilità di manutenzione, già nel debito noto di `PROJECT.md`:

- Gli effetti puntano a `voce.id`, e le voci B/C/D sono identificate **dalla descrizione intera** (gli
  effetti di `tipo_pavimento` usano come chiave "Zoccolino di gres porcellanato…"). Un secondo listino o
  una virgola cambiata rompono il legame.
- **Free e Pro sono due motori tarati separatamente** (€/m² + effetti in euro da una parte, quantità per
  voce dall'altra). Niente li tiene coerenti, e infatti divergono di un ordine di grandezza.

## 3. La proposta: tre livelli, un solo motore

L'idea è tradurre la colonna U in dati. La struttura resta fedele al principio già adottato in v2.0:
**un insieme chiuso di tipi di regola, niente formule libere nelle celle**.

```
  Risposte wizard ──► GRANDEZZE della casa ──┐
  (o default da m²)   (m², pareti, bagni,    │
                      porte, punti acqua…)    ├──► REGOLE per voce ──► quantità ──► prezzo ──► range
  Tipo ristr. ──────► INTERVENTI scelti  ────┘    (catena in ordine
  (= preset)          (bagno sì, elettrico         topologico)
                      rifatto, massetto…)
```

### Livello 1 — Grandezze (cosa misura la casa)

Generalizza `attesa_immobile`, oggi limitata ai conteggi. Ogni grandezza ha un **default calcolato dai
m²** (per fascia o come fattore) che l'utente può sovrascrivere con una risposta:

| Grandezza | Default (bozza da tarare) | Sovrascrivibile da |
|---|---|---|
| `mq_pavimento` | m² × 0,85 (calpestabile) | domanda superficie calpestabile |
| `mq_pareti` | m² × 2,7 | — |
| `mq_soffitti` | = `mq_pavimento` | — |
| `ml_battiscopa` | m² × 0,9 | — |
| `n_bagni`, `n_locali`, `n_porte`, `n_finestre`, `n_portefinestre` | fasce di `attesa_immobile` (esistono) | stepper esistenti |
| `piano` | 1 | stepper esistente |
| `mq_rivestimenti` | n_bagni_rifatti × 18 + cucina × 5 | — |
| `n_punti_acqua` | n_bagni_rifatti × 5 + cucina × 2 | — |
| `n_punti_luce` | m² × 0,55 | — |
| `n_radiatori` | n_locali + n_bagni + 1 | — |
| `mq_serramenti` | n_finestre × 2 + n_portefinestre × 2,5 (minimo 2 m² cad., nota del file) | — |

Il default dai m² è la misura "neutra a riposo" di oggi: chi non risponde ottiene una stima tipica, chi
risponde la stringe.

### Livello 2 — Interventi (cosa si fa)

Sono domande a scelta: **cosa** si rifà, non "quanto". Il **tipo di ristrutturazione diventa un preset**
di queste risposte, non più un moltiplicatore di quantità:

| Intervento | Opzioni | Leggera | Moderata | Totale |
|---|---|---|---|---|
| Pavimenti | mantieni / sovrapponi (autolivellante) / demolisci e rifai (+ massetto) | sovrapponi | demolisci | demolisci |
| Bagni da rifare | 0…n_bagni | 0 | 1 | tutti |
| Cucina (impianti) | no / sì | no | sì | sì |
| Impianto elettrico | nessuno / modifica / rifacimento | modifica | rifacimento | rifacimento |
| Impianto idrico | nessuno / derivazione / collettore | nessuno | derivazione | collettore |
| Riscaldamento | nessuno / smonta-rimonta / radiatori nuovi / pavimento | smonta-rimonta | radiatori | radiatori |
| Clima | nessuno / split (n) / canalizzato (bocchette, air zone) | nessuno | split | split |
| Muri | m² da demolire + tipo (pieni/forati/cartongesso), m² nuovi + tipo (forati/Siporex/cartongesso) | 0 | da risposta | da risposta |
| Controsoffitti | m² (0 di default) | 0 | 0 | 0 |
| Porte interne | mantieni / sostituisci battente / scorrevoli (n) | mantieni | sostituisci | sostituisci |
| Serramenti | mantieni / sostituisci (+ tapparelle PVC/alluminio, cassonetti) | mantieni | mantieni | sostituisci |
| Caldaia nuova | no / sì | no | no | sì |

L'utente vede il preset già compilato e cambia solo ciò che non torna. È anche la risposta naturale a
"Ristr. Completa o parziale" della colonna U.

### Livello 3 — Regole per voce (come si calcola)

Ogni voce ha **una** regola di quantità, scelta da un insieme chiuso di sei tipi, più tre attributi
opzionali:

| Tipo regola | Quantità | Esempi dal file |
|---|---|---|
| `fisso` | q = valore | A.0.2 quadro di cantiere, A.12.1 sicurezza |
| `grandezza` | q = grandezza × fattore | A.11.4 = `mq_pareti`; A.0.3-10 = bagni rifatti; A.8.1 = `n_punti_acqua` |
| `da_voce` | q = Σ quantità di altre voci × fattore | A.4.1 = (A.3.1 + A.3.2) × 2 lati; A.2.x = A.1.5; A.3.4 = A.3.3 |
| `percentuale` | importo = % × Σ importi di voci/sottocategorie | A.9.1 = 30% di idrico+gas+termo+clima; A.9.2 = 35% elettrico; A.9.6 = 20% demolizioni |
| `percentuale_per_grandezza` | importo = % × Σ importi × grandezza | A.0.18 = 6% pavimenti × piano |
| `scaglioni` | prezzo o quantità per fascia di una grandezza | A.8.17 quadro: ≤50 m² 500 €, ≤80 718 €, ≤100 800 €, oltre 814,5 €; A.0.1 allestimento per fascia di m² |

Attributi opzionali:

- **`condizione`**: la voce entra solo se un intervento ha una certa risposta. Riusa gli effetti
  `includi`/`escludi` esistenti.
- **`gruppo_alternativo`**: voci mutuamente esclusive, ne entra una sola, scelta dall'intervento
  (tipo muratura, tipo massetto, modifica/ex novo elettrico, radiatori/pavimento, split/canalizzato,
  battente/scorrevole, PVC/alluminio). È la generalizzazione degli assi `finitura`/`tipo_pavimento`.
- **`minimo` / `a_corpo_sotto`**: soglie scritte nelle note, per esempio "impermeabilizzazione: a corpo
  200 € se pochi metri", "massetto: se non si rifà tutto, a corpo circa 1.800 €", "serramenti: minimo
  2 m²".

Il motore valuta le voci in **ordine topologico**: prima le grandezze, poi le voci `grandezza`/`fisso`,
poi le `da_voce`, infine le `percentuale`. L'admin riceve un errore leggibile se crea un ciclo
(A dipende da B che dipende da A).

### Un solo motore per Free e Pro

Il Free diventa **lo stesso computo** sommato per categoria; il Pro lo mostra voce per voce. Free e Pro
sono quindi coerenti per costruzione, e il €/m² diventa un **risultato** (utile come controllo di
plausibilità) invece di un parametro da tarare a parte. Gli effetti Free in euro (bagni +1.900 €
per bagno in più, piano +350 €…) si sostituiscono con le voci che li generano davvero.

Questo **sposta l'oracolo** 47.985–70.575: va deciso esplicitamente (vedi §8). Per la transizione si
può affiancare un test di coerenza "Free e Pro entro X%" prima di spegnere il vecchio Free.

## 4. Le domande: cosa c'è e cosa manca

Mappa dei driver della colonna U sulle domande del catalogo attuale (`seed-domande.json`):

| Driver nel file (col. U) | Domanda oggi | Azione |
|---|---|---|
| metratura | `superficie_calpestabile` + m² | ok, diventa `mq_pavimento` |
| N. bagni | `bagni` | ok + nuova "quanti ne rifai" |
| n. porte | `porte` | ok + intervento porte (battente/scorrevole) |
| n. finestre | `finestre`, `portefinestre` | ok + intervento serramenti; "quante motorizzare" (A.10.6) |
| N. stanze / vani | `locali` | ok, guida `n_radiatori` e split |
| piano intervento | `piano` | ok, guida A.0.18 invece di +350 €/piano |
| demolizioni e nuove murature | `muri_*` | ok sui m²; **manca il tipo** (pieni/forati/cartongesso, Siporex) |
| Ristr. completa o parziale, con o senza cucina | — | **nuova**: cucina sì/no; preset parziale → A.9.3 |
| Tipo impianto raffrescamento / Se canalizzato | `condizionatori` (solo numero) | **nuova**: split/canalizzato, n. bocchette, n. air zone |
| Tipo riscaldamento | `impianti` (solo "termico") | **nuova**: radiatori/pavimento/smonta-rimonta |
| Elettrico | `impianti` (solo "elettrico") | **nuova**: modifica/rifacimento (A.8.15 vs A.8.16) |
| Tipo di mattonella scelto | `tipo_pavimento` (Pro) | ok; aggiungere formato rivestimenti (A.6.3/4/5) |
| Grandezza appartamento → punti luce | — | derivato da m² (`n_punti_luce`), nessuna domanda |
| Pavimenti: sovrapposizione o demolizione | — | **nuova**: è la scelta che pesa di più (A.1.5/6/7, A.2.x, A.2.5) |

Le domande `impianti` (scelta multipla con moltiplicatori 1,14/1,07…) e `non_rifare` (azzera una
categoria) si assorbono negli interventi: smettono di essere moltiplicatori e diventano scelte che
includono o escludono voci.

## 5. Manutenzione

1. **Articolo ≠ prezzo.** Separare l'"articolo" (codice stabile, descrizione, UM, regola di quantità,
   condizioni, gruppo alternativo), che vale per tutte le città, dal "prezzo di listino" (listino,
   codice articolo, prezzo). Un secondo listino carica **solo prezzi**: le regole si scrivono una
   volta. Risolve il debito "effetti legati agli id di voce".
2. **Codici stabili ovunque**, anche su B/C/D (es. `B.PAV.01`, `C.SER.03`, `D.CLI.02`), e tutti i
   riferimenti per codice, mai per `id` o per descrizione.
3. **L'Excel resta la lingua del tecnico.** Il collega ha già iniziato a scrivere le regole nelle
   colonne T/U: basta strutturarle. Nel foglio A-EDILE (e analoghi B/C/D) le colonne diventano:
   `regola` (uno dei 6 tipi), `driver` (grandezza o codici voce), `fattore`, `condizione`, `gruppo`,
   `minimo`. In più due fogli nuovi: **Grandezze** (default per fascia) e **Preset** (tipo → interventi).
   L'export/import Excel della Fase 08 si estende a questi fogli, con la guardia di staleness che esiste
   già.
4. **Validazione all'import**: driver inesistente, ciclo di dipendenze, gruppo alternativo senza domanda
   che lo governa, voce `cad`/`ac` con regola per m² (la causa n. 3), percentuale senza base. Ogni
   errore indica cella e motivo.
5. **Traccia per voce** nell'anteprima admin: "A.4.1 = 30 m² perché A.3.1 = 15 m² × 2 lati; A.3.1 =
   15 m² perché risposta `muri_da_creare_mq`". Estende la traccia `EffettoApplicato` già presente. È lo
   strumento con cui il tecnico verifica e tara.

## 6. Precisione

1. **Geometria invece di classi.** Pareti, soffitti, battiscopa e rivestimenti derivano da grandezze con
   un significato fisico. Oggi una classe unica `pareti_soffitti` = 2,7 × m² si applica anche ai
   controsoffitti e alle velette (229 m² su 85 m² di casa).
2. **Range per incertezza, non ±% fisso.** Una quantità che viene da una risposta ha banda stretta, una
   che viene da un default ha banda larga. Così più l'utente risponde, più il range si stringe: è anche
   una leva di prodotto per il Pro.
3. **Scaglioni e minimi delle note H** (quadro elettrico, allestimento, impermeabilizzazione a corpo,
   massetto parziale a corpo, minimo 2 m² sui serramenti, CSE/CSP per scaglioni di importo edile).
4. **Taratura su cantieri veri.** I fogli `scheda cantiere` dicono che i computi compilati esistono.
   5-10 computi reali (quantità vere del tecnico + risposte che il cliente avrebbe dato al wizard)
   diventano **casi d'oro** nella suite: per ognuno si misura l'errore per categoria e si tara finché
   sta sotto una soglia (es. ±15% sull'edile). È il modo più rapido per passare dalla bozza a numeri
   difendibili, e sostituisce l'Excel di taratura per classi.
5. **Regole "deve essere presente" come test.** Ogni nota del tipo "questa voce deve essere presente
   nel caso di rifacimento bagno" diventa un test: bagno rifatto ⇒ A.0.3-10, A.0.11, A.7.1, A.8.5 e
   A.10.5 presenti.

## 7. Incoerenze nel file da chiarire con il tecnico

| Dove | Cosa | Domanda |
|---|---|---|
| `Analisi preliminareTOTALI` F28 | `(B+C+D) × 7%` senza etichetta, sommato al totale | Cos'è (gestione, commissione)? Va nel prezzo cliente? |
| A.9.1 | percentuale applicata 30% (col. E), ma col. K dice 0,35 | Quale vale? |
| A.0.18 movimentazione | formula = 6% di A.6 × piano; col. U dice "m², tipo, piano, demolizioni e murature"; T48 dice 2.000-2.500 per 100 m² per piano | Quale delle tre è la regola? |
| A.8.20 | "da integrare sempre con la voce A.19" (non esiste) | Si intende A.9.5? |
| A.8.x | mancano i codici A.8.6, A.8.9, A.8.14 | Voci tolte o da reinserire? |
| A.9.4 | U.M. "n. bocchette" ma "se canalizzato" | Default di bocchette per stanza? |
| A.8.18 | "calcolare sempre 1 linea induzione + 1 clima" | Sempre o solo con cucina/clima? |
| A.5.x | controsoffitti senza driver chiaro (U = "A.8") | Domanda sì/no o m²? |
| B-FINITURE | etichetta "iva 10% INCLUSA" ma formula × 1,22 | 22% confermato? |
| A-EDILE L151 | il totale impresa elettrico somma L145:L148 ed esclude A.8.19-20 | Errore del foglio (solo interno) |
| A.1.13, A.1.15, A.1.16, A.2.4 | "Questa voce la toglierei" | Si tolgono o si tengono come voci da domanda Pro? |

## 8. Decisioni per Riccardo

1. **Free derivato dal computo** (un motore solo, l'oracolo si sposta) oppure Free €/m² tenuto per
   ora con un test di coerenza col Pro?
2. **Tipo di ristrutturazione come preset di interventi** al posto del moltiplicatore di quantità?
3. **Quante domande nuove nel wizard Free** (cucina, pavimenti sovrapposti/demoliti, elettrico,
   riscaldamento, clima) e quante solo nel configuratore Pro?
4. Disponibilità di **5-10 computi reali** compilati da usare come casi d'oro.
5. Le quattro voci "da togliere": via dal listino o solo escluse di default?

## 9. Percorso a tappe (candidata milestone v3.0, fasi da 11)

1. **Modello articolo/prezzo + codici stabili** (migrazione dati, effetti per codice). Nessun cambio
   di numeri.
2. **Grandezze + regole per voce + valutazione topologica + traccia.** Si parte dalle regole
   `grandezza`, `fisso` e `percentuale`, che da sole risolvono le cause 3 e 4.
3. **Interventi e gruppi alternativi; tipo come preset.** Risolve le cause 1, 2 e 5; nuove domande.
4. **Excel strutturato** (colonne regola/driver/…, fogli Grandezze e Preset) con validazione.
5. **Casi d'oro e taratura**; range per incertezza.
6. **Free derivato** (se deciso al punto 1 del §8) e spegnimento dei moltiplicatori Free.

Le tappe 1-2 si possono già fare prima del go-live di un secondo listino, e la 2 da sola porta il Pro
da centinaia di migliaia a ordini di grandezza credibili.

---

## 10. Stato dell'implementazione (fase 11)

Fatto:

- **Modello dati** (migrazione `0025`): `grandezza`, `termine_grandezza`, `valore_grandezza_opzione`,
  `regola_voce`, `sorgente_regola`, `scaglione_regola`, `preset_risposta`. Codici stabili su B/C/D
  (`B.1.1`…); lo smaltimento diventa `A.9.6` (nel seed v2 le due `A.9.5` collassavano in una sola e
  l'assistenza air zone spariva); `A.12.1.` → `A.12.1`.
- **Motore unico** (`backend/app/services/computo.py`): grandezze → interventi → regola per voce,
  sei tipi di regola, valutazione per dipendenze, traccia per voce. Il Free è il computo sommato per
  categoria, il Pro lo mostra voce per voce: i totali coincidono (Free = Pro + IVA).
- **Catalogo** (migrazione `0026` + seed): 18 domande d'intervento nel Free (pavimenti, massetto,
  bagni, cucina, gas, elettrico, collettore, riscaldamento, centralizzato, clima, caldaia, porte,
  blindata, serramenti, tapparelle, zanzariere, controsoffitti, tinteggiatura, tipo di muri nuovi).
  Spenti gli effetti `eur_per_scostamento`, i moltiplicatori di `impianti` e di `livello_finiture`, e
  gli effetti che ora sono voci.
- **Preset**: `GET /domande?tipo=` restituisce i default del tipo; il wizard li riapplica alle domande
  non toccate quando il tipo cambia.
- **Curatela**: Excel del computo (scarica, anteprima con errori per foglio e riga, applica tutto o
  niente) nella scheda "Computo parametrico" della pagina Coefficienti; `GET /admin/computo/validazione`
  e `POST /admin/computo/anteprima` con la traccia di ogni voce.
- **Fallback**: un listino senza regole usa ancora il calcolo €/m² della v1.

Numeri della bozza (Reggio Emilia, 85 m², risposte di default, imponibile senza range):

| Tipo | Edile | Totale lavori |
|---|---|---|
| Leggera | 16,4 k€ | 20,5 k€ |
| Moderata | 32,4 k€ | 41,5 k€ |
| Totale | 39,1 k€ | 67,3 k€ |

Da fare:

- **Taratura sui computi reali** (TAR-01): i valori delle grandezze e dei preset sono una bozza
  ragionata dalle note del file.
- I punti aperti del §7 (7% senza etichetta, A.9.1 al 30% o al 35%, movimentazione).
- Domande non ancora poste: tipo di muro demolito, doccia o vasca, bagni ciechi, carta da parati.
- Range per incertezza (banda stretta sulle quantità risposte).
- Sul `dev.db` locale (catalogo v2 già seminato) gli effetti dell'asse finitura sui sanitari restano
  quelli v2 più quelli nuovi: per avere la curatela pulita si risemina da zero. In produzione il
  catalogo nasce già nella forma v3.

## Appendice A — Regola proposta per ogni voce di A-EDILE

Codici come nel file (il seed usa `A.0.x` per il blocco di allestimento). "Cond." = condizione di
inclusione; "Alt." = gruppo alternativo.

| Voce | Regola proposta | Cond. / Alt. |
|---|---|---|
| A.1 (seed A.0.1) allestimento | `scaglioni` su m² (600 fino a 100 m², poi da tarare) | sempre |
| A.2 (A.0.2) quadro cantiere | `fisso` 1 | sempre (T = Fisso) |
| A.3 a-h (A.0.3-10) rimozione sanitari | `grandezza` bagni_rifatti × 1 per apparecchio presente (doccia o vasca) | bagno rifatto; f lavello = cucina; g scaldabagno = caldaia nuova |
| A.4 (A.0.11) linee idriche | `grandezza` bagni_rifatti × 1 | bagno rifatto |
| A.5 (A.0.12) rimozione porte | `grandezza` n_porte | porte sostituite |
| A.6 a/b/c (A.0.13-15) radiatori | `grandezza` n_radiatori | riscaldamento ≠ nessuno; Alt.: taglia (default b) |
| A.7 a/b (A.0.16-17) rimozione clima | `grandezza` n_clima_esistenti | Alt.: parete alta / bassa |
| A.8 (A.0.18) movimentazione | `percentuale_per_grandezza` 6% di A.6 × piano (o regola T48) | sempre — da chiarire §7 |
| A.1.1 a/b, A.1.2 demolizione muri | `grandezza` muri_da_demolire_mq | Alt.: pieni / forati / cartongesso |
| A.1.3 demolizione controsoffitti | `grandezza` controsoffitti_da_rimuovere_mq | da domanda (default 0) |
| A.1.4 spicconatura intonaco | `grandezza` muri_da_recuperare_mq | muri_lavori = sì |
| A.1.5 demolizione pavimento + sottofondo | `grandezza` mq_pavimento × quota rifatta | pavimenti = demolisci |
| A.1.6 / A.1.7 demolizione gres / parquet | `grandezza` mq_pavimento | pavimenti = demolisci senza massetto; Alt.: gres / parquet esistente |
| A.1.8 / A.1.9 demolizione battiscopa | `grandezza` ml_battiscopa | Alt.: legno / ceramica esistente |
| A.1.10 demolizione rivestimenti | `grandezza` mq_rivestimenti | bagno o cucina rifatti |
| A.1.11 a/b carta da parati | `grandezza` mq_carta (default 0) | domanda Pro |
| A.1.12 guaina | `grandezza` (default 0) | domanda Pro (terrazzi) |
| A.1.13 gradini, A.1.15 varco solaio, A.1.16 scala | — | da togliere (col. T) o solo su domanda Pro, default escluse |
| A.1.14 varco muratura strutturale | `grandezza` n_varchi_portanti | muri portanti = sì |
| A.2.1 / A.2.2 / A.2.3 massetti | `da_voce` A.1.5 × 1; `a_corpo_sotto` 1.800 se parziale | Alt.: sabbia-cemento / premiscelato / termoacustico |
| A.2.4 vespaio | — | da togliere (col. T) |
| A.2.5 autolivellante | `da_voce` A.1.6 + A.1.7, oppure mq_pavimento se pavimenti = sovrapponi | pavimenti ≠ demolisci con massetto |
| A.3.1 / A.3.2 / A.3.3 nuove murature | `grandezza` muri_da_creare_mq | Alt.: forati / Siporex / cartongesso |
| A.3.4 isolamento cartongesso | `da_voce` A.3.3 × 1 | opzione isolamento |
| A.3.5 / A.3.7 controtelai | `grandezza` porte_nuove | Alt.: battente / scorrevole |
| A.3.6 architravi | `grandezza` porte_su_muri_nuovi | muri nuovi o spostamento porte |
| A.3.8 quadratura vano | `grandezza` n_varchi | varchi su tramezzi |
| A.4.1 intonaco | `da_voce` (A.3.1 + A.3.2) × 2 | — |
| A.4.2 ripresa intonaco | `da_voce` A.1.10 + A.1.11 + (A.1.1/A.1.2 × fattore tracce) | — |
| A.5.1 / A.5.2 / A.5.3 controsoffitti | `grandezza` controsoffitti_mq (default 0); velette in ml | domanda (oggi 229 m² fissi) |
| A.5.4 soppalco | `grandezza` (default 0) | domanda Pro |
| A.6.1 / A.6.2 posa pavimenti | `grandezza` mq_pavimento | Alt.: asse `tipo_pavimento` (esiste) |
| A.6.3 / A.6.4 / A.6.5 / A.6.6 posa rivestimenti | `grandezza` mq_rivestimenti | Alt.: formato (20-60 / 65-120 / maxi / mosaico) |
| A.6.7 / A.6.8 battiscopa | `grandezza` ml_battiscopa | Alt.: legno / ceramica (esiste) |
| A.6.9 / A.6.10 levigatura marmo / parquet | `grandezza` mq_pavimento | pavimenti = mantieni e levigare |
| A.6.11 taglio porta blindata | `fisso` 1 | pavimenti rifatti e blindata mantenuta |
| A.7.1 impermeabilizzazione bagni | `grandezza` bagni_rifatti × 8 m²; `a_corpo_sotto` 200 € | bagno rifatto |
| A.7.2 membrana bituminosa | `grandezza` (default 0) | domanda Pro (terrazzi) |
| A.8.1 punti acqua | `grandezza` n_punti_acqua | idrico ≠ nessuno |
| A.8.2 braga di scarico | `grandezza` n_wc_spostati (default = bagni_rifatti) | bagno rifatto |
| A.8.3 centralina collettore | `grandezza` ceil(n_punti_acqua / 5) | idrico = collettore |
| A.8.4 pompa Sanitrit | `grandezza` (default 0) | domanda Pro |
| A.8.5 montaggio sanitari | `grandezza` bagni_rifatti × apparecchi | bagno rifatto |
| A.8.7 gas cucina | `fisso` 1 | cucina = sì e piano a gas |
| A.8.8 gas caldaia | `fisso` 1 | caldaia nuova a gas |
| A.8.10 termoidraulico | `grandezza` n_radiatori + 2 (collettore + caldaia, nota H) | riscaldamento = radiatori nuovi |
| A.8.11 modifica termoidraulico | `grandezza` n_radiatori_spostati | riscaldamento = modifica |
| A.8.12 blocco condominiale | `fisso` 1 | impianto centralizzato e modifica |
| A.8.13.1-3 pavimento radiante | `grandezza` mq_pavimento; 13.3 `fisso` 1 | Alt. con A.8.10 |
| A.8.15 / A.8.16 elettrico | `grandezza` n_punti_luce | Alt.: modifica / rifacimento |
| A.8.17 quadro elettrico | `scaglioni` su m² (nota H) | elettrico = rifacimento |
| A.8.18 linee dedicate | `fisso` 2 (induzione + clima, nota H) | elettrico ≠ nessuno — da chiarire |
| A.8.19 / A.8.20 elettrico clima canalizzato | `fisso` 1; `grandezza` n_air_zone | clima = canalizzato |
| A.8.21 predisposizione split | `grandezza` n_split | clima = split |
| A.8.22 predisposizione canalizzato | `fisso` 1 | clima = canalizzato |
| A.9.1 assistenza impianti | `percentuale` 30% di idrico + gas + termo + clima | — |
| A.9.2 assistenza elettrico | `percentuale` 35% di elettrico | — |
| A.9.3 assistenza singolo ambiente | `grandezza` ambienti_rifatti | solo preset parziale; mai insieme a A.9.1/A.9.2 (nota H) |
| A.9.4 / A.9.5 assistenza canalizzato | `grandezza` n_bocchette; n_air_zone | clima = canalizzato (sempre insieme, nota) |
| A.9.6 smaltimento | `percentuale` 20% di A.1 | — |
| A.10.1 montaggio clima | `grandezza` n_split | clima ≠ nessuno |
| A.10.2 smonta-rimonta radiatori | `grandezza` n_radiatori | riscaldamento = smonta-rimonta |
| A.10.3 posa caldaia | `fisso` 1 | caldaia nuova |
| A.10.4 boiler elettrico | `fisso` 1 | Alt. con A.10.3 |
| A.10.5 box doccia | `grandezza` bagni_rifatti con doccia | bagno rifatto |
| A.10.6 motorizzazione serrande | `grandezza` n_finestre_motorizzate (default 0) | domanda Pro |
| A.10.7 / A.10.8 allacci cucina | `fisso` 1 | cucina = sì (gas solo se piano a gas) |
| A.10.9 faretti | `da_voce` A.5.1 × 0,5 al m² | controsoffitti > 0 |
| A.10.10 lampade emergenza | `fisso` 0 (non obbligatorie, nota H) | domanda Pro |
| A.10.11 lampadari | `grandezza` n_locali + n_bagni + 1 | elettrico ≠ nessuno |
| A.10.12 foro areazione | `fisso` 1 + bagni ciechi | cucina = sì / areazione forzata |
| A.10.13 areazione forzata | `grandezza` bagni_ciechi (+ A.10.12 sempre, nota H) | bagno cieco |
| A.11.1 raschiatura | `grandezza` mq_pareti × quota (default 0) | su richiesta (nota H) |
| A.11.2 rasatura | `da_voce` nuove murature + riprese, oppure mq_pareti × quota da tipo | — |
| A.11.3 tinteggiatura soffitti | `grandezza` mq_soffitti | pittura ≠ no |
| A.11.4 / A.11.5 tinteggiatura pareti | `grandezza` mq_pareti | Alt.: lavabile / smalto |
| A.11.6 fondo | `grandezza` mq_pareti + mq_soffitti | pittura ≠ no |
| A.12.1 sicurezza | `fisso` 1 (nota: "per architetto") | sempre |

## Appendice B — Cataloghi B, C, D

- **B-FINITURE**: le quantità vengono dalle stesse grandezze dell'edile (`mq_pavimento`,
  `mq_rivestimenti`, `ml_battiscopa`) **con lo stesso gruppo alternativo** della posa corrispondente:
  scelto il gres 60×60, entrano insieme la fornitura (B) e la posa A.6.1. "Colle e stucchi" =
  `da_voce` somma dei m² posati. I sanitari (rubinetterie, vasi, bidet, piatti, cassette) =
  bagni_rifatti × 1, con un'alternativa a terra / sospeso.
- **C-SERRAMENTI**: porte = `porte_nuove` (Alt. battente / scorrevole) + montaggio come `da_voce`;
  finestre e portefinestre = `mq_serramenti` con minimo 2 m² cad.; tapparelle Alt. PVC / alluminio;
  cassonetti in ml = n_finestre × 1,2; blindata `fisso` 1 su domanda. Oggi i serramenti pesano 85-127 k€
  perché finestre, tapparelle e cassonetti hanno coefficienti per m² e "rimozione controtelaio" è a
  42,5 pezzi.
- **D-PRODOTTI**: clima = Alt. mono / dual / trial split in base a n_split; caldaia vs scaldabagno
  Alt.; termosifoni = n_radiatori; scaldasalviette = bagni_rifatti.
