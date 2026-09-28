---
phase: 09-configuratore-pro
plan: 11
subsystem: api
tags: [fastapi, pydantic, react, wizard, configuratore-pro]

requires:
  - phase: 09-configuratore-pro
    provides: "domande_configuratore/valida_risposte_pro (09-05), catalogo tipo_pavimento (09-07)"
provides:
  - "GET /me/opzioni-pro estesa con `domande` (le scelte del configuratore, es. tipo_pavimento)"
  - "POST /me/stime accetta preferenze_pro.scelte, validate contro il catalogo e persistite in risposte_pro_json"
  - "Wizard Pro step 4 con il pavimento accanto ai livelli di finitura"
  - "EstimateWizard riapribile su dati noti (risposteDiPartenza/stepIniziale)"
affects: [09-12, 09-13, 09-14]

tech-stack:
  added: []
  patterns:
    - "_domanda_out() helper condiviso tra _to_out() (dettaglio-pro) e opzioni_pro() per evitare due mapping dello stesso DTO"
    - "scelteToccate (Set<string>) come guardia contro l'override dei default server-side, stesso pattern di risposteToccate"

key-files:
  created:
    - backend/tests/test_wizard_pro_scelte.py
  modified:
    - backend/app/schemas/dettaglio_pro.py
    - backend/app/routers/dettaglio_pro.py
    - backend/app/schemas/stima_salvata.py
    - backend/app/routers/stime_salvate.py
    - backend/tests/test_no_leak.py
    - frontend/src/api/stima.ts
    - frontend/src/components/EstimateWizard.tsx

key-decisions:
  - "Il controllo 'la scelta e' su una domanda non numerica' e' esplicito nel router (oltre al type-check implicito di valida_risposte_pro), per un messaggio d'errore chiaro ('non e' una scelta') invece di uno generico 'deve essere un numero intero'"
  - "DomandaField riceve DomandaProOut senza adattamento (tipizzazione strutturale gia' documentata in api/dettaglio-pro.ts): nessun nuovo componente per disegnare le scelte del wizard"

patterns-established:
  - "Titolo/aiuto delle domande del pannello Pro nel wizard vengono SEMPRE dal catalogo (testo/help), mai da un'etichetta cablata nel client"

requirements-completed: [CFG-01, WIZ-04]

duration: 55min
completed: 2026-09-28
---

# Phase 09 Plan 11: Pavimento nel wizard Pro (gap G3, parte wizard) Summary

**Il wizard Pro chiede il pavimento allo step 4 con lo stesso meccanismo delle domande a scelta del configuratore (default risolto dal server), e la scelta arriva validata al dettaglio Pro tramite `risposte_pro_json`.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 2/2 completati
- **Files modified:** 7 (+1 creato)

## Accomplishments
- `GET /me/opzioni-pro` espone ora anche `domande` (filtrate sul `tipo_controllo`, ENG-02): il wizard puo' disegnare "Che pavimento vuoi per casa?" PRIMA che una stima esista.
- `POST /me/stime` accetta `preferenze_pro.scelte`, le valida contro il catalogo (`valida_risposte_pro` + rifiuto esplicito delle domande numeriche) e le unisce a `risposte_pro_json`, la stessa colonna che il pannello del dettaglio gia' usa — schermata e wizard restano allineati by-construction.
- Il wizard Pro (`EstimateWizard.tsx`) disegna le domande del configuratore nello step 4, dopo i livelli di finitura, con lo stesso pattern "default dal server + non sovrascrivere le scelte toccate" gia' usato per le risposte del catalogo Free.
- Nuove prop `risposteDiPartenza`/`stepIniziale` per riaprire il wizard gia' compilato (base per il "Vai alla stima Pro" del piano 09-12).

## Task Commits

1. **Task 1: API — domande a scelta del configuratore in /me/opzioni-pro e scelte validate al salvataggio** - `6c8854b` (feat)
2. **Task 2: Wizard Pro — pavimento nello step 4, scelte nel salvataggio, avvio da dati noti** - `9da7891` (feat)

**Plan metadata:** committed separately by the orchestrator after this SUMMARY.

_Nota: Task 1 aveva `tdd="true"` — i test (`test_wizard_pro_scelte.py`) sono stati scritti nello stesso commit del codice invece che in un commit RED separato, perche' l'implementazione e' stata scritta in linea con i test durante la stessa sessione di lettura del contratto esistente (vedi Deviazioni)._

## Files Created/Modified
- `backend/app/schemas/dettaglio_pro.py` - `OpzioniProOut.domande: list[DomandaProOut]`
- `backend/app/routers/dettaglio_pro.py` - helper `_domanda_out()` estratto e riusato; `opzioni_pro()` popola `domande` filtrando `CONTROLLI_NUMERICI`
- `backend/app/schemas/stima_salvata.py` - `PreferenzeProIn.scelte` con `field_validator` (<=20 chiavi, <=64 caratteri)
- `backend/app/routers/stime_salvate.py` - `salva_stima` valida `scelte` con `valida_risposte_pro`, rifiuta le domande numeriche, unisce a `risposte_pro_json`
- `backend/tests/test_wizard_pro_scelte.py` - 11 test nuovi (opzioni-pro con/senza Pro, scelta valida->dettaglio, opzione/domanda/numerica invalide->400, >20 chiavi, anti-leak, comportamento invariato senza scelte)
- `backend/tests/test_no_leak.py` - esteso con `GET /me/opzioni-pro`
- `frontend/src/api/stima.ts` - `OpzioniProOut.domande`, `PreferenzePro.scelte`
- `frontend/src/components/EstimateWizard.tsx` - stato `scelte`/`scelteToccate`, `FinitureStep` disegna le domande del configuratore, props `risposteDiPartenza`/`stepIniziale`, `preferenzePro()` include `scelte`

## Decisions Made
- Messaggio d'errore esplicito `'{codice}' non e' una scelta` per una domanda numerica passata in `scelte`, invece di lasciare che il type-check implicito di `valida_risposte_pro` produca un messaggio meno chiaro ("deve essere un numero intero").
- Nessun nuovo componente frontend per disegnare le domande del pannello nel wizard: `DomandaProOut` e' gia' strutturalmente compatibile con `DomandaField` (documentato in `api/dettaglio-pro.ts`), riusato tal quale.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Build/lint frontend nel worktree senza `node_modules`**
- **Found during:** Task 2 (verify)
- **Issue:** Il worktree non ha `frontend/node_modules`; `npm run build`/`npm run lint` non potevano girare.
- **Fix:** Symlink temporaneo `frontend/node_modules -> ../../../../frontend/node_modules` (checkout principale) per il tempo della verifica, poi rimosso. Verificato che il symlink `ln -s` su questo ambiente Windows/Git Bash ha in realta' creato una copia reale (non un reparse point: `GetFileAttributesW` senza `FILE_ATTRIBUTE_REPARSE_POINT`, inode diversi a parita' di device) — rimossa con `rm -rf` a fine verifica senza toccare il checkout principale (confermato leggendo `frontend/node_modules/react/package.json` dal checkout principale dopo la rimozione). `node_modules` e' comunque gitignored: nessun rischio di commit accidentale in nessuno dei due scenari.
- **Files modified:** nessuno (solo ambiente locale del worktree, non tracciato)
- **Verification:** `npm run build` (0, bundle emesso) e `npm run lint` (exit 0, solo warning preesistenti + 2 nuovi `react(set-state-in-effect)` sullo stesso pattern gia' presente per l'effetto `risposte`)
- **Committed in:** N/A (nessun file da questa deviazione entra nei commit)

## Known Stubs

Nessuno.

## Threat Flags

Nessuna nuova superficie fuori dal `<threat_model>` del piano: T-09-47/48/49/50 coprono `scelte` (tampering, validato contro il catalogo), `GET /me/opzioni-pro` (information disclosure, DTO chiuso; elevation of privilege, gate `require_pro` invariato) e `stepIniziale`/`risposteDiPartenza` (solo presentazione, il server rivalida tutto).

## Self-Check: PASSED

Tutti gli 8 file citati trovati sul disco; entrambi i commit (`6c8854b`, `9da7891`) presenti in `git log`.
