"""Impostazioni comuni a tutta la suite.

`ADMIN_PROMUOVI_SENZA_VERIFICA`: in produzione ADMIN_EMAIL diventa admin solo
con l'email dimostrata (Google o reset password). Molti test creano l'admin
registrandolo con ADMIN_EMAIL: qui lo si consente, come in sviluppo locale.
I test che verificano la regola di produzione lo rimettono a False.

`login_guard`: il blocco per email e' in memoria e condiviso fra i test;
si azzera a ogni test perche' uno non erediti i tentativi falliti dell'altro.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.services.login_guard import login_guard


@pytest.fixture(autouse=True)
def _admin_senza_verifica_nei_test(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_PROMUOVI_SENZA_VERIFICA", True)
    login_guard.reset()
    yield
    login_guard.reset()
