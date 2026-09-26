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
