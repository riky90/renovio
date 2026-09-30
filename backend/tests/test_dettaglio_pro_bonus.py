"""Dettaglio Pro: bonus calcolati server-side sui totali Pro (10-14, G6)."""

from __future__ import annotations

from decimal import Decimal

from app.models.bonus import BonusFiscale
from tests.test_dettaglio_pro_budget import _crea, _get, _livelli_selezionabili
from tests.test_dettaglio_pro_livelli import (  # noqa: F401  (fixture `client` inclusa)
    STIME_URL,
    _registra_pro,
    _stima_payload,
    client,
)

CHIAVI_BONUS = {
    "bonus",
    "detrazione_min",
    "detrazione_max",
    "rata_annua_min",
    "rata_annua_max",
    "disclaimer",
    "detrazione_lavori_min",
    "detrazione_lavori_max",
    "netto_min",
    "netto_max",
}


class TestBonusPro:
    def test_bonus_presente_e_coerente_col_totale_ivato(self, client):
        c, _ = client
        _registra_pro(c)
        body = _get(c, _crea(c))
        bonus = body["bonus"]
        assert bonus is not None
        assert set(bonus) == CHIAVI_BONUS
        assert Decimal(bonus["detrazione_min"]) > 0
        for lato in ("min", "max"):
            atteso = Decimal(body[f"totale_ivato_{lato}"]) - Decimal(bonus[f"detrazione_lavori_{lato}"])
            assert Decimal(bonus[f"netto_{lato}"]) == max(Decimal(0), atteso)
            assert Decimal(bonus[f"netto_{lato}"]) >= 0

    def test_parita_get_post(self, client):
        c, _ = client
        _registra_pro(c)
        sid = _crea(c)
        primo = _get(c, sid)
        post = c.post(f"{STIME_URL}/{sid}/dettaglio-pro/risposte", json={"risposte": {}}).json()
        assert post["bonus"] == primo["bonus"]

    def test_cambiando_finitura_cambia_la_base(self, client):
        c, sf = client
        _registra_pro(c)
        codici = _livelli_selezionabili(sf)
        alto = _get(c, _crea(c, {k: "alto" for k in codici}))
        medio = _get(c, _crea(c, {k: "medio" for k in codici}))
        assert Decimal(alto["totale_ivato_max"]) > Decimal(medio["totale_ivato_max"])
        assert Decimal(alto["bonus"]["netto_max"]) != Decimal(medio["bonus"]["netto_max"])
        sid = _crea(c, {k: "medio" for k in codici})
        post = c.post(
            f"{STIME_URL}/{sid}/dettaglio-pro/risposte",
            json={"risposte": {}, "livelli": {k: "alto" for k in codici}},
        ).json()
        assert post["bonus"] == alto["bonus"]

    def test_snapshot_senza_arredo_e_destinazione(self, client):
        c, _ = client
        _registra_pro(c)
        payload = _stima_payload()
        assert "arredo" not in payload and "destinazione" not in payload["input"]
        sid = c.post(STIME_URL, json=payload).json()["id"]
        assert _get(c, sid)["bonus"] is not None

    def test_arredo_dello_snapshot_non_riduce_il_netto(self, client):
        c, sf = client
        _registra_pro(c)
        # MOBILI e' spento di default nel seed: lo si accende per vedere l'arredo in base.
        with sf() as s:
            s.get(BonusFiscale, "MOBILI").attivo = True
            s.commit()
        base = _get(c, _crea(c))["bonus"]
        # L'arredo arriva col salvataggio (POST /me/stime), come fa il client (G9).
        payload = _stima_payload()
        payload["arredo"] = {
            "livello_code": "medio",
            "livello_nome": "Medio",
            "ambienti": [{"code": "cucina", "nome": "Cucina", "eur_min": "5000", "eur_max": "8000"}],
            "totale_min": "5000",
            "totale_max": "8000",
            "disclaimer": "Stima indicativa dell'arredo.",
        }
        sid = c.post(STIME_URL, json=payload).json()["id"]
        con = _get(c, sid)["bonus"]
        # la detrazione complessiva puo' crescere (Bonus Mobili), quella sui lavori no
        assert [(b["code"], b["base_min"]) for b in con["bonus"]] != [
            (b["code"], b["base_min"]) for b in base["bonus"]
        ], "l'arredo dello snapshot deve entrare nella base dei bonus"
        assert con["detrazione_lavori_min"] == base["detrazione_lavori_min"]
        assert con["netto_min"] == base["netto_min"]
        mobili = [b for b in con["bonus"] if b["code"] == "MOBILI"]
        assert mobili and Decimal(mobili[0]["base_min"]) == Decimal("5000")
        assert mobili[0]["su_arredo"] is True
        assert all(b["su_arredo"] is False for b in con["bonus"] if b["code"] != "MOBILI")

    def test_nessuna_chiave_vietata(self, client):
        c, _ = client
        _registra_pro(c)
        testo = str(_get(c, _crea(c))["bonus"]).lower()
        for vietato in ("coefficiente", "prezzo_impresa", "effettivo", "moltiplicatore"):
            assert vietato not in testo
