"""EstimationService regression tests: pin the plausibility oracles from
docs/seed-listino-reggio-emilia.md and the range/reconciliation rule
(binding, 01-02-PLAN.md <interfaces> / 01-RESEARCH.md Pitfall 4).

Primary oracle (pinned exactly): 85 mq, tipo=totale -> 47985..70575.
"""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.services.city_resolver import resolve_listino
from app.services.estimation import EstimationService
from scripts.seed import load_seed_data, seed


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        yield s


def test_primary_oracle_85mq_totale(session):
    listino, fallback = resolve_listino(session, "Reggio Emilia")
    assert fallback is False

    result = EstimationService.compute(session, listino, mq=85, tipo="totale")

    assert result.totale_min == Decimal("47985")
    assert result.totale_max == Decimal("70575")


@pytest.mark.parametrize(
    "mq,tipo,expected_min,expected_max",
    [
        (60, "totale", Decimal("34697"), Decimal("50643")),
        (110, "totale", Decimal("61273"), Decimal("90507")),
    ],
)
def test_secondary_oracles_within_1_euro(session, mq, tipo, expected_min, expected_max):
    listino, _ = resolve_listino(session, "Reggio Emilia")
    result = EstimationService.compute(session, listino, mq=mq, tipo=tipo)

    assert abs(result.totale_min - expected_min) <= 1
    assert abs(result.totale_max - expected_max) <= 1


def test_reconciliation_cards_plus_extras_equals_total(session):
    listino, _ = resolve_listino(session, "Reggio Emilia")
    result = EstimationService.compute(session, listino, mq=85, tipo="totale")

    cards_min = sum(c.totale_min for c in result.categorie)
    cards_max = sum(c.totale_max for c in result.categorie)
    extras_total = sum(e.totale for e in result.extra)

    assert abs((cards_min + extras_total) - result.totale_min) <= 1
    assert abs((cards_max + extras_total) - result.totale_max) <= 1


def test_per_category_iva_rates(session):
    listino, _ = resolve_listino(session, "Reggio Emilia")
    result = EstimationService.compute(session, listino, mq=85, tipo="totale")

    iva_by_code = {c.code: c.iva_pct for c in result.categorie}
    assert iva_by_code["A-EDILE"] == Decimal("0.100")
    assert iva_by_code["D-PRODOTTI"] == Decimal("0.100")
    assert iva_by_code["B-FINITURE"] == Decimal("0.220")
    assert iva_by_code["C-SERRAMENTI"] == Decimal("0.220")


def test_fixed_extras_not_scaled_by_range(session):
    listino, _ = resolve_listino(session, "Reggio Emilia")
    result = EstimationService.compute(session, listino, mq=85, tipo="totale")

    extras_total = sum(e.totale for e in result.extra)
    assert extras_total == Decimal("2806")  # (800+1500) * 1.22, gross, fixed

    cards_min = sum(c.totale_min for c in result.categorie)
    cards_max = sum(c.totale_max for c in result.categorie)
    assert (cards_min + extras_total) == result.totale_min
    assert (cards_max + extras_total) == result.totale_max


def test_range_always_present_even_for_low_multiplier(session):
    listino, _ = resolve_listino(session, "Reggio Emilia")
    # Serramenti multiplier is 0.10 in "leggera" — still must return a valid,
    # non-negative range (D-05), never NaN/None.
    result = EstimationService.compute(session, listino, mq=60, tipo="leggera")

    serramenti = next(c for c in result.categorie if c.code == "C-SERRAMENTI")
    assert serramenti.totale_min >= 0
    assert serramenti.totale_max >= 0
    assert serramenti.totale_min <= serramenti.totale_max


def test_no_leaked_coefficients_in_result(session):
    listino, _ = resolve_listino(session, "Reggio Emilia")
    result = EstimationService.compute(session, listino, mq=85, tipo="totale")

    result_repr = repr(result)
    assert "coefficiente_impresa" not in result_repr
    assert "0.65" not in result_repr
    assert "0.55" not in result_repr


def test_city_resolver_re_aliases_and_fallback(session):
    listino_re, fallback_re = resolve_listino(session, "reggio emilia")
    assert fallback_re is False

    listino_re2, fallback_re2 = resolve_listino(session, "Reggio nell'Emilia")
    assert fallback_re2 is False
    assert listino_re2.id == listino_re.id

    listino_modena, fallback_modena = resolve_listino(session, "Modena")
    assert fallback_modena is True
    assert listino_modena.id == listino_re.id
