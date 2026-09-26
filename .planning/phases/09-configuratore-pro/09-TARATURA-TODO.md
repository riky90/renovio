# Taratura Pro — checklist rinviata per Riccardo

**Stato: RINVIATA** — i piani 09-06 e 09-07 applicano la bozza accettata
(`docs/taratura/09-taratura-pro-compilato.xlsx`, stato `bozza-accettata`), non
valori rivisti da Riccardo. Vincolo del 2026-09-26: le fasi 09 e 10 si eseguono
di fila senza fermarsi sulla sua compilazione.

Quando Riccardo avra' tempo di rivedere davvero i coefficienti e le
assegnazioni, questa checklist guida la compilazione del file vero
(`docs/taratura/09-taratura-pro.xlsx`) e il suo rientro nel motore.

## Checklist

- [ ] 1. Apri `docs/taratura/09-taratura-pro.xlsx` e leggi il foglio `LEGGIMI_TARATURA`.
  Atteso: istruzioni chiare su cosa significano `OK` / `ATTUALE` / `MODIFICATO` (e `NO` su
  `assi_proposti`), e quali colonne non vanno mai toccate (`id`, `voce_id`, `tipo_code`).
  Note:

- [ ] 2. Scorri il foglio `coefficienti_pro` sulle voci di pavimento, pittura e battiscopa.
  Atteso: coefficienti diversi fra classi di voce, una motivazione comprensibile per ogni
  riga, nessuna colonna di prezzo riservato all'impresa (nessuna colonna
  `coefficiente_impresa`).
  Note:

- [ ] 3. Compila la colonna `decisione` per ogni riga di `coefficienti_pro` (`OK` se il
  proposto ti convince, `ATTUALE` se preferisci il valore che c'e' oggi, `MODIFICATO` se
  scrivi tu il numero in `coefficiente_qta_per_mq` o `default_conteggio`), e la colonna
  `note` dove serve un commento.
  Note:

- [ ] 4. Sul foglio `assi_proposti`, verifica le 21 voci del gres (base/medio/alto), le pose
  A.6.1/A.6.2/A.6.5/A.6.6 (tipo di pavimento) e le famiglie di alternative (sanitari, porte,
  condizionatori). Compila `decisione` (`OK` / `NO` per escludere la proposta / `MODIFICATO`
  se cambi l'opzione) e `note`.
  Note:

- [ ] 5. Regola del bagno (D-02): controlla le righe `fattore_pavimento` (bagno sempre gres a
  parte dal resto della casa) e verifica che il valore proposto (quota di m2 del bagno sul
  totale) ti torni.
  Note:

- [ ] 6. Sul foglio `dati_richiesti`, compila `valore_riccardo` per ogni dato che conosci
  meglio della bozza di Claude. Una cella vuota significa "va bene il valore proposto".
  Note:

- [ ] 7. Facoltativo: carica il file in anteprima da `/admin/parametri` (drag&drop, non
  Applica). Atteso: nessuno scarto segnalato. NON premere "Applica" — questo file lo applica
  la fase con una migrazione dedicata, non il pannello.
  Note:

- [ ] 8. In `LEGGIMI_TARATURA`, porta la riga `stato` a `compilato` e salva il file SOPRA
  `docs/taratura/09-taratura-pro-compilato.xlsx`.
  Note:

- [ ] 9. Chiedi a Claude di riapplicare la taratura. Atteso: lancia il comando del piano
  09-06 (`scripts/applica_taratura.py --file ../docs/taratura/09-taratura-pro-compilato.xlsx
  --migrazione`) e ti riporta il riepilogo delle differenze applicate.
  Note:

## Come si riapplica

Comando (piano 09-06, non ancora eseguito a questa data):

```
cd backend && .venv/Scripts/python.exe scripts/applica_taratura.py \
  --file ../docs/taratura/09-taratura-pro-compilato.xlsx --migrazione
```

Cosa aggiorna:
- i coefficienti quantita'/default_conteggio in `coefficiente_qta_voce` (dal foglio
  `coefficienti_pro`, secondo le decisioni `OK`/`ATTUALE`/`MODIFICATO` lette da
  `leggi_decisioni()`);
- l'assegnazione delle voci agli assi finitura/tipo_pavimento/stepper (dal foglio
  `assi_proposti`, righe non escluse con `NO`) — traduce le decisioni in una nuova
  migrazione Alembic additiva, non in un `UPDATE` diretto fuori catena;
- il JSON di seed (`docs/seed-dettaglio-pro.json`) e le fixture delle famiglie di
  alternative usate dai test, cosi' che un reset locale del DB riparta dai valori tarati
  invece che dalla bozza.

Una taratura successiva (una nuova compilazione del file, mesi dopo) e' sempre una NUOVA
migrazione Alembic: non si modifica mai la migrazione 0022 (o quella che applica questa prima
taratura) a posteriori — lo storico delle migrazioni deve restare una sequenza di modifiche
reali, ripetibile su ogni ambiente (dev/staging/produzione) nello stesso ordine.
