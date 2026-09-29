# Phase 10: Risultato leggibile e tetto di budget - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-29
**Phase:** 10-risultato-leggibile
**Areas discussed:** Raccolta del budget, Avviso sforamento, Barra proporzionale, Card e riepilogo

---

## Raccolta del budget

| Option | Description | Selected |
|--------|-------------|----------|
| Nel wizard + modificabile | Domanda facoltativa nel wizard e campo nel risultato | |
| Solo nel wizard | Domanda a catalogo, si cambia rifacendo la stima | |
| Solo nel risultato | Campo "Il tuo budget" a posteriori | |

**User's choice:** (testo libero) "una domanda nella sezione 3: qual e' il tuo budget per la ristrutturazione, e l'utente mette la cifra che ha in mente". La modifica dal risultato e' stata decisa dopo, nell'area avviso (si').

| Obbligo | | Selected |
|---|---|---|
| Facoltativo | Nessun avviso senza budget | ✓ |
| Obbligatorio | Ogni stima ha un tetto | |

| Forma | | Selected |
|---|---|---|
| Importo in euro | Numero libero IVA inclusa | ✓ |
| Fasce predefinite | <30k, 30-50k, ... | |

| Persistenza | | Selected |
|---|---|---|
| Salvato + nel PDF | | ✓ |
| Salvato, non nel PDF | | |
| Non salvato | | |

---

## Avviso sforamento

| Soglia | | Selected |
|---|---|---|
| Due livelli | sotto min = fuori budget, dentro = al limite, sopra max = ok | ✓ |
| Solo sopra il minimo | | |
| Solo sopra il massimo | | |

| Confronto | | Selected |
|---|---|---|
| Livello sotto | alte→medie, medie→economiche | ✓ |
| Tutti i livelli inferiori | | |
| Sempre economiche | | |

| Perimetro | | Selected |
|---|---|---|
| Solo totale lavori | | ✓ |
| Lavori + arredo | | |

| Pro | | Selected |
|---|---|---|
| Solo Free in questa fase | | |
| Anche nel dettaglio Pro | Confronto sull'asse finitura Pro | ✓ |

| Modifica dal risultato | | Selected |
|---|---|---|
| Si', campo nel box avviso | | ✓ |
| No, solo dal wizard | | |

| Calcolo del confronto | | Selected |
|---|---|---|
| Server, ricalcolo vero | | ✓ |
| Decidi tu | | |

---

## Barra proporzionale

| Scala | | Selected |
|---|---|---|
| Da 0 a un tetto | ~1,2 × max o budget | ✓ |
| Centrata sul valore medio | | |

| Marcatore budget | | Selected |
|---|---|---|
| Si', tacca verticale | | ✓ |
| No, solo nel box avviso | | |

| Card | | Selected |
|---|---|---|
| Mini-barra del peso | | ✓ |
| RangeBar anche nelle card | | |
| Nessuna barra | | |

---

## Card e riepilogo

| €/m² | | Selected |
|---|---|---|
| Range, IVA inclusa | | |
| Range, imponibile | | ✓ |

| Peso % | | Selected |
|---|---|---|
| Sul valore medio | | ✓ |
| Range di percentuali | | |

| Riepilogo | | Selected |
|---|---|---|
| Sotto il totale, nella TotalCard | | ✓ |
| Sezione a parte, espandibile | | |

| PDF | | Selected |
|---|---|---|
| Si', Free e Pro | | ✓ |
| Solo budget nel PDF | | |

---

## Claude's Discretion

- Forma tecnica del budget (tipo di controllo di catalogo o campo dedicato) e sua persistenza.
- Forma dell'endpoint del confronto e del salvataggio del budget dal risultato.
- Arrotondamento del tetto della scala, testi dell'avviso, layout mobile, raggruppamento IVA.

## Deferred Ideas

Nessuna.
