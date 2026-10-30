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

| Caso | Edile reale | Scarto bozza | Scarto tarato | Totale lavori tarato | Errore voce per voce (bozza → tarato) | Totale reale nel range (bozza → tarato) |
|---|---:|---:|---:|---:|---:|---|
| 01 appartamento, totale | 65.572 | +16% | **+3%** | +6% | 39.080 → 20.287 | sì → sì |
| 02 appartamento, parziale | 13.970 | +2% | **+6%** | +1% | 15.024 → 12.052 | sì → sì |
| 03 negozio, bagno nuovo (frontiera) | 18.060 | +21% | **+3%** | +3% | 14.621 → 7.864 | no → sì |
| 04 appartamento, totale, solo edile | 82.340 | 0% | **−5%** | −5% | 40.624 → 25.591 | sì → sì |

Imponibile in euro. L'"errore voce per voce" è la somma degli scarti assoluti delle voci di
A-EDILE con le quantità del motore ai prezzi del file. Misura le quantità e non i prezzi, e un
errore in più non compensa un errore in meno.

- **Soglia ±15% sull'edile: rispettata** nei tre appartamenti, con la stima un po' sopra il
  reale nei casi 01 e 02 (preferenza di Riccardo: meglio leggermente sopra, ma nel range).
- **Totale reale nel range in tutti e quattro i casi.**
- **Le quantità migliorano in tutti e quattro i casi**: l'errore voce per voce scende del 40%
  complessivo (109 k€ → 66 k€).
- **Il caso 04 resta sotto del 5%** per un'impermeabilizzazione a corpo da 4.000 € senza m²
  né indicazione di terrazzi nel file: non si può rispondere alla domanda Pro senza inventare.
- **I totali della bozza tornavano in parte per compensazione.** La tinteggiatura sovrastimata
  copriva assistenze, movimentazione e lavori a corpo sottostimati. Ora ognuna di queste voci ha
  la sua regola o la sua domanda.

Il lavoro è andato in tre passate, tutte nella stessa sessione:

1. quantità (tinteggiatura, battiscopa, voci bagno);
2. decisioni di Riccardo: assistenze, movimentazione, prezzi, IVA, range;
3. domande Pro per i lavori a corpo, "solo predisposizione" per il clima, rivestimenti in
   formato grande, densità dei punti elettrici.

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
4. **Taratura dei dati** (con una sola riga di codice, per mostrare le domande Pro nuove):
   - regole e grandezze: seed + migrazioni `0029_taratura_casi_reali.py` e
     `0030_domande_pro_lavori_a_corpo.py`, che scrivono solo dove il valore è ancora quello
     della bozza;
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
| Leggera | 16,4 → 14,0 k€ | 20,5 → 17,6 k€ |
| Moderata | 32,4 → 32,3 k€ | 41,5 → 40,9 k€ |
| Totale | 39,1 → 39,4 k€ | 69,3 → 69,2 k€ |

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

## Domande Pro per i lavori a corpo (terza passata)

Sei domande nuove nel pannello Pro (gruppo `configuratore_pro`, nessun effetto sul wizard Free)
e un'opzione nuova nel Free. Collegano le voci che il listino aveva già, con la regola a zero in
attesa di una domanda.

| Domanda | Grandezza | Voci |
|---|---|---|
| Quanti bagni crei da zero? (`bagni_nuovi`) | `bagni_smontati` = bagni rifatti − nuovi | Niente rimozione di sanitari (A.0.3-7), linee (A.0.11) e rivestimenti (A.1.10) per i bagni nuovi. |
| Quanti bagni sono senza finestra? (`bagni_ciechi`) | `bagni_ciechi` | Areazione forzata (A.10.13) e foro (A.10.12). |
| Quante aperture nuove o vani da allargare? (`varchi_n`) | `varchi` | Quadratura vano (A.3.8), più un architrave per varco (A.3.6). |
| Quanti metri di velette? (`velette_ml`) | `velette_ml` | Velette in cartongesso (A.5.3). |
| Quanti m² di carta da parati da togliere? (`carta_parati_mq`) | `carta_parati_mq` | Rimozione carta da parati (A.1.11.1). |
| Quanti m² di terrazzi da impermeabilizzare? (`terrazzi_mq`) | `terrazzi_mq` | Rimozione guaina (A.1.12) e membrana bituminosa (A.7.2). |
| Clima: **solo predisposizione** (opzione di `interv_clima`, Free), con "Quanti split vuoi predisporre?" | `clima_predisposizione`, `split_predisposti` | Predisposizione (A.8.21) e linea dedicata (A.8.18), senza montaggio (A.10.1) né macchine (D). |

Nelle fixture le domande sono risposte solo dove il computo lo dice:

- caso 01: 2 bagni nuovi, clima solo predisposto;
- caso 02: 10 ml di velette, 1 varco;
- caso 03: 1 bagno nuovo e cieco;
- caso 04: 3 varchi, 60 m² di carta da parati, clima solo predisposto.

Il pannello Pro ora mostra anche le domande del gruppo `configuratore_pro` senza effetti
(`services/dettaglio_pro.py::domande_configuratore`). È l'unica riga di codice cambiata. Le
regole esistenti le ricollega la migrazione `0030`; domande, opzioni e grandezze nuove le crea
il seed al boot.

Nella stessa passata, sempre per stare un po' sopra il reale, sono cambiati altri due dati:

| Dato | Prima | Dopo | Perché |
|---|---|---|---|
| Posa rivestimenti con finitura base e media | A.6.3 (formati 20-60, 30 €/m²) | **A.6.4** (formati 65-120, 40 €/m²) | Il tecnico usa A.6.4 in 2 computi su 3 (l'altro è il negozio). |
| Punti elettrici | 0,5 per m² commerciale | **0,65** | 0,91 (caso 01) e 0,43 (caso 04): media 0,67. |

Restano fuori, e servono altri computi per decidere:

- le voci di cantiere a corpo (allestimento, sicurezza): nei quattro casi non seguono né i m²
  né l'importo dei lavori;
- un eventuale range asimmetrico.

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
