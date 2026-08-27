---
phase: 03-pro-dettaglio-sottocategorie
plan: 04
subsystem: backend
tags: [fastapi, weasyprint, jinja2, pdf, paywall, decimal]

requires:
  - phase: 03-pro-dettaglio-sottocategorie
    provides: "DettaglioProService.compute() bottom-up + GET/POST dettaglio-pro dietro require_pro (03-03)"
provides:
  - "PdfService.render_pro() — PDF Pro multi-pagina brandizzato, recompute-live, asimmetria documentata vs render() (Free)"
  - "pdf_stima_pro.html — template Jinja2 multi-pagina, categoria->sottocategoria->voci a range"
  - "GET /me/stime/{id}/pdf-pro dietro require_pro, parita' by-construction col JSON via _compute_dettaglio() condiviso"
  - "test_pdf_pro.py — paywall/IDOR sempre attivi, test di parita' numerica non-byte, byte-generating skip-graceful senza GTK3"
affects: ["03-06 (bottone download PDF Pro nel frontend)"]

tech-stack:
  added: []
  patterns:
    - "_compute_dettaglio() helper unico condiviso da GET dettaglio-pro, POST risposte e GET pdf-pro — parita' schermata/PDF by-construction, non da un test a posteriori (Pitfall 2)"
    - "PdfService.render_pro() recompute-live, opposto deliberato di render() (Free, solo snapshot congelato) — asimmetria documentata nel docstring di modulo"

key-files:
  created:
    - backend/app/templates/pdf_stima_pro.html
    - backend/tests/test_pdf_pro.py
  modified:
    - backend/app/services/pdf_service.py
    - backend/app/routers/dettaglio_pro.py

key-decisions:
  - "Docstring del template pdf_stima_pro.html riformulato per non contenere letteralmente coefficiente_impresa/base_eur_mq/prezzo_impresa/moltiplicatore, stesso precedente 02/03-03 per rispettare il criterio grep meccanico"
  - "build_filename_pro() aggiunto come funzione dedicata (suffisso -dettaglio-) invece di parametrizzare build_filename(), per non toccare il contratto gia' testato della Free"

requirements-completed: [PDF-02, PRO-02]

duration: 20min
completed: 2026-08-27
---

# Phase 3 Plan 04: PDF Pro dettagliato Summary

**`PdfService.render_pro()` genera un PDF multi-pagina brandizzato con sottocategorie/voci a range, calcolato LIVE dalla stessa `DettaglioProService.compute()` del JSON tramite un unico helper `_compute_dettaglio()` condiviso — schermata e PDF non possono divergere by-construction.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-08-27T07:50:00Z
- **Completed:** 2026-08-27T08:10:00Z
- **Tasks:** 2 completati
- **Files modified:** 4 (2 creati, 2 modificati)

## Accomplishments

- `PdfService.render_pro(dettaglio, stima, user) -> bytes` con import WeasyPrint lazy (invariato dal limite GTK3 Windows) e docstring di modulo che documenta esplicitamente l'asimmetria deliberata recompute-live (Pro) vs snapshot-frozen (Free) — una regressione da "correggere" in futuro sarebbe un bug, non un fix
- `pdf_stima_pro.html`: header brandizzato con badge PRO, riepilogo input, disclaimer di non-riconciliazione (D-01), iterazione `categoria -> sottocategoria -> voci` con colonne descrizione/UM/quantità stimata/range `€ min – € max`, paginazione via `@page`/`break-inside: avoid` (nessuna nuova libreria), riga "Nessuna voce stimata" per sottocategorie vuote, footer legale invariato dal Free
- `_compute_dettaglio(session, row)` estratto nel router come unico punto di calcolo, chiamato da GET dettaglio-pro, POST risposte e il nuovo GET pdf-pro — garantisce la parità schermata/PDF per costruzione (non serve una riconciliazione a runtime, RESEARCH Pitfall 2)
- `GET /me/stime/{id}/pdf-pro` dietro `require_pro`, ownership `id+user_id` → 404 anti-IDOR, `StreamingResponse` `application/pdf` con `Content-Disposition: attachment` (filename con suffisso `-dettaglio-`)
- `test_pdf_pro.py`: matrice 401/403/404 sempre attiva (non richiede GTK3), test di parità numerica esplicito (`_compute_dettaglio()` interno vs risposta HTTP del GET JSON, confronto byte-per-byte del DTO serializzato), test byte-generating skip-graceful anti-leak sui bytes del PDF, guard statico anti-`EstimationService`
- Suite backend completa 106/106 passed + 4 skip invariati (GTK3, 2 Free + 2 Pro)

## Task Commits

1. **Task 1: PdfService.render_pro() + template pdf_stima_pro.html** - `253b82b` (feat)
2. **Task 2: Endpoint GET pdf-pro (recompute-live via stesso compute) + test parità/paywall/anti-leak** - `7bf402f` (feat)

## Files Created/Modified

- `backend/app/services/pdf_service.py` - `render_pro()`, `build_filename_pro()`, docstring di modulo esteso con l'asimmetria Free/Pro documentata
- `backend/app/templates/pdf_stima_pro.html` - template multi-pagina Jinja2/WeasyPrint, branding Slate/blue-600, anti-leak, sempre a range
- `backend/app/routers/dettaglio_pro.py` - `_compute_dettaglio()` helper condiviso, `GET /stime/{id}/pdf-pro` dietro `require_pro`
- `backend/tests/test_pdf_pro.py` - paywall/IDOR sempre attivi, test di parità numerica, byte-generating skip-graceful, guard anti-EstimationService

## Decisions Made

Vedi `key-decisions` in frontmatter. Nessuna decisione architetturale nuova: entrambe le scelte sono estensioni dirette dei pattern già stabiliti in 02-08/03-03 (docstring senza stringhe letterali per il grep meccanico; filename dedicato invece di parametrizzare quello esistente per non toccare un contratto già testato).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Commento HTML in `pdf_stima_pro.html` conteneva letteralmente le stringhe impresa vietate**
- **Found during:** Task 1, verifica finale del grep di accettazione del piano
- **Issue:** Il commento HTML di intestazione del template dichiarava esplicitamente `coefficiente_impresa/base_eur_mq/prezzo_impresa/moltiplicatore` come mai emessi, facendo fallire il criterio meccanico `grep -rn -E '...' == 0` (il pattern del piano non esclude i commenti HTML come farebbe `grep -v '^#'` sui `.py`)
- **Fix:** Riformulato il commento per non contenere le stringhe letterali, mantenendo lo stesso significato ("nessuna margine impresa-side")
- **Files modified:** `backend/app/templates/pdf_stima_pro.html`
- **Verification:** `grep -rn -E 'coefficiente_impresa|base_eur_mq|prezzo_impresa|moltiplicatore' backend/app/templates/pdf_stima_pro.html backend/app/services/pdf_service.py backend/app/routers/dettaglio_pro.py` == 0 (nessun match)
- **Committed in:** `253b82b` (Task 1 commit — corretto prima del commit, mai committato rotto)

---

**Total deviations:** 1 auto-fixed (1 bug di conformità al criterio meccanico di accettazione)
**Impact on plan:** Nessuno scope creep — correzione necessaria per rispettare il criterio letterale del piano, stesso precedente già visto in 02-account-pdf e 03-03.

## Issues Encountered

None oltre alla deviazione sopra documentata.

## Known Stubs

Nessuno. Il PDF Pro rende dati reali calcolati da `DettaglioProService.compute()` (stesso motore di 03-03, seed reale RE), non un placeholder di sviluppo.

## User Setup Required

None — nessuna configurazione di servizio esterno richiesta. Come per 02-08/03-03, la verifica byte-generating del PDF Pro resta skip-graceful su questa macchina Windows senza GTK3 (fallback accettato, verifica in produzione Railway/Debian).

## Threat Flags

Nessuna superficie non prevista dal `<threat_model>` del piano: T-03-08 (elevation of privilege), T-03-06b (IDOR), T-03-01d (information disclosure) e T-03-09 (drift schermata/PDF) erano già registrate e mitigate come pianificato.

## Next Phase Readiness

- Backend Pro completo: motore (03-03) + PDF (03-04) pronti per il consumo dal frontend (03-05/03-06).
- `_compute_dettaglio()` è ora il singolo punto di verità per il dettaglio Pro, riusabile senza rischio di divergenza da qualunque futura rotta che debba leggere lo stesso calcolo.
- Nessun blocco noto.

---
*Phase: 03-pro-dettaglio-sottocategorie*
*Completed: 2026-08-27*

## Self-Check: PASSED

Tutti i file creati verificati presenti su disco (`pdf_stima_pro.html`, `test_pdf_pro.py`); entrambi i commit di questo piano (`253b82b`, `7bf402f`) verificati presenti in `git log`.
