"""Dettaglio Pro: totale IVA inclusa, riepilogo, lettura per categoria, confronto
finiture e budget (10-06). Tutto calcolato server-side da `_compute_dettaglio`."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.models.catalogo import Categoria, Extra

from tests.test_dettaglio_pro_livelli import (  # noqa: F401  (fixture `client` inclusa)
    STIME_URL,
    _registra_pro,
    _stima_payload,
    client,
)


def _eur(v: Decimal) -> Decimal:
    return v.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _crea(c, livelli: dict | None = None, budget: int | None = None) -> int:
    payload = _stima_payload({"livelli": livelli} if livelli else None)
    if budget is not None:
        payload["budget_eur"] = budget
    return c.post(STIME_URL, json=payload).json()["id"]


def _get(c, stima_id: int) -> dict:
    r = c.get(f"{STIME_URL}/{stima_id}/dettaglio-pro")
    assert r.status_code == 200
    return r.json()


def _livelli_selezionabili(session_factory) -> list[str]:
    with session_factory() as s:
        return [
            c.code
            for c in s.query(Categoria).filter(
                Categoria.livello_selezionabile.is_(True), Categoria.nel_totale_lavori.is_(True)
            )
        ]


class TestTotaleIvato:
    def test_totale_ivato_ricalcolato_dal_db(self, client):
        c, sf = client
        _registra_pro(c)
        body = _get(c, _crea(c))
        with sf() as s:
            cats = {x.code: x for x in s.query(Categoria).filter(Categoria.nel_totale_lavori.is_(True))}
            extra = s.query(Extra).filter(Extra.attivo.is_(True)).all()
        atteso_min = Decimal(0)
        atteso_max = Decimal(0)
        for cat in body["categorie"]:
            if cat["code"] in cats:
                aliq = cats[cat["code"]].iva_pct
                mn, mx = Decimal(cat["totale_min"]), Decimal(cat["totale_max"])
                atteso_min += mn + _eur(mn * aliq)
                atteso_max += mx + _eur(mx * aliq)
        lordi = sum((_eur(e.importo * (1 + e.iva_pct)) for e in extra), Decimal(0))
        assert Decimal(body["totale_ivato_min"]) == atteso_min + lordi
        assert Decimal(body["totale_ivato_max"]) == atteso_max + lordi
        assert Decimal(body["totale_ivato_min"]) > Decimal(body["totale_min"])
        assert Decimal(body["totale_ivato_max"]) > Decimal(body["totale_max"])

    def test_riepilogo_coerente(self, client):
        c, _ = client
        _registra_pro(c)
        body = _get(c, _crea(c))
        r = body["riepilogo_iva"]
        assert r["totale_min"] == body["totale_ivato_min"]
        assert r["totale_max"] == body["totale_ivato_max"]
        iva_min = sum(Decimal(x["min"]) for x in r["righe_iva"])
        assert Decimal(r["totale_min"]) == (
            Decimal(r["imponibile_lavori_min"]) + iva_min + Decimal(r["extra_totale"])
        )
        assert len({x["iva_pct"] for x in r["righe_iva"]}) == len(r["righe_iva"])

    def test_lettura_categorie_solo_nel_totale_lavori(self, client):
        c, sf = client
        _registra_pro(c)
        body = _get(c, _crea(c))
        with sf() as s:
            fuori = {x.code for x in s.query(Categoria).filter(Categoria.nel_totale_lavori.is_(False))}
        codici = {x["code"] for x in body["lettura_categorie"]}
        assert codici
        assert not codici & fuori
        assert not {x["code"] for x in body["riepilogo_iva"]["extra"]} & fuori
        for voce in body["lettura_categorie"]:
            assert voce["eur_mq_min"] is not None
            assert voce["peso_etichetta"]


class TestBudgetEParita:
    def test_budget_dalla_colonna(self, client):
        c, _ = client
        _registra_pro(c)
        assert _get(c, _crea(c))["budget_eur"] is None
        assert _get(c, _crea(c, budget=40000))["budget_eur"] == 40000

    def test_get_post_stessi_campi_e_patch_invariante(self, client):
        c, _ = client
        _registra_pro(c)
        sid = _crea(c, budget=30000)
        primo = _get(c, sid)
        assert _get(c, sid) == primo
        post = c.post(f"{STIME_URL}/{sid}/dettaglio-pro/risposte", json={"risposte": {}}).json()
        for k in ("totale_ivato_min", "totale_ivato_max", "riepilogo_iva", "lettura_categorie", "confronto_finiture", "finiture_al_minimo"):
            assert post[k] == primo[k]

        r = c.patch(f"{STIME_URL}/{sid}/budget", json={"budget_eur": 40000})
        assert r.status_code == 200
        dopo = _get(c, sid)
        assert dopo["budget_eur"] == 40000
        for k in ("totale_min", "totale_max", "totale_ivato_min", "totale_ivato_max", "riepilogo_iva", "lettura_categorie", "confronto_finiture"):
            assert dopo[k] == primo[k]


class TestConfrontoPro:
    def test_ricalcolo_vero_un_gradino_sotto(self, client):
        c, sf = client
        _registra_pro(c)
        codici = _livelli_selezionabili(sf)
        alto = _get(c, _crea(c, {k: "alto" for k in codici}))
        medio = _get(c, _crea(c, {k: "medio" for k in codici}))
        conf = alto["confronto_finiture"]
        assert conf is not None
        assert conf["livello_code"] == "medio"
        assert Decimal(conf["totale_max"]) < Decimal(alto["totale_ivato_max"])
        # Ricalcolo vero, non proporzione: coincide con la stima a livelli "medio".
        assert Decimal(conf["totale_min"]) == Decimal(medio["totale_ivato_min"])
        assert Decimal(conf["totale_max"]) == Decimal(medio["totale_ivato_max"])
        assert alto["finiture_al_minimo"] is False

    def test_confronto_assente_se_il_ricalcolo_non_abbassa(self, client):
        """Con i dati attuali "base" costa piu' di "medio": nessun confronto."""
        c, sf = client
        _registra_pro(c)
        medio = _get(c, _crea(c, {k: "medio" for k in _livelli_selezionabili(sf)}))
        assert medio["confronto_finiture"] is None
        assert medio["finiture_al_minimo"] is False

    def test_livelli_misti_scende_la_piu_alta(self, client):
        c, sf = client
        _registra_pro(c)
        codici = _livelli_selezionabili(sf)
        assert len(codici) >= 2
        livelli = {k: "base" for k in codici}
        livelli[codici[0]] = "alto"
        body = _get(c, _crea(c, livelli))
        conf = body["confronto_finiture"]
        assert conf is not None
        assert conf["livello_code"] == "medio"
        assert Decimal(conf["totale_max"]) < Decimal(body["totale_ivato_max"])

    def test_tutti_base_al_minimo(self, client):
        c, sf = client
        _registra_pro(c)
        body = _get(c, _crea(c, {k: "base" for k in _livelli_selezionabili(sf)}))
        assert body["confronto_finiture"] is None
        assert body["finiture_al_minimo"] is True
