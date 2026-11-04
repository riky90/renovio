"""Impostazioni comuni a tutta la suite.

`ADMIN_PROMUOVI_SENZA_VERIFICA`: in produzione ADMIN_EMAIL diventa admin solo
con l'email dimostrata (Google o reset password). Molti test creano l'admin
registrandolo con ADMIN_EMAIL: qui lo si consente, come in sviluppo locale.
I test che verificano la regola di produzione lo rimettono a False.

`login_guard`: il blocco per email e' in memoria e condiviso fra i test;
si azzera a ogni test perche' uno non erediti i tentativi falliti dell'altro.

Firma delle stime: decine di test salvano snapshot scritti a mano, senza
passare da `POST /stima`. Per loro la verifica della firma e' sostituita da
un "sempre valida". I test marcati `@pytest.mark.firma_reale` usano la
verifica vera (tests/test_firma_stima.py). Nessun interruttore in produzione:
la sostituzione esiste solo qui.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.services.login_guard import login_guard


def pytest_configure(config):
    config.addinivalue_line("markers", "firma_reale: usa la verifica vera della firma delle stime")


@pytest.fixture(autouse=True)
def _firma_stime_nei_test(request, monkeypatch):
    if request.node.get_closest_marker("firma_reale") is None:
        import app.services.firma_stima as firma_stima

        monkeypatch.setattr(firma_stima, "firma_valida", lambda risultato, firma: True)
    yield


@pytest.fixture(autouse=True)
def _admin_senza_verifica_nei_test(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_PROMUOVI_SENZA_VERIFICA", True)
    login_guard.reset()
    yield
    login_guard.reset()
