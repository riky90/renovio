"""10-05: budget_eur salvato in colonna, PATCH protetto, snapshot invariato."""

from __future__ import annotations

import copy

import pytest

import app.db as db_module
from app.models.stima_salvata import StimaSalvata
from tests.test_stime_salvate import (  # noqa: F401  (fixture `client` inclusa)
    STIME_URL,
    _registra,
    _stima_payload,
    client,
)

CONFRONTO = {
    "livello_code": "medio",
    "livello_nome": "Medio",
    "totale_min": "28000.00",
    "totale_max": "40000.00",
}


def _salva(client, **extra) -> int:
    payload = _stima_payload()
    payload.update(extra)
    response = client.post(STIME_URL, json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def _riga(stima_id: int) -> StimaSalvata:
    with db_module.SessionLocal() as s:
        row = s.get(StimaSalvata, stima_id)
        s.expunge(row)
        return row


def test_post_salva_budget_in_colonna_e_non_nello_snapshot(client):
    _registra(client)
    stima_id = _salva(
        client,
        budget_eur=40000,
        confronto_finiture=CONFRONTO,
        finiture_al_minimo=False,
    )
    row = _riga(stima_id)
    assert row.budget_eur == 40000
    assert "budget_eur" not in row.risultato_json
    assert row.risultato_json["confronto_finiture"]["livello_code"] == "medio"
    assert "finiture_al_minimo" in row.risultato_json

    body = client.get(f"{STIME_URL}/{stima_id}").json()
    assert body["budget_eur"] == 40000
    assert body["confronto_finiture"] == CONFRONTO
    assert body["finiture_al_minimo"] is False


def test_patch_aggiorna_solo_la_colonna(client):
    _registra(client)
    stima_id = _salva(client, budget_eur=40000)
    prima = copy.deepcopy(_riga(stima_id).risultato_json)

    response = client.patch(f"{STIME_URL}/{stima_id}/budget", json={"budget_eur": 55000})

    assert response.status_code == 200
    assert response.json() == {"budget_eur": 55000}
    assert client.get(f"{STIME_URL}/{stima_id}").json()["budget_eur"] == 55000
    dopo = _riga(stima_id).risultato_json
    assert dopo == prima
    assert dopo["totale"] == prima["totale"]
    assert dopo["categorie"] == prima["categorie"]


def test_patch_null_azzera_il_budget(client):
    _registra(client)
    stima_id = _salva(client, budget_eur=40000)
    response = client.patch(f"{STIME_URL}/{stima_id}/budget", json={"budget_eur": None})
    assert response.status_code == 200
    assert client.get(f"{STIME_URL}/{stima_id}").json()["budget_eur"] is None


@pytest.mark.parametrize("valore", [0, -5, 1_000_000_000])
def test_patch_valida_il_budget(client, valore):
    _registra(client)
    stima_id = _salva(client)
    response = client.patch(f"{STIME_URL}/{stima_id}/budget", json={"budget_eur": valore})
    assert response.status_code == 422


def test_post_rifiuta_budget_fuori_range(client):
    _registra(client)
    payload = _stima_payload()
    payload["budget_eur"] = 0
    assert client.post(STIME_URL, json=payload).status_code == 422


def test_patch_stima_altrui_o_inesistente_404(client):
    _registra(client)
    stima_id = _salva(client)
    client.post("/api/v1/auth/logout")
    _registra(client, email="utente.b@example.com", nome="Utente B")

    altrui = client.patch(f"{STIME_URL}/{stima_id}/budget", json={"budget_eur": 1000})
    inesistente = client.patch(f"{STIME_URL}/99999/budget", json={"budget_eur": 1000})

    assert altrui.status_code == 404
    assert inesistente.status_code == 404
    assert _riga(stima_id).budget_eur is None


def test_patch_senza_sessione_401(client):
    response = client.patch(f"{STIME_URL}/1/budget", json={"budget_eur": 1000})
    assert response.status_code == 401


@pytest.mark.parametrize("tier", ["free", "pro"])
def test_patch_vale_per_free_e_pro(client, tier):
    _registra(client)
    stima_id = _salva(client)
    with db_module.SessionLocal() as s:
        s.get(StimaSalvata, stima_id).tier = tier
        s.commit()
    response = client.patch(f"{STIME_URL}/{stima_id}/budget", json={"budget_eur": 30000})
    assert response.status_code == 200


def test_snapshot_pre_fase_si_apre_senza_errori(client):
    _registra(client)
    stima_id = _salva(client)
    with db_module.SessionLocal() as s:
        row = s.get(StimaSalvata, stima_id)
        snap = dict(row.risultato_json)
        snap.pop("confronto_finiture", None)
        snap.pop("finiture_al_minimo", None)
        snap.pop("budget_eur", None)
        row.risultato_json = snap
        row.budget_eur = None
        s.commit()

    response = client.get(f"{STIME_URL}/{stima_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["confronto_finiture"] is None
    assert body["finiture_al_minimo"] is False
    assert body["budget_eur"] is None
