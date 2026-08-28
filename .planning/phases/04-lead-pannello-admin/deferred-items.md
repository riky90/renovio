# Deferred Items — Phase 04 (Lead & pannello admin)

## Piano 04-01

- **`tests/test_password_reset.py::TestResetTokenUnit::test_token_manomesso_ritorna_none`** — osservato un singolo fallimento intermittente durante l'esecuzione della suite completa post-Task 2 (`assert 42 is None` — il token manomesso è stato letto come valido). Ri-eseguito isolato: PASS. Ri-eseguita l'intera suite una seconda volta: PASS (114 passed, 4 skipped). File/test completamente estraneo al lavoro di questo piano (manomissione token reset password, non lead). Fuori scope per Rule 1-3 (scope boundary — non causato dalle modifiche di questo piano). Nessuna azione presa; segnalato per eventuale indagine di flakiness in un piano futuro se si ripresenta.

## Piano 04-02 (Package admin + CRUD listini/categoria/voce)

- **`tests/test_health.py::test_health_db_returns_live_count` fails in this
  worktree** (`sqlite3.OperationalError: no such table: listino`). Cause:
  `backend/dev.db` in this worktree checkout is a 0-byte file (migrations
  never run against it here) — pre-existing environment state, not caused
  by any file this plan touches (`test_health.py` is untouched, out of
  04-02's `files_modified` scope). Fix: run `uv run alembic upgrade head`
  (or `python scripts/seed.py`, which calls `Base.metadata.create_all`
  first) against this worktree's `backend/dev.db` before relying on that
  test locally. Does not block 04-02 acceptance criteria (all of which are
  scoped to `test_admin_listini.py`/`test_no_leak_admin.py`, both green).

## Piano 04-04 (Dashboard lead admin + CRUD referenti)

- **`tests/test_health.py::test_health_db_returns_live_count`** — stesso
  fallimento pre-esistente documentato sopra (piano 04-02), riconfermato
  qui: fallisce anche isolato (`uv run pytest tests/test_health.py -x`),
  causa invariata (`backend/dev.db` 0-byte in questo worktree). File
  totalmente estraneo a questo piano (non in `files_modified`). Suite
  completa: 161 passed, 4 skipped, 1 failed (solo questo test). Tutti i
  test di questo piano (`test_admin_lead.py`, `test_admin_referenti.py`)
  e la re-esecuzione di `test_lead.py` sono verdi.

## Piano 04-05 (Upload Excel listino preview/confirm)

- **`tests/test_health.py::test_health_db_returns_live_count`** — stesso
  fallimento pre-esistente segnalato in 04-02, riconfermato in questa
  sessione (fallisce anche in isolamento, `uv run pytest tests/test_health.py`
  da solo). Nessuna relazione con `computo_parsing.py`/
  `listino_upload_service.py`/`upload_listino.py` (file non toccati, out
  of scope). Suite completa: 158 passed, 4 skipped, 1 failed (solo questo
  test pre-esistente).
