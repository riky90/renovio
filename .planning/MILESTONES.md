# Milestones

## v2.0 domande e motore parametrico (Completata: 2026-10-01, non ancora in produzione)

**Phases completed:** 7 phases (05, 06, 07, 08, 08.1, 09, 10), 53 plans, 71 tasks
**Requirements:** 30/30 (audit `passed`, `.planning/milestones/v2.0-MILESTONE-AUDIT.md`)
**Git range:** `5ea305b` (2026-09-21) → `2cb7deb` (2026-10-01), 350 commit sopra `origin/main`
(`f011ed4`, v1.0). Codice applicativo: 207 file, +46.044 / −1.780 righe.
**Test:** suite backend 1008 passed / 5 skipped.

**Delivered:** la stima smette di rispondere solo a `(citta, mq, tipo)` e risponde a com'e'
fatta la casa e cosa si vuole farci, con domande, opzioni ed effetti curabili come dati dal
pannello admin.

**Key accomplishments:**

- Catalogo domande in database con otto tipi di effetto chiusi: il motore Free e' parametrico
  e resta identico alla v1 quando nessuno risponde (fase 05).
- Un solo wizard a quattro step per Free e Pro, con domande e default serviti dal DB, piu' il
  forfait arredo a range accanto al totale lavori e il Bonus Mobili accendibile (fasi 06-07).
- Curatela fuori dal `dev.db`: export/import Excel a round-trip zero per listini, parametri,
  lead e catalogo domande, con pagina CRUD `/admin/domande` e disattivazione al posto della
  cancellazione (fasi 08, 08.1).
- Configuratore Pro: assi finitura e pavimento come dati, nessuna alternativa sommata
  (verificato da un test che conta le voci per famiglia), sette opzioni di pavimento,
  coefficienti in bozza tarabile (fase 09).
- Risultato leggibile: RangeBar proporzionale, €/m² e peso per categoria, riepilogo IVA,
  pannello Bonus, budget dichiarato con confronto a finiture inferiori, sul web e nei PDF Free
  e Pro (fase 10).
- Audit di milestone: corretti il PDF Pro senza detrazioni e arredo (M1) e la finitura del
  wizard ignorata dal Pro (M2); percorso Pro collaudato dal vivo il 2026-10-01 (WIZ-04).

**Known deferred items at close:** 5 (see STATE.md Deferred Items). Collaudo dei PDF al
go-live; prova delle migrazioni 0014-0024 su Postgres, taratura A.6.11 e
`BACKEND_PUBLIC_URL` prima del push.

---

## v1.0 MVP (Shipped: 2026-09-09)

**Phases completed:** 4 phases (01-04), 30 plans. In produzione: backend su Render,
frontend su Vercel. Archivio: `.planning/milestones/v1.0-ROADMAP.md`.

---
