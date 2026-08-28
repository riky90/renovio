# Deferred Items — Phase 04 (lead-pannello-admin)

## From 04-02 (Package admin + CRUD listini/categoria/voce)

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
