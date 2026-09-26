"""Seed idempotency + completeness tests for the Pro detail data (03-02:
`docs/seed-dettaglio-pro.json` -> `scripts.seed.seed_dettaglio_pro`).

Uses an isolated in-memory SQLite DB per test — never touches dev.db, same
fixture pattern as `test_seed.py`.
"""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models.catalogo import Categoria, TipoRistrutturazione
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Sottocategoria, Voce
from scripts.genera_excel_taratura import leggi_decisioni
import openpyxl
from pathlib import Path
from scripts.seed import load_dettaglio_pro_data, load_seed_data, seed
from tests.session_factory import sessione_di_test


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
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
    assert categoria_codes == {"A-EDILE", "B-FINITURE", "C-SERRAMENTI", "D-PRODOTTI", "E-ARREDO"}

    # Il dettaglio Pro copre le categorie di LAVORO. `E-ARREDO` non ha ancora
    # voci: nel Free e' un forfait per ambiente (`forfait_arredo`), e le voci
    # vere arrivano con l'import Excel (fase 08). Finche' non ci sono, il
    # motore Pro scarta la categoria invece di mostrarne una vuota a 0 EUR.
    categorie_di_lavoro = {
        c for (c,) in session.query(Categoria.code).filter(Categoria.nel_totale_lavori.is_(True))
    }
    sotto_categoria_codes = {c for (c,) in session.query(Sottocategoria.categoria_code).distinct().all()}
    assert sotto_categoria_codes == categorie_di_lavoro

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


# --- Task 2 (09-06-PLAN.md): seed create-if-missing (D-41/CFG-04) ----------


def test_seed_ripetuto_non_riscrive_un_coefficiente_curato(session):
    """D-41/CFG-04: il seed CREA la riga se manca, non la possiede piu' — una
    riga gia' presente (curata da una migrazione o dal pannello admin) non
    deve tornare al valore di bozza a ogni riavvio del container. La bozza e'
    cambiata per CFG-04 e cambiera' ancora con la taratura vera di Riccardo:
    il valore atteso e' quello scritto a mano nel test, non un numero cablato
    dal JSON."""
    data = load_seed_data()
    seed(session, data)

    riga = (
        session.query(CoefficienteQuantitaVoce)
        .filter(CoefficienteQuantitaVoce.coefficiente_qta_per_mq.isnot(None))
        .first()
    )
    assert riga is not None
    valore_curato = Decimal("99.9999")
    riga.coefficiente_qta_per_mq = valore_curato
    session.commit()
    riga_id = riga.id

    seed(session, data)  # rilancio del seed, come a ogni boot del container

    session.expire_all()
    riga_dopo = session.get(CoefficienteQuantitaVoce, riga_id)
    assert riga_dopo.coefficiente_qta_per_mq == valore_curato


def test_db_nuovo_ha_i_valori_del_seed_json(session):
    """Un DB appena seminato ha, per ogni (voce, tipo) di un campione del
    seed JSON, esattamente il valore del JSON — confronto riga per riga, mai
    un numero cablato nel test."""
    data = load_seed_data()
    seed(session, data)

    dettaglio = load_dettaglio_pro_data()
    verificate = 0
    for sotto_data in dettaglio["sottocategorie"][:3]:
        query_sotto = session.query(Sottocategoria).filter_by(categoria_code=sotto_data["categoria_code"])
        codice_sotto = sotto_data.get("codice")
        sotto = (
            query_sotto.filter_by(codice=codice_sotto).one()
            if codice_sotto is not None
            else query_sotto.filter_by(codice=None, nome=sotto_data["nome"]).one()
        )
        for voce_data in sotto_data["voci"][:5]:
            codice_voce = voce_data.get("codice")
            query_voce = session.query(Voce).filter_by(sottocategoria_id=sotto.id)
            voce = (
                query_voce.filter_by(codice=codice_voce).one()
                if codice_voce is not None
                else query_voce.filter_by(codice=None, descrizione=voce_data["descrizione"]).one()
            )
            for tipo_code, coeff_data in voce_data.get("coefficienti", {}).items():
                riga = (
                    session.query(CoefficienteQuantitaVoce)
                    .filter_by(voce_id=voce.id, tipo_code=tipo_code)
                    .one()
                )
                if coeff_data.get("coefficiente_qta_per_mq") is not None:
                    assert riga.coefficiente_qta_per_mq == Decimal(str(coeff_data["coefficiente_qta_per_mq"]))
                if coeff_data.get("default_conteggio") is not None:
                    assert riga.default_conteggio == coeff_data["default_conteggio"]
                verificate += 1
    assert verificate > 0


def test_seed_json_coerente_con_le_decisioni_del_file_di_taratura():
    """Il seed-dettaglio-pro.json deve corrispondere, per ogni `CoeffDeciso`
    del file di decisioni reale, al valore che `leggi_decisioni` ha estratto
    — resta vero dopo ogni riapplicazione di `scripts/applica_taratura.py`
    (piano 09-06). Risolve i `voce_id` del file contro `backend/dev.db` (la
    stessa fonte usata quando lo script e' stato lanciato), mai un id
    cablato a mano. Se `dev.db` non e' presente in questo ambiente, il test
    e' saltato (stesso pattern degli skip GTK3/WeasyPrint)."""
    backend_dir = Path(__file__).resolve().parents[1]
    dev_db_path = backend_dir / "dev.db"
    if not dev_db_path.exists():
        pytest.skip("backend/dev.db non presente in questo ambiente")

    from sqlalchemy import create_engine as _create_engine

    from scripts.applica_taratura import risolvi_chiave_naturale

    file_taratura = backend_dir.parent / "docs" / "taratura" / "09-taratura-pro-compilato.xlsx"
    if not file_taratura.exists():
        pytest.skip("file di taratura non presente in questo ambiente")

    wb = openpyxl.load_workbook(file_taratura, data_only=True)
    decisioni = leggi_decisioni(wb)

    seed_dettaglio = load_dettaglio_pro_data()
    indice: dict[tuple[str, str, str], dict] = {}
    for sotto in seed_dettaglio["sottocategorie"]:
        chiave_sotto = sotto.get("codice") if sotto.get("codice") is not None else sotto["nome"]
        for voce in sotto["voci"]:
            chiave_voce = voce.get("codice") if voce.get("codice") is not None else voce["descrizione"]
            indice[(sotto["categoria_code"], chiave_sotto, chiave_voce)] = voce

    engine = _create_engine(f"sqlite:///{dev_db_path}")
    session_locale = sessione_di_test(engine)
    verificate = 0
    try:
        with session_locale() as db_session:
            for riga in decisioni.coefficienti:
                chiave_dict = risolvi_chiave_naturale(db_session, riga.voce_id)
                if chiave_dict is None:
                    continue
                chiave = (chiave_dict["categoria_code"], chiave_dict["sottocategoria"], chiave_dict["voce"])
                voce_entry = indice.get(chiave)
                if voce_entry is None:
                    continue
                blocco = voce_entry.get("coefficienti", {}).get(riga.tipo_code, {})
                if riga.coefficiente_qta_per_mq is not None:
                    assert blocco.get("coefficiente_qta_per_mq") is not None, chiave
                    assert Decimal(str(blocco["coefficiente_qta_per_mq"])) == riga.coefficiente_qta_per_mq, chiave
                elif riga.default_conteggio is not None:
                    assert blocco.get("default_conteggio") == riga.default_conteggio, chiave
                verificate += 1
    finally:
        engine.dispose()
    assert verificate > 0
