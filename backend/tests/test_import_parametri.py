"""Test che contano per `/admin/import-excel/parametri` (08-06-PLAN.md,
CUR-01/CUR-02/CUR-03): round-trip a vuoto sui cinque fogli, il file di
default che non azzera mai il coefficiente impresa, la variante con
margine che lo aggiorna, nessuna eliminazione su import parziale, il
forfait arredo (buco storico chiuso da questo piano) modificabile da
Excel, il gate admin-only, e il file del computo rifiutato con un
messaggio leggibile invece di un 500.
"""

from __future__ import annotations

import io

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.arredo import ForfaitArredo
from app.models.dettaglio_pro import CoefficienteQuantitaVoce
from app.models.listino import ListinoCategoria
from app.models.user import User
from app.services.export_excel.parametri import build_workbook_parametri
from app.services.export_excel.workbook import TOKEN_CANCELLA
from app.services.import_excel.parametri import diff as diff_parametri
from app.schemas.admin_import import RigaPiattaIn
from scripts.seed import load_seed_data, seed

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
IMPORT_URL = "/api/v1/admin/import-excel/parametri"

ADMIN_EMAIL = "admin.import.parametri@example.com"

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    db_path = tmp_path / "test_import_parametri.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    test_client = TestClient(app)
    test_client._session_local = testing_session_local
    return test_client


def _registra_admin(client, email=ADMIN_EMAIL, nome="Admin Import Parametri"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def _registra_ruolo(client, role: str, email: str, nome: str):
    resp = client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})
    with client._session_local() as db:
        user = db.query(User).filter_by(email=email).one()
        user.role = role
        db.commit()
    return resp


def _workbook_default(client) -> bytes:
    with client._session_local() as db:
        file_bytes, _ = build_workbook_parametri(db, con_margine=False)
    return file_bytes


def _workbook_con_margine(client) -> bytes:
    with client._session_local() as db:
        file_bytes, _ = build_workbook_parametri(db, con_margine=True)
    return file_bytes


def _post_preview(client, xlsx_bytes: bytes):
    return client.post(
        f"{IMPORT_URL}/preview",
        files={"file": ("parametri.xlsx", xlsx_bytes, MIME_XLSX)},
    )


def _a_riga_piatta_in(diff_riga: dict) -> dict:
    """Ricostruisce `RigaPiattaIn` da `DiffRigaOut` esattamente come fa il
    client (round-trip stateless, `FlatImportDialog.tsx::toRigaPiattaIn`).

    Questo helper E' il sostituto del frontend in questa suite: se diverge
    dalla funzione TypeScript, i test smettono di dire qualcosa sul flusso
    reale. Come quella, separa i `null`: un campo il cui valore nuovo e'
    `null` e' una CANCELLAZIONE e va dichiarato in `campi_da_cancellare`,
    non lasciato dentro `valori` — dove il resolver lo stringificherebbe
    (`str(None) == "None"`, CR-02).
    """
    valori = {}
    campi_da_cancellare = []
    for campo, valore in diff_riga["valori_nuovi"].items():
        if valore is None:
            campi_da_cancellare.append(campo)
        else:
            valori[campo] = valore
    return {
        "foglio": diff_riga["foglio"],
        "id": diff_riga["id"],
        "valori": valori,
        "campi_da_cancellare": campi_da_cancellare,
    }


def _post_confirm(client, preview_body: dict):
    nuove = [_a_riga_piatta_in(r) for r in preview_body["nuove"]]
    modificate = [_a_riga_piatta_in(r) for r in preview_body["modificate"]]
    return client.post(
        f"{IMPORT_URL}/confirm",
        json={"risorsa": "parametri", "nuove": nuove, "modificate": modificate},
    )


def _modifica_cella(xlsx_bytes: bytes, foglio: str, riga_id, colonna: str, nuovo_valore) -> bytes:
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb[foglio]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    col_id = header.index("id")
    col_target = header.index(colonna)
    for row in ws.iter_rows(min_row=2):
        if str(row[col_id].value) == str(riga_id):
            row[col_target].value = nuovo_valore
            break
    else:
        raise AssertionError(f"riga con id={riga_id!r} non trovata nel foglio {foglio}")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _tronca_righe(xlsx_bytes: bytes, foglio: str, mantieni: int) -> bytes:
    """Simula un file caricato con un sottoinsieme delle righe (T-08-51):
    rimuove tutte le righe dati del foglio tranne le prime `mantieni`."""
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb[foglio]
    for r in range(ws.max_row, 1 + mantieni, -1):
        ws.delete_rows(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestRoundtripAVuoto:
    def test_roundtrip_parametri_a_vuoto(self, client):
        _registra_admin(client)
        xlsx = _workbook_default(client)

        response = _post_preview(client, xlsx)
        assert response.status_code == 200
        body = response.json()

        assert len(body["nuove"]) == 0
        assert len(body["modificate"]) == 0


class TestFileSenzaMargineNonAzzeraIlCoefficiente:
    def test_file_senza_margine_non_azzera_il_coefficiente(self, client):
        _registra_admin(client)
        xlsx = _workbook_default(client)

        with client._session_local() as db:
            margini_prima = {
                r.id: r.coefficiente_impresa
                for r in db.query(ListinoCategoria).order_by(ListinoCategoria.id).all()
            }

        # Cambia un campo non sensibile (base_eur_mq) per esercitare davvero
        # il ramo di apply, sullo stesso foglio che NON contiene il margine.
        primo_id = next(iter(margini_prima))
        xlsx_modificato = _modifica_cella(xlsx, "listino_categoria", primo_id, "base_eur_mq", 999.0)

        preview = _post_preview(client, xlsx_modificato).json()
        assert len(preview["modificate"]) >= 1

        confirm = _post_confirm(client, preview)
        assert confirm.status_code == 200

        with client._session_local() as db:
            margini_dopo = {
                r.id: r.coefficiente_impresa
                for r in db.query(ListinoCategoria).order_by(ListinoCategoria.id).all()
            }

        assert margini_dopo == margini_prima


class TestFileConMargineAggiornaIlCoefficiente:
    def test_file_con_margine_aggiorna_il_coefficiente(self, client):
        _registra_admin(client)
        xlsx = _workbook_con_margine(client)

        with client._session_local() as db:
            riga = db.query(ListinoCategoria).order_by(ListinoCategoria.id).first()
            riga_id = riga.id
            margine_prima = riga.coefficiente_impresa

        nuovo_margine = 0.9 if float(margine_prima) != 0.9 else 0.8
        xlsx_modificato = _modifica_cella(xlsx, "listino_categoria", riga_id, "coefficiente_impresa", nuovo_margine)

        preview = _post_preview(client, xlsx_modificato).json()
        assert len(preview["modificate"]) >= 1

        confirm = _post_confirm(client, preview)
        assert confirm.status_code == 200

        with client._session_local() as db:
            riga_dopo = db.get(ListinoCategoria, riga_id)
            assert float(riga_dopo.coefficiente_impresa) == pytest.approx(nuovo_margine)


class TestModificaMoltiplicatoreViaExcel:
    def test_modifica_moltiplicatore_via_excel(self, client):
        _registra_admin(client)
        xlsx = _workbook_default(client)

        wb = openpyxl.load_workbook(io.BytesIO(xlsx))
        ws = wb["moltiplicatori"]
        prima_riga = next(ws.iter_rows(min_row=2, max_row=2))
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        riga_id = prima_riga[header.index("id")].value

        xlsx_modificato = _modifica_cella(xlsx, "moltiplicatori", riga_id, "valore", 1.23)

        preview = _post_preview(client, xlsx_modificato).json()
        righe_moltiplicatori = [r for r in preview["modificate"] if r["foglio"] == "moltiplicatori"]
        assert len(righe_moltiplicatori) == 1
        assert righe_moltiplicatori[0]["campi_modificati"] == ["valore"]

        confirm = _post_confirm(client, preview)
        assert confirm.status_code == 200

        with client._session_local() as db:
            from app.models.catalogo import Moltiplicatore

            riga_dopo = db.get(Moltiplicatore, riga_id)
            assert float(riga_dopo.valore) == pytest.approx(1.23)


class TestImportNonEliminaMaiRighe:
    def test_import_non_elimina_mai_righe(self, client):
        _registra_admin(client)
        xlsx = _workbook_default(client)

        with client._session_local() as db:
            conteggi_prima = {
                "moltiplicatori": db.query(ListinoCategoria).count(),
                "forfait_arredo": db.query(ForfaitArredo).count(),
                "coeff_pro": db.query(CoefficienteQuantitaVoce).count(),
            }

        # Sottoinsieme: rimuove tutte le righe forfait_arredo tranne la prima.
        xlsx_troncato = _tronca_righe(xlsx, "forfait_arredo", mantieni=1)

        preview = _post_preview(client, xlsx_troncato).json()
        confirm = _post_confirm(client, preview)
        assert confirm.status_code == 200

        with client._session_local() as db:
            conteggi_dopo = {
                "moltiplicatori": db.query(ListinoCategoria).count(),
                "forfait_arredo": db.query(ForfaitArredo).count(),
                "coeff_pro": db.query(CoefficienteQuantitaVoce).count(),
            }

        assert conteggi_dopo == conteggi_prima


class TestForfaitArredoModificabileDaExcel:
    def test_forfait_arredo_modificabile_da_excel(self, client):
        _registra_admin(client)
        xlsx = _workbook_default(client)

        with client._session_local() as db:
            riga = db.query(ForfaitArredo).order_by(ForfaitArredo.id).first()
            riga_id = riga.id

        xlsx_modificato = _modifica_cella(xlsx, "forfait_arredo", riga_id, "eur_min", 111.0)
        xlsx_modificato = _modifica_cella(xlsx_modificato, "forfait_arredo", riga_id, "eur_max", 222.0)

        preview = _post_preview(client, xlsx_modificato).json()
        righe_forfait = [r for r in preview["modificate"] if r["foglio"] == "forfait_arredo"]
        assert len(righe_forfait) == 1

        confirm = _post_confirm(client, preview)
        assert confirm.status_code == 200

        with client._session_local() as db:
            riga_dopo = db.get(ForfaitArredo, riga_id)
            assert float(riga_dopo.eur_min) == pytest.approx(111.0)
            assert float(riga_dopo.eur_max) == pytest.approx(222.0)


class TestImportVietatoAlNonAdmin:
    def test_import_vietato_al_non_admin(self, client):
        xlsx = None
        _registra_admin(client, email="admin.per.file@example.com", nome="Admin Per File")
        with client._session_local() as db:
            file_bytes, _ = build_workbook_parametri(db, con_margine=False)
        xlsx = file_bytes

        for role, email in (("consulente", "consulente.import@example.com"), ("user", "utente.import@example.com")):
            _registra_ruolo(client, role, email, f"Ruolo {role}")

            response_preview = _post_preview(client, xlsx)
            assert response_preview.status_code == 403

            response_confirm = client.post(
                f"{IMPORT_URL}/confirm", json={"risorsa": "parametri", "nuove": [], "modificate": []}
            )
            assert response_confirm.status_code == 403


class TestFileDelComputoRifiutatoConMessaggio:
    def test_file_del_computo_rifiutato_con_messaggio(self, client):
        _registra_admin(client)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "A-EDILE"
        ws.append((None, "A.1", "DEMOLIZIONI", None, None, None))
        wb.create_sheet("B-FINITURE")
        wb.create_sheet("C- SERRAMENTI PORTE  ")
        wb.create_sheet("D- PRODOTTI")
        buf = io.BytesIO()
        wb.save(buf)

        response = _post_preview(client, buf.getvalue())
        assert response.status_code == 400
        assert response.json()["detail"]


class TestCancellazioneRoundTripCoefficientiPro:
    """CR-02, lato `parametri`: `#CANCELLA#` su `domanda_mirata_key` deve
    scrivere NULL, non la stringa letterale `"None"`.

    Stessa meccanica del lead (vedi `test_import_lead.py`): la preview
    rappresenta la cancellazione con `valori_nuovi[campo] = None`, e se il
    client la rimanda dentro `valori` invece che in `campi_da_cancellare`
    il resolver fa `str(None).strip()` — una stringa non vuota, che passa
    la validazione e finisce a database.
    """

    def test_cancella_domanda_mirata_key_scrive_null(self, client):
        _registra_admin(client)
        with client._session_local() as db:
            coeff = (
                db.query(CoefficienteQuantitaVoce)
                .filter(CoefficienteQuantitaVoce.domanda_mirata_key.isnot(None))
                .order_by(CoefficienteQuantitaVoce.id)
                .first()
            )
            assert coeff is not None
            coeff_id = coeff.id

        xlsx = _workbook_default(client)
        xlsx_modificato = _modifica_cella(
            xlsx, "coefficienti_pro", coeff_id, "domanda_mirata_key", TOKEN_CANCELLA
        )

        preview = _post_preview(client, xlsx_modificato)
        assert preview.status_code == 200
        body = preview.json()
        modificate = [r for r in body["modificate"] if r["foglio"] == "coefficienti_pro"]
        assert len(modificate) == 1
        assert modificate[0]["valori_nuovi"]["domanda_mirata_key"] is None

        confirm = _post_confirm(client, body)
        assert confirm.status_code == 200

        with client._session_local() as db:
            dopo = db.get(CoefficienteQuantitaVoce, coeff_id)
            assert dopo.domanda_mirata_key != "None", "scritta la stringa 'None' invece di NULL"
            assert dopo.domanda_mirata_key is None

    def test_un_null_dentro_valori_e_uno_scarto_non_una_stringa(self, client):
        """Difesa in profondita': un client che sbaglia a ricostruire il
        payload non deve poter corrompere il campo."""
        _registra_admin(client)
        with client._session_local() as db:
            coeff = (
                db.query(CoefficienteQuantitaVoce)
                .filter(CoefficienteQuantitaVoce.domanda_mirata_key.isnot(None))
                .order_by(CoefficienteQuantitaVoce.id)
                .first()
            )
            coeff_id, chiave_prima = coeff.id, coeff.domanda_mirata_key

        payload_sbagliato = {
            "risorsa": "parametri",
            "nuove": [],
            "modificate": [
                {
                    "foglio": "coefficienti_pro",
                    "id": str(coeff_id),
                    "valori": {"domanda_mirata_key": None},
                    "campi_da_cancellare": [],
                }
            ],
        }
        confirm = client.post(f"{IMPORT_URL}/confirm", json=payload_sbagliato)
        assert confirm.status_code == 200
        assert confirm.json()["righe_applicate"] == 0

        with client._session_local() as db:
            assert db.get(CoefficienteQuantitaVoce, coeff_id).domanda_mirata_key == chiave_prima

    def test_la_preview_segnala_lo_scarto_su_un_null_dentro_valori(self, client):
        _registra_admin(client)
        with client._session_local() as db:
            coeff = (
                db.query(CoefficienteQuantitaVoce)
                .filter(CoefficienteQuantitaVoce.domanda_mirata_key.isnot(None))
                .order_by(CoefficienteQuantitaVoce.id)
                .first()
            )
            righe = [
                RigaPiattaIn(
                    foglio="coefficienti_pro",
                    id=str(coeff.id),
                    valori={"domanda_mirata_key": None},
                    campi_da_cancellare=[],
                )
            ]
            nuove, modificate, scarti = diff_parametri(db, righe)

        assert nuove == [] and modificate == []
        assert len(scarti) == 1
        assert "domanda_mirata_key" in scarti[0].motivo
        assert "campi_da_cancellare" in scarti[0].motivo
