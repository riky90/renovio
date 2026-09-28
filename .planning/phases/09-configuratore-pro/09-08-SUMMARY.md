---
phase: 09-configuratore-pro
plan: 08
subsystem: database
tags: [alembic, dev-db, chiusura-fase, controlli-api, human-uat]

# Dependency graph
requires:
  - phase: 09-configuratore-pro plan 04
    provides: "migrazione 0021 (asse finitura + stepper mirati da curatela esistente)"
  - phase: 09-configuratore-pro plan 06
    provides: "migrazione 0022 (taratura approvata su tre canali)"
  - phase: 09-configuratore-pro plan 07
    provides: "applica_assi.py, regola D-02 quota bagno, fixture famiglie_alternative_pro.json"
provides:
  - "backend/dev.db portato a 0022 (head) e seminato, con backup pre-migrazione"
  - "controlli automatici del percorso Pro via API verdi su copia di dev.db (default D-07, regola bagno D-02, stepper bagni, anti-leak)"
  - "09-HUMAN-UAT.md: checklist del collaudo dal vivo di Riccardo, registrata come pending/non bloccante (WIZ-04)"
affects: [09-09, 09-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Controlli API a-e eseguiti con uno script Python usa-e-getta (scratchpad, non versionato) che monta FastAPI TestClient su una COPIA sqlite di dev.db, mai sul file reale — stesso pattern engine-swap/monkeypatch SessionLocal dei test esistenti (test_dettaglio_pro_paywall.py)"
    - "Controllo anti-leak (d) sulle SOLE chiavi del JSON, non su substring del testo delle descrizioni: 'effett' come substring grezza produce falsi positivi legittimi ('effettuato' nelle descrizioni voce del computo)"

key-files:
  created:
    - .planning/phases/09-configuratore-pro/09-HUMAN-UAT.md
  modified: []

key-decisions:
  - "Controllo (e) PDF: SKIP graceful, non fallimento — stesso limite ambientale GTK3/WeasyPrint su Windows gia' documentato dal piano 02-08 in poi (probe runtime via OSError, non un check hardcoded su sys.platform)"
  - "Nessun commit di codice per il Task 1: dev.db, il suo backup e lo script di controllo sono tutti gitignored/scratchpad per costruzione (CLAUDE.md, D-41); l'unico artefatto versionato del piano e' 09-HUMAN-UAT.md (Task 2)"
  - "Checklist scritta con lo stesso testo del piano, senza indentazione, per rispettare l'automated verify (grep '^- \\[ \\]')"

requirements-completed: [WIZ-04]

# Metrics
duration: ~35min
completed: 2026-09-28
---

# Phase 09 Plan 08: dev.db allo stato finale, gate completi, controlli API automatici, collaudo rinviato Summary

**`backend/dev.db` migrato a `0022 (head)` e seminato (con backup), suite/build/lint verdi, cinque controlli automatici del percorso Pro via API verdi su una copia del DB, e `09-HUMAN-UAT.md` pronto con la checklist del collaudo dal vivo di Riccardo registrata come pending, non bloccante — le fasi 09-10 proseguono senza aspettarlo.**

## Performance

- **Duration:** ~35 min (esclusa l'attesa della suite backend, ~26 min)
- **Tasks:** 2/2
- **Files modified:** 1 creato (`09-HUMAN-UAT.md`)

## Accomplishments

- **Backup + migrazione**: `backend/dev.db.bak-pre-0021-20260928-084905` creato prima di
  qualunque scrittura; `alembic upgrade head` da `0020` a `0022 (head)` (passa per `0021`
  asse finitura/stepper mirati e `0022` taratura approvata); `scripts/seed.py` rieseguito
  (create-if-missing, D-41 — nessuna riscrittura della curatela esistente).
- **Conteggi post-migrazione** su `dev.db`: `voce.livello` non nulli **21** (invariati, come
  atteso dal 09-04), `coefficiente_qta_voce.domanda_mirata_key` non nulli **144** (invariati);
  effetti `includi` **48**, `quantita_per_unita` **48**, `escludi` **32**, `fattore_quantita`
  **3**, `eur_mq_categoria` **7**, `moltiplicatore_categoria` **47**, `eur_per_scostamento`
  **12**, `eur_fisso_categoria` **2** — **199 effetti totali**; `coefficiente_qta_voce`
  totali **573**.
- **Suite backend completa**: `818 passed, 5 skipped` in 26min16s (`.venv/Scripts/python.exe
  -m pytest -q`), nessun rosso.
- **Build e lint frontend**: `npm run build` verde (`tsc -b && vite build`, 2122 moduli,
  warning solo sulla dimensione del chunk); `npm run lint` (`oxlint`) exit 0, solo warning
  preesistenti (`only-export-components`, `set-state-in-effect`), nessun errore.
- **Server avviati e fermati**: backend (`uvicorn app.main:app` su 127.0.0.1:8000) verificato
  con `curl http://127.0.0.1:8000/api/v1/health/db` -> `{"status":"ok","listini":1,"storage":"db"}`;
  processo fermato prima di chiudere il piano (porta 8000 libera per il riavvio
  dell'orchestratore). Il frontend non e' stato avviato in questo piano (la verifica /health
  richiedeva solo il backend; porta 5173 comunque libera).
- **Cinque controlli automatici (a)-(e)** eseguiti con uno script usa-e-getta in scratchpad
  su una **copia** di `dev.db` (mai il file reale), via `TestClient` con `SessionLocal`
  monkeypatchata sulla copia: utente Pro registrato, attivato, stima NUOVA creata
  (Reggio Emilia, 85 m2, totale) — vedi tabella sotto.

## Controlli API (a)-(e)

| Controllo | Esito | Dettaglio |
|---|---|---|
| (a) default: A.6 una sola posa, B-FINITURE max 1/famiglia | **VERDE** | A.6 presenti: `A.6.1, A.6.10, A.6.11, A.6.3, A.6.4, A.6.7, A.6.8, A.6.9` (nessuna delle altre pose A.6.2/.5/.6); nessuna famiglia B-FINITURE con piu' di una voce |
| (b) `tipo_pavimento=parquet`: posa parquet presente, quota bagno gres resta (D-02) | **VERDE** | A.6 con parquet: aggiunge `A.6.2`, mantiene `A.6.1`; 7 voci del bagno (sottocategoria GRES) presenti |
| (c) bagni=2 -> quantita' raddoppiata | **VERDE** | bagni=1 -> 1.0, bagni=2 -> 2.0 (voce "Miscelatore cromato monocomando da incasso per doccia/vasca") |
| (d) nessuna chiave JSON con "impresa"/"coefficiente"/"effett" | **VERDE** | controllo ricorsivo sulle chiavi del JSON (non sul testo delle descrizioni: "effettuato" e' testo legittimo del computo, non una chiave) |
| (e) PDF dettagliato Pro (200, content-type pdf) | **SKIP** (non un fallimento) | WeasyPrint/GTK3 non disponibile su questa macchina Windows — stesso limite noto e documentato dal piano 02-08 in poi; probe runtime (import + catch `OSError`), la logica resta coperta dai test della suite (skip-graceful), verificabile a byte in ambiente con GTK3 |

## Task Commits

1. **Task 1: dev.db allo stato finale, gate completi, controlli API** — nessun commit di
   codice: `dev.db`, il suo backup e lo script di controllo usa-e-getta sono tutti
   gitignored/scratchpad per costruzione (nessun file tracciato modificato da questo task).
2. **Task 2: 09-HUMAN-UAT.md** — `b890aea` (docs) — checklist del collaudo rinviato, stato
   pending, esiti dei controlli automatici del Task 1 riportati in testa al file.

## Files Created/Modified

- `.planning/phases/09-configuratore-pro/09-HUMAN-UAT.md` — nuovo: frontmatter `status:
  pending`/`requirement: WIZ-04`, sezione Stato con la tabella dei controlli automatici,
  sezione "Come si avvia", sezione "Se una voce fallisce", 16 voci di checklist (testo
  invariato dal piano), sezione Esito da compilare da Riccardo.
- `backend/dev.db` (non tracciato) — migrato `0020 -> 0022 (head)`, seminato.
- `backend/dev.db.bak-pre-0021-20260928-084905` (non tracciato) — backup pre-migrazione.

## Decisions Made

- Controllo (e) trattato come SKIP graceful (non rosso che blocca il piano): stesso limite
  ambientale GTK3/WeasyPrint gia' accettato in tutta la fase 02 e successive su questa
  macchina Windows; la produzione (Debian/Render) ha GTK3 nativo.
- Il controllo anti-leak (d) verifica le CHIAVI del JSON, non fa un substring-match grezzo
  sul testo intero della risposta: la prima versione dello script falliva su "effettuato"
  (parola italiana legittima in una descrizione voce del computo), un falso positivo
  corretto prima di considerare il controllo definitivo.
- Nessun file di codice modificato in questo piano: e' un piano di chiusura ambientale/
  verifica, coerente con `files_modified: [.planning/.../09-HUMAN-UAT.md]` dichiarato nel
  frontmatter del piano.

## Deviations from Plan

Nessuna deviazione Rule 1-4. Un solo aggiustamento nello script di controllo usa-e-getta
(non un file del piano, scratchpad non versionato): il controllo (d) e' stato corretto da
substring grezza su tutto il testo della risposta a controllo sulle sole chiavi del JSON,
perche' la versione iniziale produceva un falso positivo su "effettuato" (parola italiana
legittima, non una chiave vietata). Non e' una deviazione dal codice di produzione — lo
script non viene committato.

## Known Stubs

Nessuno.

## Threat Flags

Nessuno. La migrazione tocca solo `dev.db` locale (trust boundary gia' registrato nel
threat_model del piano); il controllo (d) di questo piano copre esattamente T-09-25
(Information Disclosure sul JSON del dettaglio).

## Issues Encountered

Nessuno bloccante. Vedi Deviations per l'aggiustamento del falso positivo nello script di
controllo (non nel codice di produzione).

## User Setup Required

Nessuna azione di servizio esterno. Il collaudo dal vivo (WIZ-04) resta a Riccardo, quando
potra' farlo — non blocca le fasi 09-10 (vincolo del 2026-09-26).

## Next Phase Readiness

- WIZ-04 e' verificato automaticamente via API (percorso Pro end-to-end: paywall, default,
  regola bagno D-02, stepper, anti-leak) e pronto per il collaudo dal vivo, registrato come
  pending in `09-HUMAN-UAT.md`.
- `backend/dev.db` e' allo stato finale della fase (`0022 head`, seminato) — nessuna
  migrazione pendente per le fasi 09-09/09-10.
- Nessun push: la milestone si pusha a fine Fase 10 (decisione di Riccardo).
- La fase 09 risulta 8/8 piani completi con questo piano.

---
*Phase: 09-configuratore-pro*
*Completed: 2026-09-28*

## Self-Check: PASSED

- `.planning/phases/09-configuratore-pro/09-HUMAN-UAT.md` — FOUND
- `backend/dev.db.bak-pre-0021-20260928-084905` — FOUND
- Commit `b890aea` — FOUND in `git log`
- `alembic current` su `backend/dev.db` — `0022 (head)` confermato
- Suite backend completa — 818 passed, 5 skipped confermato dall'output del comando
