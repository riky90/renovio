# Taratura del computo parametrico sui computi reali (TAR-01) — 2026-10-30

Taratura del motore (`backend/app/services/computo.py`) su quattro computi veri del tecnico,
anonimizzati in `docs/casi-reali/`. Piano di partenza: `HANDOVER.md`. La cronaca della sessione
e le decisioni di Riccardo sono in `NOTA-SESSIONE-2026-10-30.md`, in questa cartella.

File di questa cartella:

| File | Cosa contiene |
|---|---|
| `README.md` | Questo report: esito, cosa è stato tarato e perché, cosa resta. |
| `report-bozza.md` | Confronto con lo stato di `main` prima della sessione (computo, prezzi e IVA della bozza). |
| `report-tarato.md` | Stesso confronto dopo la taratura: le 10 voci più lontane per caso, con la traccia del motore. |
| `NOTA-SESSIONE-2026-10-30.md` | Cosa è stato fatto, in ordine, decisioni prese e punti aperti. |

Per rigenerare:

```bash
cd backend
.venv/bin/python scripts/estrai_casi_reali.py        # xlsx -> tests/fixtures/casi_reali/*.json
.venv/bin/python scripts/confronta_casi_reali.py ../.planning/prove/2026-11-taratura/report-tarato.md
```

## Esito in breve

| Caso | Edile reale | Scarto bozza | Scarto tarato | Errore voce per voce (bozza → tarato) | Totale reale nel range (bozza → tarato) |
|---|---:|---:|---:|---:|---|
| 01 appartamento, totale | 65.572 | +16% | **0%** | 39.080 → 23.665 | sì → sì |
| 02 appartamento, parziale | 13.970 | +2% | **−7%** | 15.024 → 12.649 | sì → sì |
| 03 negozio, bagno nuovo (frontiera) | 18.060 | +21% | **+2%** | 14.621 → 9.042 | no → sì |
| 04 appartamento, totale, solo edile | 82.340 | 0% | **−11%** | 40.624 → 26.735 | sì → sì |

Imponibile in euro. L'"errore voce per voce" è la somma degli scarti assoluti delle voci di
A-EDILE con le quantità del motore ai prezzi del file. Misura le quantità e non i prezzi, e un
errore in più non compensa un errore in meno.

- **Soglia ±15% sull'edile: rispettata** nei tre appartamenti. Il negozio è fuori soglia per
  scelta, vedi sotto, ma sta comunque a +2%.
- **Totale reale nel range in tutti e quattro i casi.**
- **Le quantità migliorano in tutti e quattro i casi.** L'errore voce per voce scende del 34%
  complessivo (109 k€ → 72 k€).
- **I totali della bozza tornavano in parte per compensazione.** Nei casi 02 e 04 la
  tinteggiatura sovrastimata (2-8 k€) copriva assistenze, movimentazione e lavori a corpo
  sottostimati. Ora queste voci hanno ognuna la sua regola. Lo scarto residuo (−7%, −11%) è
  quasi tutto in lavori a corpo che il wizard non chiede (sezione "Voci a corpo").

## Come è stato fatto

1. **Estrazione** (`backend/scripts/estrai_casi_reali.py`): ogni xlsx diventa
   `backend/tests/fixtures/casi_reali/caso-0N.json` e contiene:
   - per ogni voce con quantità o totale: codice, UM, quantità, prezzo e totale cliente;
   - i totali del riepilogo.

   I codici di A-EDILE vengono dalla stessa macchina a stati del seed (`extract_a_edile`) e
   sono verificati sulla descrizione:
   - lo smaltimento `A.9.5` dei file 2025-26 è ricondotto ad `A.9.6`;
   - le righe riscritte dal tecnico sono marcate `descrizione_modificata`.

   **Mai** colonne impresa, coefficiente, fee o guadagno: lo verifica un test.
2. **Input del wizard** dedotti dalle quantità e scritti nella fixture (`input`), con la
   motivazione di ogni deduzione (`deduzioni`). Riccardo li ha confermati il 2026-10-30.
3. **Confronto** (`backend/scripts/confronta_casi_reali.py`): `computo_free` ed
   `EstimationService.compute` sugli input del caso, contro il file:
   - per categoria;
   - voce per voce;
   - range.

   Due casi spostano importi fra categorie rispetto al listino, e la fixture lo dichiara
   (`riclassifica`):
   - **caso 02**: le porte sono in edile;
   - **caso 04**: la fornitura della caldaia è dentro A.10.3.

   Lo scarto per categoria si misura a parità di perimetro.
4. **Taratura dei dati, non del codice**:
   - regole e grandezze: seed + migrazione `0029_taratura_casi_reali.py`, che scrive solo
     dove il valore è ancora quello della bozza;
   - prezzi, IVA e range: il seed li riscrive a ogni avvio.
5. **Casi d'oro** in `backend/tests/test_casi_reali.py`.

## Cosa è stato tarato

### Quantità (seed `seed-computo.json` + migrazione 0029)

Valori sostenuti da almeno due casi concordi.

| Dato | Bozza | Tarato | Evidenza nei computi |
|---|---|---|---|
| A.11.3 tinteggiatura | solo soffitti | pareti + soffitti (`superfici_fondo`) | Il tecnico tinteggia tutto con A.11.3 (4 casi su 4); nel caso 04 la descrizione dice "soffitti e pareti". |
| A.11.4 lavabile su pareti | `pareti_tinteggiate` | fattore 0 | Mai usata (0 su 4). |
| `mq_pareti` | 2,9 × calpestabile | **2,2** | m² tinteggiati / m² calpestabili: 5,2 · 2,4 · 3,8 · 2,6, mediana 3,2 = 1 (soffitti) + 2,2. |
| A.11.6 fondo | 100% delle superfici | **40%** | 150 m² su 140 di pavimento (caso 01), 400 su 195 (caso 04), assente nei parziali. |
| `rasatura_mq` | 30% pareti + intonaco nuovo | 30% pareti | 0,71 · 0,73 · 0,53 · 0,51 m² per m² calpestabile, anche con 85 m² di muri nuovi. |
| `ml_battiscopa` | 1,1 × calpestabile | **0,65** | 0,86 (caso 01), 0,46 (caso 04), 0,43 (caso 03). |
| `punti_acqua` | 5 / bagno + 2 / cucina | **4 / bagno + 3 / cucina** | 15, 11 e 4 punti: li riproduce tutti e tre. |
| A.0.11 linee idriche (UM `ac`) | 1 per bagno | **1 a corpo** se si rifà un bagno | 300 € a corpo per due bagni. |
| A.7.1 impermeabilizzazione | 6 m² / bagno | **4 m²** (minimo 200 €) | 450 € per tre bagni, 200 € per uno. |
| A.8.5 montaggio sanitari | 4 / bagno | **3** | 10 per tre bagni, 6 per due. |
| A.10.11 lampadari | `punti_lampadari` | fattore 0 | Mai presenti (0 su 3 elettrici rifatti). |
| A.10.12 foro cappa | 1 con la cucina | fattore 0 | Assente in 3 cucine rifatte su 3. |
| A.9.1 assistenza impianti | 30% | **40%** | A corpo nei totali: 39% (caso 01), 45% (caso 04). Decisione di Riccardo. |
| A.9.2 assistenza elettrico | 35% | **45%** | A corpo nei totali: 47% (caso 01), 55% (caso 04). Decisione di Riccardo. |
| A.0.18 movimentazione | 6% di A.6 × (piano + 1) | **12%**, minimo 100 € | 2.000 € al primo piano (casi 01 e 04), 100-300 € al piano terra. Decisione di Riccardo. |

### Prezzi, IVA e range (seed, riscritti a ogni avvio)

| Dato | Prima | Dopo | Perché |
|---|---|---|---|
| A.2.1 massetto sabbia-cemento | 40 €/m² | **30** | 30 in tutti e tre i computi 2025-26. |
| A.8.16 punto elettrico ex novo | 65 € | **60** | 47 / 55 / 60 nei computi; 60 è il più recente (2026-05). |
| IVA C-SERRAMENTI | 22% | **10%** | Ristrutturazione su abitazione: aliquota agevolata, come nei computi del tecnico. Vedi la sezione "IVA dei serramenti". |
| Range della leggera | ±10% | **±15%** | I parziali hanno più lavori a corpo e meno prevedibili; il caso 02 stava a −11% sul totale. Moderata (±15%) e totale (±20%) invariati. |

Il file sorgente `docs/computo-base-reggio-emilia.xlsx` ha ancora 40 e 65. Se si rilancia
`scripts/extract_dettaglio_pro.py`, i due prezzi vanno rimessi, oppure va aggiornato il file.

### Effetto sui numeri di riferimento

Reggio Emilia, 85 m², risposte di default, imponibile:

| Tipo | Edile bozza → tarato | Totale lavori bozza → tarato |
|---|---|---|
| Leggera | 16,4 → 13,6 k€ | 20,5 → 17,3 k€ |
| Moderata | 32,4 → 30,1 k€ | 41,5 → 38,6 k€ |
| Totale | 39,1 → 37,2 k€ | 69,3 → 66,9 k€ |

L'oracolo v1 (il calcolo €/m², usato solo da un listino senza regole) passa da
47.985–70.575 € a **47.251–69.473 €** per effetto dell'IVA dei serramenti. I test che lo
fissano sono aggiornati.

Anche le cifre delle guide pubbliche (`frontend/src/data/guide-costi.json`) sono rigenerate.

## IVA dei serramenti

La regola (beni significativi, DM 29/12/1999), per lavori su abitazione:

- **10%** sulla manodopera e sul valore del bene fino a concorrenza del costo del lavoro;
- **22%** sull'eventuale eccedenza del valore del bene;
- **4%** per prima casa in nuove costruzioni o eliminazione di barriere;
- **22%** per solo materiale senza posa, per immobili non residenziali o di lusso.

Cosa fa ora l'app: C-SERRAMENTI al 10%, come il tecnico. È esatto quando il valore dei beni
significativi (finestre, porte, caldaia, condizionatori) non supera il resto dei lavori del
contratto, cioè in ogni ristrutturazione con un po' di edile. Nei quattro casi l'eccedenza è
zero.

Non è ancora modellata l'**eccedenza**. Serve per i lavori di soli serramenti o quasi, per
esempio leggera + sostituzione delle finestre: una parte del valore delle finestre andrebbe al
22% e oggi va al 10%. Per modellarla servono:

1. il valore del bene per voce (per finestre e portefinestre "fornitura e posa" è da stimare,
   per esempio 70-80%);
2. il calcolo dell'eccedenza nella stima Free e nel dettaglio Pro;
3. la riga IVA 22% nel riepilogo, sia nel backend sia nel frontend.

È un lavoro a sé, proposto come prossimo passo. Il 4% e gli immobili non residenziali restano
fuori: il wizard prevede solo abitazioni.

## Voci a corpo: si può fare meglio?

Sì, in parte. Lo scarto residuo dei due appartamenti sotto il reale si divide così (imponibile,
motore ai prezzi del file):

| Tipo di scarto | Caso 02 | Caso 04 | Come ridurlo |
|---|---:|---:|---|
| Lavori a corpo che il wizard non chiede: velette, posa parziale, architrave, controtelaio scorrevole (02); impermeabilizzazione grande, nicchie, varchi, carta da parati (04) | −2.100 | −7.000 | **Domande Pro mirate**: le voci esistono già nel listino, con la regola a fattore 0 in attesa di una domanda. |
| Clima con sola predisposizione: il motore monta anche gli split | — | +1.750 | Un'opzione "solo predisposizione" in `interv_clima`. |
| Voci di cantiere a corpo (allestimento, sicurezza) | −100 | −1.600 | Nessuno schema nei 4 casi (sicurezza 500-2.000 € senza legame con m² o importo). Servono altri computi. |
| Densità dei punti elettrici | −1.600 | +800 | Una domanda Pro sui punti, o un conteggio per stanza. |
| Rivestimenti (formato e m²) | −700 | −2.000 | m² di rivestimento per bagno nel Pro (oggi 18 fissi). |

Le domande Pro coprirebbero circa due terzi del residuo dei casi 02 e 04, senza toccare il Free.
Sono, in ordine di peso:

1. impermeabilizzazione di terrazzi e balconi (A.7.2, m²);
2. varchi e modifiche di vani porta (A.3.8, n);
3. velette e controsoffitti nel Pro (A.5.3; `controsoffitti_mq` esiste già);
4. carta da parati (A.1.11, m²);
5. bagno nuovo o rifatto e bagno cieco (A.0.x, A.1.10, A.10.12-13);
6. clima con sola predisposizione.

Per le voci di cantiere servono più computi, non più regole.

Un'alternativa senza domande nuove è un range asimmetrico (per esempio −10% / +20%). Il motore
tende a stare sotto il reale perché i lavori a corpo non chiesti aggiungono costo, non lo
tolgono. Con quattro casi però è prematuro: da rivalutare con i prossimi computi.

## Caso 03: perché è di frontiera

È un negozio: un solo bagno creato da zero in un locale commerciale. Il wizard e i preset sono
pensati per un'abitazione: mancano "bagno nuovo" e "bagno cieco", e un immobile non
residenziale avrebbe IVA al 22%. Si misura e si riporta (+2% sull'edile, totale nel range), ma
non entra nella soglia: il test lo salta con la motivazione scritta nella fixture.

## Incoerenze dei file reali (per il tecnico)

1. **Caso 01: B e C a corpo nel riepilogo.**
   - B-FINITURE vale 15.730 € IVA inclusa contro 11.786 € delle righe del foglio B: ci sono
     3.232 € imponibili in più senza voce.
   - C-SERRAMENTI vale 15.950 € senza nessuna riga nel foglio C.
2. **Caso 02**: il subtotale "TOTALE ASSISTENZA MURARIA" del foglio vale 400 €. Le righe
   sommano 705 € (A.9.1 105 € + A.9.2 600 €). Il totale del riepilogo segue il subtotale.
3. **Caso 03**: la movimentazione ha quantità "T" (piano terra) scritta a parole. L'estrazione
   la tiene come `quantita_testo` e conta il totale.
4. **Quadro elettrico (A.8.17)**: la nota H dà scaglioni da 500 a 814,5 €. Nei computi vale
   500-600 € sempre, anche oltre 100 m² e anche con la sola modifica dell'impianto.
