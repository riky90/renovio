"""Seed idempotency + completeness tests for the Pro detail data (03-02:
`docs/seed-dettaglio-pro.json` -> `scripts.seed.seed_dettaglio_pro`).

Uses an isolated in-memory SQLite DB per test — never touches dev.db, same
fixture pattern as `test_seed.py`.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.models.catalogo import Categoria, TipoRistrutturazione
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Sottocategoria, Voce
from scripts.seed import load_seed_data, seed


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)
    with testing_session_local() as s:
        yield s


def _counts(session: Session) -> dict[str, int]:
    return {
        "sottocategoria": session.query(Sottocategoria).count(),
        "voce": session.query(Voce).count(),
        "coefficiente_qta_voce": session.query(CoefficienteQuantitaVoce).count(),
    }


def test_seed_dettaglio_pro_covers_all_categories(session):
    data = load_seed_data()
    seed(session, data)

    categoria_codes = {c for (c,) in session.query(Categoria.code).all()}
    assert categoria_codes == {"A-EDILE", "B-FINITURE", "C-SERRAMENTI", "D-PRODOTTI"}

    sotto_categoria_codes = {c for (c,) in session.query(Sottocategoria.categoria_code).distinct().all()}
    assert sotto_categoria_codes == categoria_codes

    gerarchiche = session.query(Sottocategoria).filter_by(categoria_code="A-EDILE", famiglia="gerarchica").all()
    assert len(gerarchiche) >= 11

    catalogo = session.query(Sottocategoria).filter(Sottocategoria.categoria_code != "A-EDILE").all()
    assert all(s.famiglia == "catalogo" for s in catalogo)
    assert len(catalogo) > 0

    counts = _counts(session)
    assert counts["sottocategoria"] > 0
    assert counts["voce"] > 0
    assert counts["coefficiente_qta_voce"] > 0


def test_seed_dettaglio_pro_is_idempotent(session):
    data = load_seed_data()
    seed(session, data)
    before = _counts(session)

    seed(session, data)  # re-run must not duplicate any row
    after = _counts(session)

    assert before == after


def test_ogni_voce_ha_coefficiente_per_ciascun_tipo(session):
    data = load_seed_data()
    seed(session, data)

    tipo_codes = [c for (c,) in session.query(TipoRistrutturazione.code).all()]
    assert len(tipo_codes) == 3

    voci = session.query(Voce).all()
    assert len(voci) > 0
    for voce in voci:
        coeff_tipi = {
            c.tipo_code
            for c in session.query(CoefficienteQuantitaVoce).filter_by(voce_id=voce.id).all()
        }
        assert coeff_tipi == set(tipo_codes), f"voce {voce.id} ({voce.descrizione!r}) manca coefficienti per tutti i tipi"


def test_nessun_dato_impresa_nel_dettaglio(session):
    """Nessuna colonna prezzo/coefficiente impresa esiste sul modello Voce (D-10)."""
    voce_columns = {c.name for c in Voce.__table__.columns}
    assert "coefficiente_impresa" not in voce_columns
    assert "prezzo_impresa" not in voce_columns
