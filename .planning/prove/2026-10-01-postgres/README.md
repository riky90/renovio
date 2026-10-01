# Prova delle migrazioni v2.0 su Postgres (2026-10-01)

Primo dei passi prima del push (vedi `.planning/STATE.md`). Esito: **le migrazioni 0014-0024
passano su Postgres partendo da uno stato v1.0 con dati utente, e l'app v2 funziona su quel
DB.** Nessun blocco al push da questa prova. Tre osservazioni sotto, una delle quali va decisa
prima del go-live.

## Come e' stata fatta

1. Postgres **16.2** locale (pacchetto `pgserver` da PyPI, in un venv usa-e-getta, porta 55432).
2. Stato di produzione v1.0 ricostruito con il codice di `origin/main` (`f011ed4`) in un
   worktree: `alembic upgrade head` (→ `0013`) e `scripts/seed.py`, cioe' quello che il
   Dockerfile faceva al boot. Poi `popola_v1.py`: due utenti (uno Pro), 8 stime salvate (Free,
   Pro con risposte bagni/porte/condizionatori, una in fallback su Modena), 2 lead, tutti creati
   dalle API della v1.
3. Deploy v2 come il Dockerfile attuale: `alembic upgrade head` (0013 → 0024, 2,7 s, nessun
   avviso) e `scripts/seed.py`.
4. Verifiche:
   - `confronta_valori.py`: tabelle di configurazione del Postgres migrato contro un SQLite
     nuovo creato a head e seminato. Stessi conteggi in tutte le tabelle, differenze solo nei
     dati utente.
   - Coefficienti Pro del Postgres contro `dev.db` (quello del collaudo): **identici**.
   - Totali Pro (85 m², totale, finiture base/medio/alto) Postgres contro copia di `dev.db`:
     **identici al centesimo**.
   - `smoke_v2.py`: **39/39 PASS**. Login degli utenti v1, Pro che resta Pro, apertura delle 8
     stime v1 e dettaglio Pro sulle stime Pro v1, Free respinto dal Pro, nuova stima v2 con
     risposte e arredo, salvataggio con budget, ricalcolo Pro (parquet, bagni, livelli),
     PATCH budget, **WR-06 su Postgres** (PUT con mq 0, -5, 2001, 2^31, citta vuota e citta di
     101 caratteri → 422 e riga invariata; PUT valido → 200; POST mq 0 → 422), lead nuovo,
     oracolo Free 47.985-70.575, 28 GET admin senza 500, export tracciati in `export_log`.
   - M2 su Postgres: con `livello_finiture` base/medio/alto il dettaglio Pro applica
     `{B-FINITURE, C-SERRAMENTI, D-PRODOTTI}` allo stesso livello.

Per rifarla servono gli script di questa cartella e i passi sopra; il DB era usa-e-getta.

## Osservazioni

### 1. Totale Pro circa 8 volte il Free — da decidere prima del go-live

85 m², totale, finiture medie: Free 47.985-70.575 €, imponibile Pro **386.027 €** (A-EDILE da
solo 293.031 €). Uguale su Postgres e su `dev.db`, quindi non e' un effetto della migrazione:
sono i coefficienti in bozza. Le voci piu' pesanti sono quantita' a corpo o a numero
moltiplicate per i m²:

| Voce | Quantita' | um | Importo min |
|---|---|---|---|
| A.9.3 Assistenza muraria singolo ambiente | 72,25 | cad | 43.350 |
| A.1.16 Demolizione di scala interna | 42,50 | ac | 27.540 |
| A.1.15 Apertura di varco su solaio | 42,50 | ac | 23.800 |
| A.1.13 Rimozione gradini | 42,50 | ac | 22.100 |
| A.9.4 Assistenza muraria impianto (bocchette) | 72,25 | n. | 14.450 |
| A.6.11 Taglio porta blindata | 72,25 | ac | 14.450 |
| A.5.1 Controsoffitto in cartongesso | 229,50 | mq | 12.852 |
| A.1.14 Apertura varco su muratura strutturale | 21,25 | ac | 11.900 |

A.6.11 era gia' noto (`09-TARATURA-TODO.md`); le altre voci hanno lo stesso difetto. Con questi
coefficienti un utente Pro in produzione vedrebbe circa 4.500 €/m².

### 2. Installazione da zero: due voci con il coefficiente sbagliato

Nel `seed-dettaglio-pro.json` ci sono due coppie di voci con descrizione identica nella stessa
sottocategoria: gres "30 x 60 cm, spessore 10 mm" (ordine 10 e 11) e parquet "wengè"
(ordine 34 e 35). Su un DB vuoto il seed abbina per descrizione e la voce 11/35 prende 0,6
invece di 0,85 (in tutti e tre i tipi, scalati). Il percorso di produzione (migrazioni dalla
v1) da' i valori giusti, quindi **non tocca il push**; tocca un DB nuovo (secondo ambiente,
test che seminano da zero).

### 3. Il seed riscrive `updated_at` di 6 voci a ogni avvio

Secondo giro del seed sul DB gia' migrato: nessun valore cambia, ma `voce.updated_at` viene
riscritto su 6 voci (le due sopra, la cassetta d'incasso, il radiatore — 129,5646 nel JSON
contro 129,56 nella colonna numeric(…,2) — e altre due). Su Render il seed gira a ogni boot e
il free tier riavvia spesso: l'avviso "cambiata dopo l'export" (D-11) del re-import del listino
scattera' su quelle righe senza che nessuno le abbia toccate.

Arrotondamento a parte, i prezzi con piu' di due decimali nel JSON vengono troncati a due su
Postgres (gia' cosi' in produzione dalla v1).
