# Taratura del computo parametrico sui computi reali (TAR-01) — 2026-10-30

Prima taratura del motore (`backend/app/services/computo.py`) su quattro computi veri del
tecnico, anonimizzati in `docs/casi-reali/`. Piano di partenza: `HANDOVER.md`. La cronaca della
sessione è in `NOTA-SESSIONE-2026-10-30.md`, in questa cartella.

File di questa cartella:

| File | Cosa contiene |
|---|---|
| `README.md` | Questo report: esito, cosa è stato tarato e perché, cosa no. |
| `report-bozza.md` | Confronto con i valori della bozza (seed prima di questa sessione). |
| `report-tarato.md` | Stesso confronto dopo la taratura: le 10 voci più lontane per caso, con la traccia. |
| `NOTA-SESSIONE-2026-10-30.md` | Cosa è stato fatto, in ordine, e le domande aperte per Riccardo. |

I due report si rigenerano con:

```bash
cd backend
.venv/bin/python scripts/estrai_casi_reali.py        # xlsx -> tests/fixtures/casi_reali/*.json
.venv/bin/python scripts/confronta_casi_reali.py ../.planning/prove/2026-11-taratura/report-tarato.md
```

## Esito in breve

| Caso | Edile reale | Bozza | Tarato | Errore voce per voce (bozza → tarato) | Totale reale nel range |
|---|---:|---:|---:|---:|---|
| 01 appartamento, totale | 65.572 | +16% | **0%** | 39.080 → 25.858 | sì |
| 02 appartamento, parziale | 13.970 | +2% | **−9%** | 14.933 → 12.286 | **no** (−2% sotto il massimo) |
| 03 negozio, bagno nuovo (frontiera) | 18.060 | +21% | **+2%** | 14.484 → 9.349 | sì |
| 04 appartamento, totale, solo edile | 82.340 | 0% | **−12%** | 41.762 → 30.451 | sì |

Imponibile in euro. L'"errore voce per voce" è la somma degli scarti assoluti delle voci di
A-EDILE con le quantità del motore ai prezzi del file. Misura le quantità e non i prezzi, e un
errore in più non compensa un errore in meno.

- **Soglia ±15% sull'edile: rispettata** nei tre appartamenti. Il negozio (caso 03) è fuori
  soglia per scelta, vedi sotto.
- **Totale reale nel range: 3 casi su 4.** Il caso 02 resta fuori di circa il 2%. Il test lo
  marca `xfail(strict=True)` con la causa.
- **Le quantità migliorano in tutti e quattro i casi.** L'errore voce per voce scende del 29%
  complessivo (110 k€ → 78 k€).
- **Una precisazione onesta.** Con la bozza, i totali edile dei casi 02 e 04 tornavano per
  compensazione: la tinteggiatura era sovrastimata di 2-8 k€ e copriva voci sottostimate. Tolta
  la sovrastima, restano scoperte proprio quelle voci. Sono quasi tutte nei punti aperti del §7
  della proposta (assistenze murarie, movimentazione) o in lavori che il wizard non chiede.
  Lo scenario più sotto mostra cosa succede se il tecnico conferma i valori che i dati
  suggeriscono.

## Come è stato fatto

1. **Estrazione** (`backend/scripts/estrai_casi_reali.py`): ogni xlsx diventa
   `backend/tests/fixtures/casi_reali/caso-0N.json` e contiene:
   - per ogni voce con quantità o totale: codice, UM, quantità, prezzo e totale cliente;
   - i totali del riepilogo.

   I codici di A-EDILE vengono dalla stessa macchina a stati del seed (`extract_a_edile`) e
   sono verificati sulla descrizione:
   - lo smaltimento `A.9.5` dei file 2025-26 è ricondotto ad `A.9.6`;
   - le righe riscritte dal tecnico sono marcate `descrizione_modificata` (per esempio
     "Sostituzione detentori" nel posto di A.8.10, o "5 porte battenti" nel posto di A.10.9).

   **Mai** colonne impresa, coefficiente, fee o guadagno: lo verifica un test.
2. **Input del wizard** dedotti dalle quantità e scritti nella fixture (`input`), con la
   motivazione di ogni deduzione (`deduzioni`). Lo script li conserva se si rilancia
   l'estrazione.
3. **Confronto** (`backend/scripts/confronta_casi_reali.py`): `computo_free` ed
   `EstimationService.compute` sugli input del caso, contro il file:
   - per categoria;
   - voce per voce, con quantità, importo, importo a prezzi del file e traccia del motore;
   - range.

   Due casi spostano importi fra categorie rispetto al listino, e la fixture lo dichiara
   (`riclassifica`):
   - **caso 02**: le porte sono in edile (A.10.9);
   - **caso 04**: la fornitura della caldaia è dentro A.10.3.

   Lo scarto per categoria si misura a parità di perimetro, e il totale non cambia.
4. **Taratura dei dati, non del codice**: seed `backend/seed_data/seed-computo.json` e
   migrazione `0029_taratura_casi_reali.py` per i DB già seminati. La migrazione scrive solo
   dove il valore è ancora quello della bozza.
5. **Casi d'oro** in `backend/tests/test_casi_reali.py`.

## Le deduzioni da confermare

Sono la parte più fragile: una deduzione sbagliata falsa la taratura. Il dettaglio è nelle
fixture (`deduzioni`). Le più incerte:

| Caso | Deduzione | Perché è incerta |
|---|---|---|
| 02 | **55 m² calpestabili / 65 commerciali** | Nel file non ci sono m². Sono ricavati da 60 punti elettrici e 130 m² di tinteggiatura. |
| 01 | **3 bagni, 6 locali** | I bagni vengono dai sanitari forniti (3 di ogni tipo); lo stato di fatto ne aveva uno. I locali sono ricavati dalla formula dei radiatori (10 = 1 + locali + bagni). |
| 01 | **Serramenti sostituiti, finestre al default** | C-SERRAMENTI è un importo a corpo (15.950 € IVA inclusa) nel riepilogo, senza righe. |
| 04 | **230 m² commerciali, porte mantenute** | 195 m² di pavimento sono certi. 14 porte rimosse ma solo 3 controtelai nuovi: le porte, se ci sono, sono fuori contratto. |
| 02, 03, 04 | **`non_rifare`** finiture/prodotti/serramenti | Nel riepilogo B, C e D sono a zero: il cliente li compra a parte. |

## Cosa è stato tarato (seed + migrazione 0029)

Solo valori sostenuti da almeno due casi concordi.

| Dato | Bozza | Tarato | Evidenza nei computi |
|---|---|---|---|
| A.11.3 tinteggiatura | solo soffitti | pareti + soffitti (`superfici_fondo`) | Il tecnico tinteggia tutto con A.11.3, in tutti e 4 i casi; nel caso 04 la descrizione dice "soffitti e pareti". |
| A.11.4 lavabile su pareti | `pareti_tinteggiate` | fattore 0 | Mai usata (0 su 4). |
| `mq_pareti` | 2,9 × calpestabile | **2,2** | m² tinteggiati / m² calpestabili: 5,2 · 2,4 · 3,8 · 2,6, mediana 3,2 = 1 (soffitti) + 2,2. |
| A.11.6 fondo | 100% delle superfici | **40%** | 150 m² su 140 di pavimento (caso 01), 400 su 195 (caso 04), assente nei parziali. |
| `rasatura_mq` | 30% pareti + intonaco nuovo | 30% pareti (termine intonaco a 0) | 0,71 · 0,73 · 0,53 · 0,51 m² per m² calpestabile, anche con 85 m² di muri nuovi (caso 01). |
| `ml_battiscopa` | 1,1 × calpestabile | **0,65** | 0,86 (caso 01), 0,46 (caso 04), 0,43 (caso 03). |
| `punti_acqua` | 5 / bagno + 2 / cucina | **4 / bagno + 3 / cucina** | 15 (3 bagni + cucina), 11 (2 bagni + cucina), 4 (1 bagno): li riproduce tutti e tre. |
| A.0.11 linee idriche (UM `ac`) | 1 per bagno | **1 a corpo** se si rifà un bagno | 300 € a corpo per due bagni (caso 04). |
| A.7.1 impermeabilizzazione | 6 m² / bagno | **4 m²** (minimo 200 € invariato) | 450 € per tre bagni (caso 01), 200 € per uno (caso 03). |
| A.8.5 montaggio sanitari | 4 / bagno | **3** | 10 per tre bagni, 6 per due. |
| A.10.11 lampadari | `punti_lampadari` | fattore 0 | Mai presenti (0 su 3 elettrici rifatti). |
| A.10.12 foro cappa | 1 con la cucina | fattore 0 | Assente in 3 cucine rifatte su 3; c'è solo per un bagno cieco. |

Effetto sui numeri di riferimento (Reggio Emilia, 85 m², risposte di default, imponibile):

| Tipo | Edile bozza → tarato | Totale lavori bozza → tarato |
|---|---|---|
| Leggera | 16,4 → 13,2 k€ | 20,5 → 16,8 k€ |
| Moderata | 32,4 → 29,2 k€ | 41,5 → 37,8 k€ |
| Totale | 39,1 → 35,9 k€ | 69,3 → 65,6 k€ |

Le cifre delle guide pubbliche (`frontend/src/data/guide-costi.json`) sono rigenerate da un DB
seminato col seed tarato.

## Cosa NON è stato tarato, e perché

### Punti aperti del §7 della proposta: segnalati, non tarati via

Pesano sullo scarto, ma la regola la decide il tecnico.

| Voce | Regola attuale | Nei computi reali |
|---|---|---|
| A.9.1 assistenza impianti | 30% di idrico, gas, termo, clima | Scritta **a corpo**: 4.000 € (39% degli impianti, caso 01), 5.500 € (45%, caso 04); 30% solo nel parziale (caso 02). |
| A.9.2 assistenza elettrico | 35% dell'elettrico | A corpo: 3.600 € (47%, caso 01), 3.600 € (55%, caso 04), 600 € (14%, caso 02; 38%, caso 03). |
| A.0.18 movimentazione | 6% di A.6 × (piano + 1) | 2.000 € al primo piano (casi 01 e 04), 100-300 € al piano terra. In tutti i casi è circa il **10-12%** di A.6 × (piano + 1), con un minimo di 100 €. |

**Scenario non applicato**, con A.9.1 al 40%, A.9.2 al 45% e A.0.18 al 12% con minimo
100 €:

| Caso | Scarto edile | Totale reale nel range |
|---|---:|---|
| 01 | +3% | sì |
| 02 | −5% | **sì** |
| 03 | +5% | sì |
| 04 | −8% | sì |

Sono quattro casi su quattro nel range, con l'edile entro ±8%. Se il tecnico conferma, basta
cambiare tre fattori (Excel del computo o migrazione) e togliere il caso 02 da `FUORI_RANGE`
in `test_casi_reali.py`: lo `xfail` stretto lo segnala da solo.

### Scarti di solo prezzo

Il listino seminato non è quello dei computi 2025-26, e non è un errore del motore.

| Voce | Listino | Computi reali |
|---|---:|---|
| A.2.1 massetto sabbia-cemento | 40 €/m² | **30** in tutti e tre i casi |
| A.8.16 punto elettrico ex novo | 65 € | 47 / 55 / 60 |
| A.6.1 posa pavimento | 30 €/m² | 30-36 |
| A.12.1 sicurezza | 1.000 € | 500 / 700 / 1.000 / 2.000 |
| A.0.1 allestimento | 600 € (scaglioni) | 400 / 800 / 500 / 1.500 |
| A.8.17 quadro elettrico | 560-905 € (scaglioni) | 500-600 sempre, anche oltre 100 m² e anche con la sola modifica (caso 03) |

Il massetto da solo vale 1.400-1.950 € a cantiere. Se il listino va aggiornato, va fatto dal
pannello admin, su conferma del tecnico.

### Densità dei punti elettrici: varianza alta, lasciata a 0,5 per m²

Punti per m² commerciale:

- caso 01: 0,91;
- caso 04: 0,43;
- caso 02: dato circolare, perché i suoi m² sono dedotti proprio dai punti.

Due casi in disaccordo non bastano per spostare il fattore. Una domanda Pro sui punti, o un
conteggio per stanza, stringerebbe questa voce: oggi è la più incerta dell'elettrico.

### Lavori che il wizard non chiede

Per questi lavori manca una domanda; non vanno compensati con un preset.

| Lavoro | Casi | Peso |
|---|---|---|
| **Bagno nuovo** (non rifatto): niente rimozioni né demolizione rivestimenti | 03, e in parte 01 (da 1 a 3 bagni) | ~700 € di rimozioni e demolizioni in più nel motore |
| **Clima: solo predisposizione** | 01, 04 (predisposizione sì, montaggio e fornitura no) | +700 / +1.750 € di A.10.1 nel motore |
| **Bagno cieco** (areazione forzata + foro) | 03 | 500 € mancanti |
| **Carta da parati** | 04 | 480 € mancanti |
| **Nicchie, varchi, modifica vani porta** (A.3.2-A.3.8 riscritte) | 04 | ~2.300 € mancanti |
| **Velette, posa di un pavimento parziale, architrave, controtelaio scorrevole** a corpo | 02 | ~2.100 € mancanti: è la causa del caso 02 fuori range |
| **Impermeabilizzazione grande** (4.000 € a corpo, forse un terrazzo) | 04 | 3.700 € mancanti |
| **Porte rimosse e fornite fuori contratto** | 04 | 1.340 € di rimozioni porte e radiatori mancanti |

### Altre osservazioni

- **Intonaco del caso 01**: 85 m² di muri nuovi senza A.4.1, solo 150 m² di ripresa
  (A.4.2). Negli altri casi A.4.1 = 2 × muri nuovi, come la regola: caso isolato, regola lasciata.
- **Rivestimenti**: 50 m² per tre bagni + cucina (caso 01), circa 80 per due bagni + cucina
  (caso 04, a corpo). Non c'è un fattore unico; resta 18 per bagno + 5 per cucina.
- **A.6.11 taglio blindata** e **A.10.5 box doccia**: il motore li mette, i computi no (tranne
  il taglio della porta d'ingresso nel caso 03). Pesano poco, lasciati.

## Caso 03: perché è di frontiera

È un negozio: un solo bagno creato da zero in un locale commerciale, con elettrico modificato,
un tramezzo nuovo e il pavimento rifatto su 47 m². Il wizard e i preset sono pensati per
un'abitazione. Mancano "bagno nuovo" e "bagno cieco", e il tipo effettivo calcolato è
`moderata`. Si misura e si riporta (+2% sull'edile dopo la taratura, totale nel range), ma non
entra nella soglia: il test lo salta con la motivazione scritta nella fixture.

## Incoerenze dei file reali (per il tecnico)

1. **IVA dei serramenti.** Il riepilogo dice "C-PORTE E SERRAMENTI iva inclusa 10%" e calcola
   al 10%; l'app usa il 22% per C-SERRAMENTI. Va chiarito: la regola di dominio 5 non dà la
   percentuale dei serramenti.
2. **Caso 01: B e C a corpo nel riepilogo.**
   - B-FINITURE vale 15.730 € IVA inclusa contro 11.786 € delle righe del foglio B: ci sono
     3.232 € imponibili in più senza voce.
   - C-SERRAMENTI vale 15.950 € senza nessuna riga nel foglio C.
3. **Caso 02**: il subtotale "TOTALE ASSISTENZA MURARIA" del foglio vale 400 €. Le righe
   sommano 705 € (A.9.1 105 € + A.9.2 600 €). Il totale del riepilogo segue il subtotale.
4. **Caso 03**: la movimentazione ha quantità "T" (piano terra) scritta a parole. L'estrazione
   la tiene come `quantita_testo` e conta il totale.
