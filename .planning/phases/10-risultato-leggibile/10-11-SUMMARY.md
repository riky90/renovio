---
phase: 10-risultato-leggibile
plan: 11
subsystem: risultato
tags: [gap-closure, G3, confronto-finiture, wizard]
requires: []
provides:
  - regressione server Free (confronto == stima fresca) e Pro (livelli misti)
  - wizard: default della nuova fascia di m2 riapplicati alle domande non toccate
affects: [10-15]
key-files:
  modified:
    - backend/tests/test_confronto_finiture.py
    - backend/tests/test_dettaglio_pro_budget.py
    - frontend/src/components/EstimateWizard.tsx
decisions:
  - "G3: esito B (client). Il server e' corretto; la divergenza nasce dagli input del wizard"
  - "risposteToccate da flag booleano globale a insieme per-codice (ref)"
metrics:
  completed: 2026-09-29
  tasks: 2
---

# Phase 10 Plan 11: chiusura G3 (confronto finiture) Summary

Esito **B (client)**: il percorso server e' corretto, il wizard invia risposte diverse a seconda dell'ordine in cui l'utente compila.

## Causa radice G3

**Server (escluso).** `test_confronto_coincide_con_stima_fresca` prova 9 combinazioni (leggera/moderata/totale x 85/140/300 m2), ognuna con le risposte di default piu' varianti una-domanda-alla-volta (ogni opzione delle scelte singole, scelte multiple complete, stepper default+1, muri_lavori e efficientamento = "si"), livello "alto". In tutte, `confronto_finiture` (min e max) e' identico a una POST fresca con `livello_finiture` = livello inferiore. Verde senza modifiche a `stima.py`/`dettaglio_pro.py`. Anche il confronto Pro coincide (`test_confronto_pro_coincide`, livelli tutti alto e misti).

**Client (riprodotto).** I default degli stepper dipendono dalla fascia di m2. Differenza fra i default a 85 e a 300 m2 (dal catalogo `GET /domande?tier=free&mq=`): condizionatori 2 vs 4, finestre 5 vs 9, locali 3 vs 5, superficie_calpestabile 76 vs 340, portefinestre 1 vs 2, porte 5 vs 9, bagni 1 vs 2. In `EstimateWizard` il flag globale `risposteToccate` diventava `true` al primo tocco (es. scegliere finiture "alto"), e da li' un cambio di m2 non riapplicava piu' i default: il wizard teneva gli stepper della fascia precedente.

Passi di riproduzione: aprire il wizard con m2 85, toccare una risposta (es. livello finiture), portare i m2 a 300, inviare. Le risposte inviate hanno gli stepper della fascia 85; un wizard pulito a 300 m2 li ha della fascia 300. Sono due stime con input diversi, non un errore del confronto.

Importi (totale, tipo "totale", Reggio Emilia, livello alto, max / confronto "medio" max):
- 85 m2, stepper fascia 85: 81.257 / 71.248
- 85 m2, stepper fascia 300: 100.221 / 90.212
- 300 m2, stepper fascia 85: 260.729 / 225.402
- 300 m2, stepper fascia 300: 279.693 / 244.366

Il divario tra stepper di fascia diversa a parita' di m2 e' di ~19k EUR sul massimo; la differenza di Riccardo (337.923 vs 336.111, ~1,8k) e' minore, quindi nel suo caso e' plausibile che cambi solo qualche stepper. I suoi input non sono noti e il valore esatto non e' stato replicato: la conferma dal vivo e' nella checklist 10-15 (voci G3 (d) ed (e)). Meccanismo provato, coincidenza numerica esatta non provata.

## Correzione

`frontend/src/components/EstimateWizard.tsx`: `risposteToccate` e' ora un insieme per-codice (`useRef<Set<string>>`), come `scelteToccate`. Al cambio di catalogo (m2) si riapplicano i default della nuova fascia alle domande non toccate e si conservano le risposte date. Per `risposteDiPartenza` (piano 10-12, "Modifica") contano come toccate solo le chiavi con valore diverso dal default del primo catalogo caricato. `applicaValoriStandard` svuota l'insieme. `useState(risposteDiPartenza !== undefined)` non esiste piu'; `scelteToccate` invariato (4 occorrenze).

## Commits
- Vedi `git log` del piano: test G3 Free e Pro, poi fix wizard.

## Verifica
- pytest test_confronto_finiture, test_dettaglio_pro_budget, test_stima_api, test_estimation, test_no_leak: 59 passed (oracolo 85 m2 verde).
- `npm run build` ok; `npm run lint` solo warning preesistenti.

## Deviations from Plan
- [Rule 3] Il test parametrico disabilita `limiter` (slowapi, 20/min) nella fixture `client` del file: senza, le centinaia di POST fallivano per rate limit.
- Durata: ~8 s per combinazione, ~75 s per il test parametrico (piano: <60 s). Varianti gia' ridotte (stepper +1, scelta multipla completa); ulteriore riduzione toglierebbe copertura.
- Nessun codice di produzione backend modificato (esito B).
- Nessun test frontend automatico per il wizard (non esiste infrastruttura di test componenti); la verifica dal vivo e' nella 10-15.

## Stato G3
Causa identificata e corretta lato client; la chiusura definitiva resta alla checklist 10-15 (voci G3 (d) ed (e)).

## Known Stubs
None.

## Self-Check: PASSED
