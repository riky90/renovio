# Phase 06 — Wizard unico, domande servite dal DB · RETRO-SUMMARY

**Status:** ✅ Complete
**Delivered:** 2026-09-21 · commit `1f2a8b8`
**Requirements:** WIZ-01, WIZ-02, WIZ-03

> **Nota sul tracking.** Come la Phase 05, eseguita **fuori dal ciclo GSD** dal piano
> `~/.claude/plans/il-punto-1-come-steady-comet.md` (la sua "Fase 2"). Questo documento
> ricostruisce il consegnato; non è un piano.

## Cosa è stato consegnato

**Il client non conosce più nessuna domanda per nome.**

`GET /api/v1/domande?tier=&mq=` serve catalogo, opzioni e i **default già risolti** per la
fascia di metri quadri. I default li risolve il server, con la stessa `attese_per_mq()` che
nel motore fa da baseline allo scostamento: se il client rifacesse il conto per conto suo,
una fascia modificata dall'admin sposterebbe il calcolo senza spostare ciò che l'utente vede,
e lo scostamento partirebbe da un default che nessuno ha toccato.

**Il catalogo NON pubblica gli effetti.** Il client sa *cosa* chiedere, non *quanto vale* la
risposta. Un test lo verifica sul JSON serializzato, non sulle chiavi di primo livello.

**Frontend:**

- `components/ui/number-stepper.tsx` — primitivo `−/valore/+`, tap ≥44px, `inputMode="numeric"`.
  Sostituisce gli input numerici grezzi perché questi campi arrivano **pre-compilati e si
  aggiustano** invece di compilarsi: coi bottoni lo stato vuoto — che non è un numero e non è
  nemmeno zero — semplicemente non esiste.
- `EstimateWizard` unico al posto di `EstimateForm` + `EstimateFormPro`: Free a tre step, Pro
  a quattro (**1 · Dove** — **2 · L'immobile** — **3 · La ristrutturazione** — **4 · Le
  finiture**). Non era duplicazione di markup: col catalogo i due form sono lo stesso form con
  un filtro diverso sul tier, e tenerli separati significava due posti in cui montare le
  stesse domande.
- `DomandaField` disegna una domanda qualsiasi conoscendo solo i cinque `tipo_controllo`. Un
  gruppo che il wizard non riconosce **cade nello step 3 invece di sparire**: il modo in cui
  questa fase poteva fallire in silenzio era proprio una domanda attiva in tabella che non
  viene mai posta.
- Le risposte alle domande nascoste **non partono**: il motore le ignorerebbe comunque, ma
  finirebbero nello snapshot congelato dove sembrerebbero risposte date.

Sparisce `EstimateFormPro.tsx:DOMANDE`.

## Verifica

- **430 passed, 5 skipped** (421 + 9 nuovi) · `tsc -b` pulito
- Provato dal vivo sul dev server: 85 m² Reggio Emilia totale dal wizard → `47.985–70.575`,
  **oracolo primario esatto**
- Modena 200 m²: layer spento e risposte sui default danno lo stesso numero
  (`109.110–162.262`); portare i bagni da 2 a 4 sposta di **5.808 €**
- I default seguono la fascia: 85 m² → 3 locali / 1 bagno / 5 finestre; 200 m² → 5 / 2 / 9

## Debito lasciato aperto

- **`DettaglioProView.tsx:FIELD_LABELS` resta.** Le sue tre chiavi sono il contratto del
  motore Pro (`coefficiente_qta_voce.domanda_mirata_key`), e il tipo `RisposteDomande` è
  chiuso a tre campi lato schema (`RisposteDomandeRequest`). Chiuderlo significa rendere le
  risposte Pro un dizionario aperto → **Phase 09**, insieme al configuratore.
  *(Il blocco più stretto — `condizionatori` senza una domanda nel catalogo — è stato risolto
  il 2026-09-21: la domanda ora esiste, QST-05 è soddisfatto per tutte e tre le chiavi.)*
- **Il percorso Pro del wizard è verificato solo a livello di tipi.** Lo step 4 monta i
  livelli di finitura e le eventuali domande `tier_minimo=pro`, che nel seed sono zero:
  esiste e non è mai stato visto pieno. Serve un account Pro reale → **WIZ-04, Phase 09**.
