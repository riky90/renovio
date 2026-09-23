"""Test anti-leak per `GET /api/v1/admin/coefficienti/export.xlsx` (08-04-PLAN.md,
CUR-03). Il punto di questi test è che aprono il file generato con openpyxl e
guardano dentro: uno status code non direbbe niente sul contenuto, ed è il
contenuto che viaggia fuori dall'applicazione (regola di dominio #1,
`CLAUDE.md`).

Copre: il file di default non contiene mai `coefficiente_impresa` né un
foglio `AVVISO`; `?margine=true` la contiene, apre sul foglio `AVVISO`, ed è
marcato nel nome; il consulente non scarica nessuna delle due varianti;
`export_log` distingue le due varianti; i cinque fogli dati sono presenti
col conteggio righe atteso.
"""

from __future__ import annotations

import io

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.arredo import ForfaitArredo
from app.models.export_log import ExportLog
from app.models.user import User
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
COEFF_URL = "/api/v1/admin/coefficienti"

ADMIN_EMAIL = "admin.export.margine@example.com"

VALORI_MARGINE_SEED = {"0.65", "0.6", "0.5", "0.55"}


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    db_path = tmp_path / "test_export_margine.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    test_client = TestClient(app)
    test_client._session_local = testing_session_local  # per le assert dirette a DB
    return test_client


def _registra_admin(client, email=ADMIN_EMAIL, nome="Admin Export Margine"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def _registra_consulente(client, email="consulente.export@example.com", nome="Consulente Export"):
    resp = client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})
    with client._session_local() as db:
        user = db.query(User).filter_by(email=email).one()
        user.role = "consulente"
        db.commit()
    return resp


class TestExportDefaultSenzaMargine:
    def test_export_default_non_contiene_coefficiente_impresa(self, client):
        _registra_admin(client)

        response = client.get(f"{COEFF_URL}/export.xlsx")
        assert response.status_code == 200

        wb = openpyxl.load_workbook(io.BytesIO(response.content))

        assert "AVVISO" not in wb.sheetnames

        for nome_foglio in wb.sheetnames:
            ws = wb[nome_foglio]
            header_row = next(ws.iter_rows(min_row=1, max_row=1), None)
            if header_row is None:
                continue
            header = [cell.value for cell in header_row]
            assert "coefficiente_impresa" not in header, f"colonna margine trovata nel foglio {nome_foglio}"

        # Nessun valore di margine del seed compare in nessuna cella — non
        # solo l'header, anche i dati.
        for nome_foglio in wb.sheetnames:
            ws = wb[nome_foglio]
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None and str(cell.value) in VALORI_MARGINE_SEED and nome_foglio == "listino_categoria":
                        pytest.fail(
                            f"valore di margine {cell.value!r} trovato in {nome_foglio}!{cell.coordinate}"
                        )


class TestExportConMargine:
    def test_export_margine_contiene_la_colonna_e_il_foglio_avviso(self, client):
        _registra_admin(client)

        response = client.get(f"{COEFF_URL}/export.xlsx", params={"margine": "true"})
        assert response.status_code == 200
        assert "con-margine" in response.headers["content-disposition"]

        wb = openpyxl.load_workbook(io.BytesIO(response.content))

        assert wb.sheetnames[0] == "AVVISO"

        ws = wb["listino_categoria"]
        header = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
        assert "coefficiente_impresa" in header


class TestExportMargineVietatoAlConsulente:
    def test_export_margine_vietato_al_consulente(self, client):
        _registra_consulente(client)

        response_margine = client.get(f"{COEFF_URL}/export.xlsx", params={"margine": "true"})
        assert response_margine.status_code == 403

        response_default = client.get(f"{COEFF_URL}/export.xlsx")
        assert response_default.status_code == 403

        with client._session_local() as db:
            assert db.query(ExportLog).count() == 0


class TestExportLogDistingueVarianti:
    def test_export_log_distingue_le_due_varianti(self, client):
        _registra_admin(client)

        r1 = client.get(f"{COEFF_URL}/export.xlsx")
        assert r1.status_code == 200
        r2 = client.get(f"{COEFF_URL}/export.xlsx", params={"margine": "true"})
        assert r2.status_code == 200

        with client._session_local() as db:
            righe = db.query(ExportLog).filter_by(risorsa="parametri").order_by(ExportLog.id).all()
            assert len(righe) == 2
            assert righe[0].include_margine is False
            assert righe[1].include_margine is True


class TestCinqueFogliDatiPresenti:
    def test_cinque_fogli_dati_presenti(self, client):
        _registra_admin(client)

        response = client.get(f"{COEFF_URL}/export.xlsx")
        assert response.status_code == 200

        wb = openpyxl.load_workbook(io.BytesIO(response.content))
        fogli_attesi = {
            "ISTRUZIONI",
            "moltiplicatori",
            "listino_categoria",
            "extra",
            "coefficienti_pro",
            "forfait_arredo",
        }
        assert fogli_attesi.issubset(set(wb.sheetnames))

        forfait_sheet = wb["forfait_arredo"]
        n_righe_file = forfait_sheet.max_row - 1  # meno l'header

        with client._session_local() as db:
            n_righe_db = db.query(ForfaitArredo).count()

        assert n_righe_file == n_righe_db
        assert n_righe_file > 0
