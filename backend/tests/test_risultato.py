"""Test delle funzioni pure di presentazione (mirror di frontend/src/lib/risultato.ts)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.risultato import (
    incidenza_eur_mq,
    peso_categoria,
    riepilogo_iva,
    scala_barra,
    somma_medi,
)


class TestScalaBarra:
    def test_tetto_e_percentuali(self):
        s = scala_barra(50000, 55000)
        assert s.tetto == 66000
        assert s.left_pct == pytest.approx(75.76, abs=0.01)
        assert s.right_pct == pytest.approx(83.33, abs=0.01)
        assert s.budget_pct is None

    def test_larghezza_cresce_con_incertezza(self):
        stretta = scala_barra(90000, 110000)
        larga = scala_barra(80000, 120000)
        assert larga.width_pct - stretta.width_pct >= 8

    def test_larghezza_minima_4_punti(self):
        s = scala_barra(99000, 100000)
        assert s.width_pct == pytest.approx(4)
        centro = (s.left_pct + s.right_pct) / 2
        assert centro == pytest.approx((99000 + 100000) / 2 / s.tetto * 100)

    def test_passo_grande_sopra_soglia(self):
        assert scala_barra(80000, 100000).tetto == 120000

    def test_budget_estende_tetto(self):
        s = scala_barra(40000, 50000, budget=150000)
        assert s.tetto == 150000
        assert s.budget_pct == pytest.approx(100)

    @pytest.mark.parametrize("budget", [None, 0])
    def test_senza_budget(self, budget):
        assert scala_barra(40000, 50000, budget=budget).budget_pct is None


class TestIncidenza:
    def test_eur_mq(self):
        assert incidenza_eur_mq(26350, 32300, 85) == (310, 380)

    def test_mq_zero(self):
        assert incidenza_eur_mq(26350, 32300, 0) is None

    def test_accetta_stringhe(self):
        assert incidenza_eur_mq("26350.00", "32300.00", 85) == (310, 380)


class TestPeso:
    def test_meno_di_uno(self):
        p = peso_categoria(Decimal("400"), Decimal("600"), Decimal("100000"))
        assert p.etichetta == "<1%"
        assert p.fill_pct == 2

    def test_normale(self):
        p = peso_categoria(Decimal("34000"), Decimal("34800"), Decimal("100000"))
        assert p.etichetta == "34%"
        assert p.fill_pct == pytest.approx(34.4)

    def test_somma_zero(self):
        p = peso_categoria(1, 2, Decimal("0"))
        assert (p.etichetta, p.fill_pct) == ("0%", 0)

    def test_somma_medi(self):
        cats = [
            {"totale_min": "100.00", "totale_max": "200.00"},
            {"totale_min": "300.00", "totale_max": "500.00"},
        ]
        assert somma_medi(cats) == Decimal("550")


def _cat(imp_min, imp_max, iva_pct, iva_min, iva_max):
    return {
        "imponibile_min": imp_min,
        "imponibile_max": imp_max,
        "iva_pct": iva_pct,
        "iva_min": iva_min,
        "iva_max": iva_max,
        "totale_min": str(Decimal(imp_min) + Decimal(iva_min)),
        "totale_max": str(Decimal(imp_max) + Decimal(iva_max)),
    }


class TestRiepilogoIva:
    def _dati(self):
        cats = [
            _cat("10000.00", "15000.00", "0.10", "1000.00", "1500.00"),
            _cat("8000.00", "12000.00", "0.22", "1760.00", "2640.00"),
        ]
        extra = [{"code": "cse", "nome": "CSE", "importo": "1500.00", "iva_pct": "0.22"}]
        totale = {
            "imponibile_min": "19500.00",
            "imponibile_max": "28500.00",
            "iva_min": "3090.00",
            "iva_max": "4470.00",
            "totale_min": "22590.00",
            "totale_max": "32970.00",
        }
        return cats, extra, totale

    def test_righe_ordinate_e_riconciliate(self):
        cats, extra, totale = self._dati()
        r = riepilogo_iva(cats, extra, totale)
        assert [x.iva_pct for x in r.righe_iva] == [Decimal("0.10"), Decimal("0.22")]
        assert [x.etichetta for x in r.righe_iva] == ["IVA 10%", "IVA 22%"]
        assert r.righe_iva[0].min == Decimal("1000.00")
        assert r.righe_iva[1].min == Decimal("3090.00") - Decimal("1000.00")
        assert sum(x.max for x in r.righe_iva) == Decimal("4470.00")

    def test_imponibile_lavori_solo_categorie(self):
        cats, extra, totale = self._dati()
        r = riepilogo_iva(cats, extra, totale)
        assert r.imponibile_lavori_min == Decimal("18000.00")
        assert r.imponibile_lavori_max == Decimal("27000.00")
        assert r.extra_totale == Decimal("1500.00")
        assert r.totale_min == Decimal("22590.00")

    def test_una_sola_aliquota(self):
        cats = [_cat("10000.00", "15000.00", "0.10", "1000.00", "1500.00")]
        totale = {
            "imponibile_min": "10000.00",
            "imponibile_max": "15000.00",
            "iva_min": "1000.00",
            "iva_max": "1500.00",
            "totale_min": "11000.00",
            "totale_max": "16500.00",
        }
        r = riepilogo_iva(cats, [], totale)
        assert len(r.righe_iva) == 1
        assert r.extra_totale == Decimal("0")


class TestLivelloInferiore:
    OPZ = [("alto", 3, False), ("base", 1, False), ("medio", 2, True)]

    def test_scende_di_un_gradino(self):
        from app.services.risultato import livello_inferiore

        assert livello_inferiore(self.OPZ, "alto") == "medio"
        assert livello_inferiore(self.OPZ, "medio") == "base"

    def test_al_minimo_e_sconosciuto(self):
        from app.services.risultato import livello_inferiore

        assert livello_inferiore(self.OPZ, "base") is None
        assert livello_inferiore(self.OPZ, "boh") is None

    def test_scelto_none_parte_dal_default(self):
        from app.services.risultato import livello_corrente, livello_inferiore

        assert livello_inferiore(self.OPZ, None) == "base"
        assert livello_corrente(self.OPZ, None) == "medio"
        assert livello_corrente(self.OPZ, "alto") == "alto"
        assert livello_corrente(self.OPZ, "boh") == "medio"
