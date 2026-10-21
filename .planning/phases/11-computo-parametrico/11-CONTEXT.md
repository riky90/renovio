# Phase 11: Computo parametrico - Context

**Gathered:** 2026-10-21
**Status:** In esecuzione

<domain>
## Phase Boundary

Il motore Pro e il motore Free diventano lo stesso computo: grandezze della casa → interventi
scelti (con il tipo di ristrutturazione come preset) → una regola di quantità per voce. Fonte
del ragionamento: colonne T/U e note H del nuovo Excel. Analisi completa e tabella voce per voce
in `docs/proposta-computo-parametrico.md`. Requisiti: GRD-01..03, RGL-01..05, INT-01..03,
MOT-01..04, CUR3-01.

Stato misurato il 2026-10-21 (DB seed + migrazioni fino alla 0024): Pro 85 m² totale =
386.027–579.042 €, di cui A-EDILE 293–440 k€ e C-SERRAMENTI 85–127 k€; ricostruzione manuale con
le regole del file ≈ 42.400 € di edile imponibile.

</domain>

<decisions>
## Implementation Decisions (Riccardo, 2026-10-21)

- **D-01:** Free derivato dallo stesso motore del Pro. L'oracolo 47.985–70.575 si sposta: i
  test che lo fissavano diventano test del nuovo computo.
- **D-02:** Tutte le domande nuove sugli interventi vanno nel wizard **Free**.
- **D-03:** Il tipo di ristrutturazione diventa un preset delle risposte (ok).
- **D-04:** Nessun computo reale disponibile ora: i valori sono **bozza** ragionata dal file
  (note H, colonne T/U) e i casi d'oro arrivano dopo (TAR-01).

## Scelte tecniche

- **D-05:** Regole e grandezze in tabelle nuove, legate al codice voce. Le voci B/C/D ricevono
  codici `B.n.m`, `C.n.m`, `D.n.m` per sottocategoria; lo smaltimento `A.9.5` duplicato diventa
  `A.9.6` (come nel nuovo file); `A.12.1.` perde il punto finale.
- **D-06:** Le condizioni sono grandezze-flag (> 0), così interventi e quantità parlano la
  stessa lingua: un'opzione assegna un valore a una grandezza (`valore_grandezza_opzione`).
- **D-07:** Gli assi Pro esistenti (`finitura`, `tipo_pavimento`) e gli effetti `escludi` /
  `fattore_quantita` continuano a decidere inclusione e fattori; la regola sostituisce solo la
  quantità di base. Le voci senza regola usano la catena v2 (`CoefficienteQuantitaVoce`).
- **D-08:** I tipi di regola e le sorgenti speciali (`mq`, `tipo_<code>`) sono un vocabolario
  chiuso nel codice, come i tipi di effetto: aggiungerne uno è una decisione di design.
- **D-09:** Le correzioni di categoria Free che restano (moltiplicatori, €/m², € fissi) si
  applicano al totale di categoria del computo; nel Pro i moltiplicatori scalano le voci della
  categoria e i termini additivi compaiono come voci "a corpo" tracciabili, così Free e Pro
  coincidono.

</decisions>
