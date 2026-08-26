# Phase 3: Pro & dettaglio sottocategorie - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-26
**Phase:** 3-Pro & dettaglio sottocategorie
**Areas discussed:** Coerenza Pro↔Free, Dati voci-chiave nel DB, Quantità, Stato Pro & paywall, PDF Pro & upgrade snapshot

---

## Coerenza Pro↔Free (motore parametrico)

| Option | Description | Selected |
|--------|-------------|----------|
| Top-down | Il totale di categoria Free si ripartisce tra le sottocategorie con pesi % (riconcilia per costruzione) | |
| Bottom-up | Voci × quantità × prezzo unitario; può NON combaciare col totale Free | ✓ |
| Bottom-up ancorato | Calcolo per voce poi riscalato al totale di categoria Free | |

**User's choice:** Bottom-up, senza riconciliazione. Il Free è una stima meno precisa, è accettabile che i due numeri differiscano; il Pro usa come base il massimo dettaglio dell'Excel.
**Notes:** Ha comportato la riscrittura del criterio di successo #2 della ROADMAP (prima imponeva "coerenti con i totali della Fase 1"), confermata dall'utente.

---

## Dati voci-chiave nel DB

| Option | Description | Selected |
|--------|-------------|----------|
| Fonte = fogli dettaglio Excel, esteso nello stesso seed | Prezzi RE dai fogli A/B/C/D; altre città via admin dopo | ✓ |

**User's choice:** Base = i fogli di dettaglio dell'Excel allegato (prezzi RE). Le altre città verranno inserite da admin via upload Excel o creando voci (Fase 4).
**Notes:** Struttura mappata e salvata in `docs/computo-struttura-dettaglio.md`. Scoperto che solo A-EDILE ha sotto-codici a.1/a.2; B/C/D sono cataloghi piatti. Le quantità nel file sono tutte 0.

---

## Quantità (sotto-decisione emersa)

| Option | Description | Selected |
|--------|-------------|----------|
| Domande all'utente | Poche domande in più (bagni, porte…): più preciso, più attrito | |
| Preset admin | Quantità-per-m² preimpostate: zero attrito, meno aderente | |
| Ibrido | Preset per-m² + poche domande sulle voci ad alto impatto | ✓ |

**User's choice:** Ibrido.
**Notes:** Regola data dall'utente: dove UM = mq, il prezzo è al metro quadro → quantità = frazione dei mq dell'appartamento.

---

## Stato Pro & paywall

| Option | Description | Selected |
|--------|-------------|----------|
| A — rappresentazione | Interruttore `is_pro` semplice vs **tessera abbonamento** (stato+scadenza) | Tessera ✓ |
| B — attivazione v1 | Admin manuale vs **bottone stub production-shaped** vs nessuno | Stub production-shaped ✓ |
| C — lucchetto | Gate server-side sull'endpoint (non solo UI nascosta) | ✓ (dato per scontato) |

**User's choice:** A = tessera abbonamento; B = bottone "Attiva Pro" finto ma con tutto preimpostato come se fosse reale, così in produzione basta accendere il pagamento.
**Notes:** C spiegato in termini business e accettato come strada giusta (evitare che un Free aggiri la UI).

---

## PDF Pro & upgrade snapshot

| Option | Description | Selected |
|--------|-------------|----------|
| Estendi generatore esistente | WeasyPrint esteso con sottocategorie | ✓ |
| Calcolo on-demand dagli input | Usa città/mq/tipo dello snapshot salvato | ✓ |
| Riconciliazione col totale Free | — | ✗ (rifiutata, misure diverse) |

**User's choice:** Estendere il PDF con le categorie di dettaglio; calcolo on-demand sugli input (città, mq, importanza intervento già noti); NON riconcilia col totale (misura diversa, più precisa).

---

## Claude's Discretion

- Schema esatto tabelle sottocategoria/voce/coefficiente-quantità (estendendo lo schema esistente).
- Meccanica UI del paywall e della schermata dettaglio; forma dello stub di pagamento.
- Set iniziale di domande mirate e coefficienti quantità-per-m² (taratura poi da admin).

## Deferred Ideas

- Pagamento reale + prezzo abbonamento definito → post-v1.
- Upload Excel multi-città + CRUD admin → Fase 4.
- Taratura fine coefficienti/quantità → Fase 4.
- Lead dal livello Pro → Fase 4.
