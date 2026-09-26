# Deferred items — Phase 09 (09-03)

## test_health.py::test_health_db_returns_live_count fails in questo ambiente

- **Trovato durante:** verifica finale del piano 09-03 (suite completa, non richiesta dal
  piano ma lanciata per prudenza dopo lo swap del motore Pro).
- **Sintomo:** `sqlalchemy.exc.OperationalError: no such table: listino`.
- **Causa:** il test istanzia `TestClient(app)` senza monkeypatchare `SessionLocal`, quindi
  colpisce il DB configurato dall'ambiente (`dev.db`), assente in questo worktree (per
  costruzione: i worktree non contengono file gitignored come `backend/dev.db`).
- **Fuori scope:** non ha nulla a che fare con `effetti.py`/`dettaglio_pro.py`; non toccato
  da nessun task del piano 09-03. Non corretto qui (Rule scope boundary).

## test_dettaglio_pro.py::test_post_risposte_payload_generico_ricalcola_e_valida fallisce (pre-esistente, non causato dal 09-06)

- **Trovato durante:** verifica suite completa dopo il Task 2 del piano 09-06.
- **Sintomo:** `assert "A.6.1" not in codici_a6` fallisce — A.6.1 resta nel computo anche con
  `tipo_pavimento=parquet`.
- **Causa:** il test e' stato scritto nel 09-05 (`5dbfdf7`, "contratto API generico"), PRIMA
  della decisione D-02 del 09-07 (`596f370`, gia' in `239e5f1` a inizio di questo piano): A.6.1
  (quota bagno) resta SEMPRE inclusa a prescindere dal pavimento scelto per il resto della casa
  — vedi `test_dettaglio_pro_alternative.py` e la docstring di `applica_assi` in
  `scripts/applica_taratura.py`. Il test 09-05 non e' mai stato aggiornato per il nuovo
  comportamento.
- **Fuori scope:** nessun task del piano 09-06 tocca il routing/schema di
  `POST .../dettaglio-pro/risposte` o la governance A.6.1; il fallimento e' identico prima e
  dopo i Task 1/2 di questo piano (verificato riproducendolo isolato). Non corretto qui (Rule
  scope boundary) — da chiudere in un piano che tocchi davvero quell'endpoint/quel test.

## test_stima_tier.py::TestStimaFreeNonDiventaPro::test_post_risposte_403 fallisce (pre-esistente, non causato dal 09-06)

- **Trovato durante:** stessa verifica del punto precedente.
- **Sintomo:** `assert response.status_code == 403` fallisce, arriva `422`.
- **Causa:** il test posta il payload FLAT pre-09-05 (`{"bagni": 1, "porte": 1,
  "condizionatori": 1}`), ma dal 09-05 (`5dbfdf7`, "contratto API generico") il body atteso e'
  `{"risposte": {...}, "livelli": {...}}` — Pydantic risponde 422 (validazione) prima di
  arrivare al controllo 403 (`require_pro`), che e' cio' che il test vuole verificare. Il test
  non e' mai stato aggiornato al nuovo contratto.
- **Fuori scope:** nessun task del piano 09-06 tocca schema/contratto di quell'endpoint. Non
  corretto qui (Rule scope boundary).
