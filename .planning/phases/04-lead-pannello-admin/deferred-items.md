# Deferred Items — Phase 04 (Lead & pannello admin)

## Piano 04-01

- **`tests/test_password_reset.py::TestResetTokenUnit::test_token_manomesso_ritorna_none`** — osservato un singolo fallimento intermittente durante l'esecuzione della suite completa post-Task 2 (`assert 42 is None` — il token manomesso è stato letto come valido). Ri-eseguito isolato: PASS. Ri-eseguita l'intera suite una seconda volta: PASS (114 passed, 4 skipped). File/test completamente estraneo al lavoro di questo piano (manomissione token reset password, non lead). Fuori scope per Rule 1-3 (scope boundary — non causato dalle modifiche di questo piano). Nessuna azione presa; segnalato per eventuale indagine di flakiness in un piano futuro se si ripresenta.
