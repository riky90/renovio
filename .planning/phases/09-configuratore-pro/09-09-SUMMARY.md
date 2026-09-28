---
phase: 09-configuratore-pro
plan: 09
subsystem: database
tags: [alembic, sqlalchemy, taratura, configuratore-pro, pavimenti]

# Dependency graph
requires:
  - phase: 09-configuratore-pro
    provides: "genera_excel_taratura.py/applica_taratura.py esistenti (09-01, 09-06, 09-07): PropostaAsse, applica_assi, emetti_migrazione"
provides:
  - "proponi_assegnazione estesa: laminato/vinilico_lvt/moquette/sottofondo governati sull'asse tipo_pavimento, A.6.3/.4/.7/.8/.9/.10 governate per intero, gres a pavimento con famiglia dedicata e quota bagno"
  - "aggiorna_foglio_assi() + CLI --aggiorna-assi: aggiornamento del foglio assi_proposti di un workbook esistente senza perdere decisioni gia' scritte"
  - "applica_assi con bersagli condivisi fra opzioni (una voce inclusa da piu' opzioni dello stesso asse) e dedup per famiglia sull'asse finitura"
  - "fail-loud: ValueError su opzione/domanda citata ma assente dal seed; RuntimeError nel template di migrazione se il catalogo e' presente e una chiave naturale non si risolve"
affects: [09-10, 09-14]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "una PropostaAsse per (voce, opzione): una voce con piu' alternative produce piu' righe nel foglio assi_proposti, non una riga con lista"
    - "_record_effetti indicizza gli includi come frozenset di opzioni per bersaglio, non un'opzione singola: il diff di emetti_migrazione distingue bersagli condivisi da spostamenti veri"
    - "guardia fail-loud a due fasi nel template di migrazione: prima si risolvono TUTTE le chiavi naturali, poi (solo se il catalogo e' presente) si solleva RuntimeError sulle non risolte, altrimenti si scrive"

key-files:
  created: []
  modified:
    - backend/scripts/genera_excel_taratura.py
    - backend/scripts/applica_taratura.py
    - backend/tests/test_taratura_pro.py
    - backend/tests/test_applica_taratura.py

key-decisions:
  - "Moquette esclusa da OPZIONI_CON_QUOTA_BAGNO_A6_1: non ha una posa dedicata nel computo, usa A.6.1 a quantita' piena come posa generica (da confermare a Riccardo nel ri-collaudo)"
  - "Sottofondo Unilin -> famiglia sottofondo_laminato (distinta da fornitura_pavimento_laminato) pur condividendo l'opzione 'laminato': bersaglio condiviso volutamente su due famiglie diverse"

requirements-completed: [CFG-02, CFG-04]

duration: ~70min
completed: 2026-09-28
---

# Phase 09 Plan 09: Regole di curatela G1/G2 (generatore + applicazione) Summary

**proponi_assegnazione governa laminato/vinilico/moquette/sottofondo e A.6 intera per opzione, applica_assi gestisce bersagli condivisi fra opzioni e fallisce rumorosamente su opzioni/chiavi non risolte, invece di sommare in silenzio le alternative del pavimento**

## Performance

- **Duration:** ~70 min
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Chiusa la classe di bug "voce alternativa mai governata -> sempre inclusa -> sommata" (G1/G2 di `09-HUMAN-UAT.md`) alla SORGENTE della curatela: le nuove regole vivono in `genera_excel_taratura.py` e `applica_taratura.py`, non in un fix a mano su `seed-domande.json` (che il prossimo `--solo-assi` cancellerebbe).
- `proponi_assegnazione` ora produce una riga `PropostaAsse` per ogni coppia (voce, opzione): A.6.2/.7/.8/.10 coprono tutte le loro alternative di pavimento, A.6.3/.4 l'asse finitura, A.6.9 e' esclusa di default; vinilico/laminato/sottofondo/moquette (oggi "sempre incluse") e i battiscopa alternativi finiscono sull'asse `tipo_pavimento`.
- La fornitura gres a pavimento (sottocategoria "PAVIMENTI E RIVESTIMENTI GRES", testo "per pavimentazion...") ha famiglia dedicata `fornitura_pavimento_gres` e la stessa quota bagno (D-02, `_FATTORE_BAGNO_PROPOSTO`) delle altre cinque opzioni; il gres di rivestimento resta invariato.
- `applica_assi` traduce correttamente una voce inclusa da PIU' opzioni dello stesso asse (bersagli condivisi, D-08) senza sovrascritture, e continua a dedupllicare le famiglie con quota bagno anche sull'asse finitura.
- Fail-loud in due punti: `ValueError` quando il file di taratura cita un'opzione o una domanda assente dal seed (prima: `continue` silenzioso); `RuntimeError` nel template di migrazione emesso se il catalogo e' presente e almeno una chiave naturale non si risolve, dopo aver risolto tutte e quattro le sezioni prima di scrivere.
- Nuova `aggiorna_foglio_assi()` + CLI `--aggiorna-assi PERCORSO` (ripetibile): riscrive il foglio `assi_proposti` di un workbook esistente preservando `decisione`/`note` gia' scritte per riga identica, senza toccare `coefficienti_pro`.

## Task Commits

1. **Task 1: Regole di proposta per i nuovi pavimenti, A.6 intera e gres a pavimento + aggiornamento del foglio assi** - `74bc62a` (feat)
2. **Task 2: applica_assi con bersagli condivisi e fail-loud, diff e template di migrazione corretti** - `ca7f121` (feat)

_Entrambi i task erano `tdd="true"`: test scritti prima del codice, verificati rossi con l'assenza delle nuove funzioni/costanti e poi verdi dopo l'implementazione, in un unico ciclo per task (non due commit separati test/feat, per restare aderenti alla struttura gia' in uso nel resto della fase 09)._

## Files Created/Modified

- `backend/scripts/genera_excel_taratura.py` - `_MAPPA_A6_TIPO_PAVIMENTO` estesa a (asse, famiglia, tupla opzioni); `OPZIONI_CON_QUOTA_BAGNO_A6_1`, `OPZIONI_TIPO_PAVIMENTO` nuove costanti; regole 1/3/4 di `proponi_assegnazione` estese; `aggiorna_foglio_assi()` + `--aggiorna-assi` in `main()`
- `backend/scripts/applica_taratura.py` - skip dell'`includi` ristretto alle sole righe `tipo_pavimento` di voci con quota bagno; `ValueError` su opzione/domanda sconosciuta; `_record_effetti` con `includi` a frozenset; diff di `emetti_migrazione` bersaglio-condiviso-aware; `_catalogo_presente()` + guardia `RuntimeError` a due fasi in `upgrade()`
- `backend/tests/test_taratura_pro.py` - `TestProponiAssegnazioneA6Intera`, `TestProponiAssegnazioneForniturePavimenti`, `TestProponiAssegnazioneGresAPavimento`, `TestAggiornaFoglioAssi`
- `backend/tests/test_applica_taratura.py` - `TestApplicaAssiBersagliCondivisi`, `TestApplicaAssiGresAPavimentoFinituraEFattore`, `TestApplicaAssiOpzioneSconosciuta`, `TestRecordEffettiBersagliCondivisi`, `TestTemplateGuardiaCatalogoPresente` (esercita `upgrade()` su un DB reale portato alla testa via Alembic, copia temporanea di `alembic/`, mai il file vero)

## Decisions Made

- Moquette esclusa dalla quota bagno di A.6.1: nessuna posa dedicata nel computo per la moquette, resta sulla posa generica A.6.1 a quantita' piena — decisione di Claude, segnalata nel motivo della riga per il ri-collaudo di Riccardo.
- Il sottofondo Unilin (famiglia `sottofondo_laminato`) e la fornitura laminato (famiglia `fornitura_pavimento_laminato`) condividono deliberatamente l'opzione `laminato`: sono due voci distinte del computo (sottofondo in schiuma vs. pavimento laminato) che devono comparire entrambe quando l'utente sceglie laminato — proprio il caso "bersagli condivisi" che il Task 2 doveva gestire senza sovrascritture.

## Deviations from Plan

None - plan eseguito come scritto. Le tre righe di dettaglio implementative (mappa A.6, regole 3/4, guardia del template) seguono l'azione descritta nel piano; le uniche scelte lasciate aperte dal testo (moquette su A.6.1, famiglia distinta per il sottofondo) sono documentate sopra come decisioni, non deviazioni.

## Issues Encountered

Il primo tentativo di scrivere `_catalogo_presente`/la guardia `RuntimeError` dentro `_TEMPLATE_MIGRAZIONE` ha rotto `emetti_migrazione` con `KeyError: 'categoria_code'`: l'intero template passa per `str.format()`, quindi ogni graffa singola nel testo del modulo emesso (f-string con `{variabile}` destinate a runtime, non a `.format()`) doveva essere raddoppiata (`{{variabile}}`). Corretto raddoppiando le graffe nei quattro messaggi di `non_risolte.append(...)` e nel messaggio del `RuntimeError`; verificato rieseguendo sia la suite dei due file toccati sia `test_migrazioni_sqlite.py` (che esercita lo stesso template su Alembic reale) — 131 test verdi in totale.

## User Setup Required

None - nessuna configurazione di servizi esterni richiesta.

## Next Phase Readiness

- Le regole G1/G2 vivono ora nella sorgente ripetibile della curatela (generatore + convertitore), con i loro test unitari su voci/decisioni sintetiche: nessun numero di taratura reale cablato.
- L'applicazione ai dati reali (rigenerazione del workbook su `dev.db`, aggiornamento di `seed-domande.json`/`famiglie_alternative_pro.json`, migrazione emessa e verificata sul catalogo reale) resta al piano **09-10**, come previsto dall'obiettivo del piano.
- Nessuna modifica a `backend/seed_data/`, `docs/taratura/` o alla migrazione `0022` gia' emessa (verificato con `git diff --stat`).

---
*Phase: 09-configuratore-pro*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: `.planning/phases/09-configuratore-pro/09-09-SUMMARY.md`
- FOUND: commit `74bc62a`
- FOUND: commit `ca7f121`
