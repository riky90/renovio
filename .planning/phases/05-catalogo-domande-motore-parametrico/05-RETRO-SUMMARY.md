# Phase 05 — Catalogo domande + motore Free parametrico · RETRO-SUMMARY

**Status:** ✅ Complete
**Delivered:** 2026-09-21 · commit `5ea305b`
**Requirements:** QST-01, QST-02, QST-03, QST-04, PAR-01, PAR-02, PAR-03, PAR-05

> **Nota sul tracking.** Questa fase è stata eseguita **fuori dal ciclo GSD**, a partire dal
> piano `~/.claude/plans/il-punto-1-come-steady-comet.md` (la sua "Fase 1"). Non esistono
> `05-NN-PLAN.md` né `05-CONTEXT.md`, e inventarli a posteriori significherebbe scrivere un
> piano che nessuno ha seguito. Questo documento è la ricostruzione retrospettiva del
> consegnato, tratta dal commit e dal codice — non un piano.

## Cosa è stato consegnato

**Migrazione `0014`, interamente additiva.** Quattro tabelle nuove in
`backend/app/models/domanda.py`:

| Tabella | Ruolo |
|---|---|
| `domanda` | code, testo, help, `tipo_controllo`, gruppo, ordine, `tier_minimo`, `attributo_code`, visibilità condizionale, `attiva` |
| `opzione_domanda` | le risposte possibili; per `stepper`/`numero` una sola opzione implicita `code='valore'` |
| `effetto_opzione` | cosa fa una risposta al calcolo: `tipo_effetto` + target (categoria \| sottocategoria \| voce) + `valore` |
| `attesa_immobile` | la baseline per `(attributo, fascia di m²)` |

**`backend/app/services/effetti.py`** è l'unico posto in cui una risposta diventa aritmetica.
I motori non contengono un solo `if` sul codice di una domanda. I sette tipi di effetto sono
un **insieme chiuso** — `moltiplicatore_categoria`, `eur_mq_categoria`, `eur_per_scostamento`,
`includi`, `escludi`, `fattore_quantita`, `quantita_per_unita` — perché un motore a regole
marcisce quando in una cella si può scrivere qualunque cosa.

**Motore Free esteso.** `EstimationService.compute()` prende un quinto parametro `risposte`
opzionale; `StimaRequest.risposte` è opzionale a sua volta, quindi l'API resta
retrocompatibile e il layer è un **no-op a riposo**.

**CRUD admin** su domande/opzioni/effetti/attese, più `POST /admin/domande/anteprima` —
l'anteprima è lo strumento con cui si tara, quindi è stata costruita qui invece che rimandata.

**Seed bozza:** 16 domande, 42 opzioni, 52 effetti, 30 attese.

## La decisione che regge la fase

Le correzioni agiscono sullo **scostamento** dal valore atteso per fascia di m², non sul
valore assoluto. È ciò che rende il layer neutro **per costruzione** e non per fortuna: un
85 m² con i valori standard costa esattamente quanto costava prima che questo layer
esistesse.

La seconda: la **proprietà del dato è asimmetrica**. Testo e struttura delle domande sono del
prodotto, e il seed li riscrive a ogni boot; i valori degli effetti e le attese sono
dell'admin, e il seed li crea **solo se mancano**. Senza questa asimmetria ogni deploy
riporterebbe la taratura alla bozza cablata nel repo.

## Verifica

- **421 passed, 5 skipped**
- Migrazione provata `upgrade → downgrade → upgrade`; seed eseguito due volte su DB vergine
- **Oracolo primario** 85 m² · totale · Reggio Emilia → `47.985 – 70.575 €` verde in **tre**
  forme: layer spento, layer acceso senza risposte, risposte esplicite pari agli attesi
- Nessuna tabella nuova porta il coefficiente impresa (`test_no_leak*`)

## Debito lasciato aperto

- **I 52 coefficienti sono una bozza, non una taratura.** Vale anche per le 30 attese.
  Finché non sono confermati su preventivi reali aggiungono **risoluzione, non accuratezza**.
  → resta aperto fino alla taratura su preventivi reali (CFG-04 in Phase 09 per il lato Pro).
- `POST /admin/domande/anteprima` esiste, ma l'anteprima completa del breakdown Free con il
  delta rispetto alla stima senza risposte è **PAR-04**, schedulato in Phase 08.
