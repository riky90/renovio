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
from decimal import Decimal

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
from app.models.dettaglio_pro import CoefficienteQuantitaVoce
from app.models.listino import ListinoCategoria
from app.models.user import User
from app.services.export_excel.parametri import build_workbook_parametri
from app.services.export_excel.workbook import TOKEN_CANCELLA
from app.services.import_excel.parametri import diff as diff_parametri
from app.schemas.admin_import import RigaPiattaIn
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

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
    testing_session_local = sessione_di_test(engine)

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


class TestBooleaniScrittiAMano:
    """WR-01: una cella booleana compilata a mano non va passata a `bool()`.

    Excel non impone alla cella `attivo` un tipo booleano: l'admin che
    vuole disattivare una riga ci scrive `FALSE`, `no` o `0` come testo. In
    Python `bool("FALSE")`, `bool("no")` e `bool("0")` sono tutti `True`, e
    la riga sarebbe rimasta attiva con l'intenzione opposta e nessun errore
    da nessuna parte. Nessun test lo copriva perche' il round-trip a vuoto
    rilegge sempre il booleano nativo scritto dall'export.
    """

    @pytest.mark.parametrize("testo", ["FALSE", "false", "No", "0", "falso"])
    def test_falso_scritto_a_mano_disattiva_davvero(self, client, testo):
        _registra_admin(client)
        with client._session_local() as db:
            riga = db.query(ForfaitArredo).filter_by(attivo=True).order_by(ForfaitArredo.id).first()
            assert riga is not None
            riga_id = riga.id

        xlsx = _workbook_default(client)
        xlsx_modificato = _modifica_cella(xlsx, "forfait_arredo", riga_id, "attivo", testo)

        preview = _post_preview(client, xlsx_modificato)
        assert preview.status_code == 200
        body = preview.json()
        righe = [r for r in body["modificate"] if r["foglio"] == "forfait_arredo"]
        assert len(righe) == 1, f"{testo!r} non e' stato letto come una disattivazione"
        assert righe[0]["valori_nuovi"]["attivo"] is False

        confirm = _post_confirm(client, body)
        assert confirm.status_code == 200

        with client._session_local() as db:
            assert db.get(ForfaitArredo, riga_id).attivo is False

    @pytest.mark.parametrize("testo", ["TRUE", "si", "sì", "1", "x"])
    def test_vero_scritto_a_mano_riattiva(self, client, testo):
        _registra_admin(client)
        with client._session_local() as db:
            riga = db.query(ForfaitArredo).order_by(ForfaitArredo.id).first()
            riga.attivo = False
            db.commit()
            riga_id = riga.id

        xlsx = _workbook_default(client)
        xlsx_modificato = _modifica_cella(xlsx, "forfait_arredo", riga_id, "attivo", testo)

        body = _post_preview(client, xlsx_modificato).json()
        confirm = _post_confirm(client, body)
        assert confirm.status_code == 200

        with client._session_local() as db:
            assert db.get(ForfaitArredo, riga_id).attivo is True

    def test_booleano_non_interpretabile_e_uno_scarto_descritto(self, client):
        """Una parola che non vuol dire ne' vero ne' falso non deve
        diventare un'ipotesi: la riga si scarta, con un motivo leggibile."""
        _registra_admin(client)
        with client._session_local() as db:
            riga = db.query(ForfaitArredo).filter_by(attivo=True).order_by(ForfaitArredo.id).first()
            riga_id, attivo_prima = riga.id, riga.attivo

        xlsx = _workbook_default(client)
        xlsx_modificato = _modifica_cella(xlsx, "forfait_arredo", riga_id, "attivo", "forse")

        body = _post_preview(client, xlsx_modificato).json()
        assert [r for r in body["modificate"] if r["foglio"] == "forfait_arredo"] == []
        scarti = [s for s in body["scarti"] if "attivo" in s["motivo"]]
        assert len(scarti) == 1
        assert "booleano" in scarti[0]["motivo"]

        confirm = _post_confirm(client, body)
        assert confirm.status_code == 200
        with client._session_local() as db:
            assert db.get(ForfaitArredo, riga_id).attivo == attivo_prima


def _aggiungi_riga(xlsx_bytes: bytes, foglio: str, valori: dict) -> bytes:
    """Appende una riga al foglio, riempiendo le celle per nome di colonna.

    Le colonne non citate restano vuote — che nel formato piatto significa
    "campo non toccato" (D-09), esattamente come una riga compilata a mano
    da un admin che ne valorizza solo alcune.
    """
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb[foglio]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    riga = ws.max_row + 1
    for colonna, valore in valori.items():
        ws.cell(row=riga, column=header.index(colonna) + 1, value=valore)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestListinoCategoriaNuovaSenzaMargine:
    """WR-02: una riga `listino_categoria` NUOVA senza `coefficiente_impresa`
    va scartata in anteprima, non saltata in silenzio in `apply()`.

    `coefficiente_impresa` e' NOT NULL a database e non compare nell'export
    di default (regola di dominio #1: il margine esce solo dalla variante
    esplicita). Prima la riga compariva fra le `nuove` dell'anteprima,
    l'admin confermava, e `apply()` faceva un `continue` muto: il conteggio
    "N righe applicate" tornava piu' basso di quanto mostrato, senza che
    niente dicesse quale riga era saltata ne' perche'.
    """

    def test_riga_nuova_senza_margine_e_uno_scarto_visibile_in_anteprima(self, client):
        _registra_admin(client)
        with client._session_local() as db:
            conteggio_prima = db.query(ListinoCategoria).count()

        xlsx = _workbook_default(client)
        xlsx_modificato = _aggiungi_riga(
            xlsx,
            "listino_categoria",
            {"listino_id": 1, "categoria_code": "E-ARREDO", "base_eur_mq": 50.0, "iva_pct": 0.10},
        )

        preview = _post_preview(client, xlsx_modificato)
        assert preview.status_code == 200
        body = preview.json()

        assert [r for r in body["nuove"] if r["foglio"] == "listino_categoria"] == [], (
            "la riga non creabile non deve comparire fra le nuove"
        )
        scarti = [s for s in body["scarti"] if "listino_categoria" in s["motivo"]]
        assert len(scarti) == 1
        assert "coefficiente_impresa" in scarti[0]["motivo"]
        assert "E-ARREDO" in scarti[0]["motivo"]

        # il conteggio di /confirm e' coerente con quanto mostrato: zero righe
        confirm = _post_confirm(client, body)
        assert confirm.status_code == 200
        assert confirm.json()["righe_applicate"] == 0

        with client._session_local() as db:
            assert db.query(ListinoCategoria).count() == conteggio_prima

    def test_riga_nuova_con_margine_valido_viene_creata(self, client):
        """Contro-prova: con la variante export-con-margine e un valore
        valido, la riga nuova si crea e il conteggio la include."""
        _registra_admin(client)
        with client._session_local() as db:
            conteggio_prima = db.query(ListinoCategoria).count()

        xlsx = _workbook_con_margine(client)
        xlsx_modificato = _aggiungi_riga(
            xlsx,
            "listino_categoria",
            {
                "listino_id": 1,
                "categoria_code": "E-ARREDO",
                "base_eur_mq": 50.0,
                "iva_pct": 0.10,
                "coefficiente_impresa": 0.7,
            },
        )

        body = _post_preview(client, xlsx_modificato).json()
        nuove = [r for r in body["nuove"] if r["foglio"] == "listino_categoria"]
        assert len(nuove) == 1
        assert [s for s in body["scarti"] if "listino_categoria" in s["motivo"]] == []

        confirm = _post_confirm(client, body)
        assert confirm.status_code == 200

        with client._session_local() as db:
            assert db.query(ListinoCategoria).count() == conteggio_prima + 1
            creata = db.query(ListinoCategoria).filter_by(listino_id=1, categoria_code="E-ARREDO").one()
            assert creata.coefficiente_impresa == Decimal("0.700")

    def test_riga_nuova_con_margine_fuori_bound_e_uno_scarto_descritto(self, client):
        _registra_admin(client)
        xlsx = _workbook_con_margine(client)
        xlsx_modificato = _aggiungi_riga(
            xlsx,
            "listino_categoria",
            {
                "listino_id": 1,
                "categoria_code": "E-ARREDO",
                "base_eur_mq": 50.0,
                "coefficiente_impresa": 1.5,
            },
        )

        body = _post_preview(client, xlsx_modificato).json()
        assert [r for r in body["nuove"] if r["foglio"] == "listino_categoria"] == []
        scarti = [s for s in body["scarti"] if "listino_categoria" in s["motivo"]]
        assert len(scarti) == 1
        assert "non valido" in scarti[0]["motivo"]

        with client._session_local() as db:
            assert db.query(ListinoCategoria).filter_by(categoria_code="E-ARREDO").count() == 0


def _prima_riga(xlsx_bytes: bytes, foglio: str) -> dict:
    """La prima riga dati del foglio come dict colonna -> valore. Serve per
    riusare codici padre realmente esistenti (tipo_code, livello_code…)
    senza cablare nel test valori che dipendono dal seed."""
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb[foglio]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    valori = next(ws.iter_rows(min_row=2, max_row=2, values_only=True))
    return dict(zip(header, valori))


class TestIdNonNumericoNonFa500:
    """CR-01: nessuna conversione a intero puo' far cadere l'import.

    Il guard che proteggeva le tre chiavi naturali numeriche era
    `str(x).strip().lstrip("-").isdigit()`, e `lstrip("-")` toglie TUTTI i
    meno iniziali: `"--5"` lo superava e il successivo `int("--5")`
    sollevava `ValueError`. Nessuno lo catturava — non il resolver, non
    `diff()`, non il router, non un exception handler globale — quindi un
    refuso di battitura in una cella bastava a restituire 500 e a far
    perdere l'intero file, contro la regola dichiarata nella docstring del
    modulo ("un valore fuori bound e' uno scarto, non un update").

    I quattro `int(r.id)` avevano lo stesso problema per un'altra via:
    `RigaPiattaIn.id` e' una stringa libera e in `/confirm` arriva dal
    client senza alcuna validazione numerica.
    """

    def test_intero_non_solleva_mai(self):
        from app.services.import_excel.parametri import _intero

        # Il caso che passava il vecchio guard e poi esplodeva.
        assert _intero("--5") is None
        assert _intero("abc") is None
        assert _intero("") is None
        assert _intero(None) is None
        assert _intero("3.5") is None
        # I casi legittimi continuano a funzionare, spazi compresi.
        assert _intero(" 7 ") == 7
        assert _intero(7) == 7
        assert _intero("-7") == -7

    def test_listino_id_a_doppio_meno_e_uno_scarto_non_un_500(self, client):
        _registra_admin(client)
        xlsx = _workbook_con_margine(client)
        xlsx_modificato = _aggiungi_riga(
            xlsx,
            "listino_categoria",
            {
                "listino_id": "--5",
                "categoria_code": "E-ARREDO",
                "base_eur_mq": 50.0,
                "coefficiente_impresa": 0.7,
            },
        )

        response = _post_preview(client, xlsx_modificato)
        assert response.status_code == 200
        body = response.json()

        scarti = [s for s in body["scarti"] if "listino_id non numerico" in s["motivo"]]
        assert len(scarti) == 1
        assert "--5" in scarti[0]["motivo"]
        assert [r for r in body["nuove"] if r["foglio"] == "listino_categoria"] == []

    def test_voce_id_a_doppio_meno_e_uno_scarto_non_un_500(self, client):
        _registra_admin(client)
        xlsx = _workbook_default(client)
        tipo_code = _prima_riga(xlsx, "coefficienti_pro")["tipo_code"]
        xlsx_modificato = _aggiungi_riga(
            xlsx,
            "coefficienti_pro",
            {"voce_id": "--7", "tipo_code": tipo_code, "coefficiente_qta_per_mq": 1.0},
        )

        response = _post_preview(client, xlsx_modificato)
        assert response.status_code == 200
        scarti = [s for s in response.json()["scarti"] if "voce_id non numerico" in s["motivo"]]
        assert len(scarti) == 1
        assert "--7" in scarti[0]["motivo"]

    def test_opzione_id_a_doppio_meno_e_uno_scarto_non_un_500(self, client):
        _registra_admin(client)
        xlsx = _workbook_default(client)
        livello_code = _prima_riga(xlsx, "forfait_arredo")["livello_code"]
        xlsx_modificato = _aggiungi_riga(
            xlsx,
            "forfait_arredo",
            {"opzione_id": "--3", "livello_code": livello_code, "eur_min": 100.0, "eur_max": 200.0},
        )

        response = _post_preview(client, xlsx_modificato)
        assert response.status_code == 200
        scarti = [s for s in response.json()["scarti"] if "opzione_id non numerico" in s["motivo"]]
        assert len(scarti) == 1
        assert "--3" in scarti[0]["motivo"]

    def test_confirm_con_id_non_numerico_non_fa_500(self, client):
        """`/confirm` riceve gli id dal client, non dal file: il parser non
        li ha mai visti e non puo' averli filtrati. Un id non numerico deve
        essere una riga non applicata, non la caduta dell'intera richiesta
        (che porterebbe con se' tutte le altre righe valide del file)."""
        _registra_admin(client)

        response = client.post(
            f"{IMPORT_URL}/confirm",
            json={
                "risorsa": "parametri",
                "nuove": [],
                "modificate": [
                    {"foglio": "moltiplicatori", "id": "abc", "valori": {"valore": 1.5}, "campi_da_cancellare": []},
                    {"foglio": "listino_categoria", "id": "--5", "valori": {"base_eur_mq": 1.0}, "campi_da_cancellare": []},
                    {"foglio": "coefficienti_pro", "id": "x1", "valori": {"coefficiente_qta_per_mq": 1.0}, "campi_da_cancellare": []},
                    {"foglio": "forfait_arredo", "id": "--3", "valori": {"eur_min": 1.0}, "campi_da_cancellare": []},
                ],
            },
        )

        assert response.status_code == 200
        assert response.json()["righe_applicate"] == 0

    def test_una_eccezione_imprevista_in_diff_diventa_400_non_500(self, client, monkeypatch):
        """La rete di sicurezza del router, indipendente dai resolver: il
        contratto "mai un 500" non deve dipendere dal fatto che nessuno
        dimentichi mai un `int()` non protetto.

        Verifica anche che il messaggio restituito NON riporti il testo
        dell'eccezione: su questa risorsa una riga porta
        `coefficiente_impresa`, che non esce mai verso il client (regola di
        dominio #1).
        """
        from app.services.import_excel.registry import risolvi_handler

        _registra_admin(client)
        xlsx = _workbook_default(client)

        def _esplode(*args, **kwargs):
            raise RuntimeError("coefficiente_impresa=0.65 su listino 1")

        monkeypatch.setattr(risolvi_handler("parametri"), "diff", _esplode)

        response = _post_preview(client, xlsx)
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "coefficiente_impresa" not in detail
        assert "0.65" not in detail
        assert "non e' riuscito a elaborare" in detail


class TestChiaveNaturaleDuplicataNelFile:
    """CR-02: due righe con la stessa chiave naturale e senza `id` nello
    stesso file non devono far cadere l'intero import.

    `apply()` risolveva ogni riga con una query e, non trovando nulla,
    faceva `db.add(...)` senza flush. La sessione di produzione e'
    `autoflush=False` (`app/db.py`), quindi l'oggetto aggiunto per la prima
    riga non veniva scritto prima della query della seconda: due INSERT, e
    il vincolo unico scattava al `db.commit()` del router — 500, e nessuna
    riga importata, nemmeno le altre valide del file.

    QUESTA CLASSE DIPENDE DALLA CONFIGURAZIONE DELLA SESSIONE. Con
    `autoflush=True` (il default di `sessionmaker`, che tutte le fixture
    usavano prima di WR-04) il difetto e' invisibile: la query della
    seconda riga innescherebbe da sola il flush della prima. La fixture di
    questo file costruisce ora la sessione con `tests/session_factory.py`,
    cioe' con gli stessi kwargs della produzione — senza quello, questi
    test passerebbero anche sul codice rotto.
    """

    def test_la_sessione_di_test_e_configurata_come_la_produzione(self, client):
        """Guardia esplicita: se qualcuno riporta la fixture al
        `sessionmaker` nudo con i default di SQLAlchemy, e' questo test a
        dirlo, non un 500 in produzione sei mesi dopo."""
        from app.db import SessionLocal

        assert client._session_local.kw["autoflush"] is False
        assert client._session_local.kw["autoflush"] == SessionLocal.kw["autoflush"]
        assert client._session_local.kw["autocommit"] == SessionLocal.kw["autocommit"]

    def test_apply_con_due_righe_stessa_chiave_naturale_non_esplode_al_commit(self, client):
        """Il difetto nudo, senza passare da `diff()`: `apply()` riceve due
        righe identiche per chiave naturale (e' cio' che accade se il
        client re-invia un payload costruito altrove) e il commit deve
        riuscire, creando UNA riga."""
        from app.services.import_excel.parametri import apply as apply_parametri

        riga = RigaPiattaIn(
            foglio="listino_categoria",
            id=None,
            valori={
                "listino_id": 1,
                "categoria_code": "E-ARREDO",
                "base_eur_mq": 50.0,
                "coefficiente_impresa": 0.7,
            },
            campi_da_cancellare=[],
        )

        with client._session_local() as db:
            assert db.query(ListinoCategoria).filter_by(categoria_code="E-ARREDO").count() == 0
            applicate = apply_parametri(db, [riga, riga.model_copy(deep=True)], [], is_admin=True)
            db.commit()

        # IN-01: la prima riga crea, la seconda trova la prima e non cambia
        # nulla, quindi conta una sola riga applicata.
        assert applicate == 1
        with client._session_local() as db:
            assert db.query(ListinoCategoria).filter_by(listino_id=1, categoria_code="E-ARREDO").count() == 1

    def test_la_preview_segnala_il_duplicato_prima_della_conferma(self, client):
        """Il secondo intervento: l'admin deve vedere il duplicato in
        anteprima, non scoprirlo a conferma fatta."""
        _registra_admin(client)
        xlsx = _workbook_con_margine(client)
        nuova = {
            "listino_id": 1,
            "categoria_code": "E-ARREDO",
            "base_eur_mq": 50.0,
            "coefficiente_impresa": 0.7,
        }
        xlsx_modificato = _aggiungi_riga(_aggiungi_riga(xlsx, "listino_categoria", nuova), "listino_categoria", nuova)

        body = _post_preview(client, xlsx_modificato).json()

        nuove_lc = [r for r in body["nuove"] if r["foglio"] == "listino_categoria"]
        assert len(nuove_lc) == 1
        scarti = [s for s in body["scarti"] if "piu' di una riga nuova" in s["motivo"]]
        assert len(scarti) == 1
        assert "E-ARREDO" in scarti[0]["motivo"]

    def test_confirm_con_duplicato_nel_payload_crea_una_sola_riga(self, client):
        """Round-trip completo con il duplicato forzato nel payload di
        `/confirm` (il client potrebbe non aver rispettato lo scarto della
        preview): 200, nessun 500, e una sola riga a database."""
        _registra_admin(client)

        riga = {
            "foglio": "listino_categoria",
            "id": None,
            "valori": {
                "listino_id": 1,
                "categoria_code": "E-ARREDO",
                "base_eur_mq": 50.0,
                "coefficiente_impresa": 0.7,
            },
            "campi_da_cancellare": [],
        }
        response = client.post(
            f"{IMPORT_URL}/confirm",
            json={"risorsa": "parametri", "nuove": [riga, dict(riga)], "modificate": []},
        )

        assert response.status_code == 200
        with client._session_local() as db:
            assert db.query(ListinoCategoria).filter_by(listino_id=1, categoria_code="E-ARREDO").count() == 1

    def test_un_vincolo_violato_al_commit_e_un_400_non_un_500(self, client, monkeypatch):
        """Rete di sicurezza indipendente dal fix: se un vincolo venisse
        comunque violato (un'altra chiave, una rotta futura), il router
        deve tradurlo in 400 con rollback, mai in un 500. Il messaggio non
        riporta `str(exc)`: un `IntegrityError` stampa query e parametri, e
        fra quei parametri puo' esserci `coefficiente_impresa`."""
        from sqlalchemy.exc import IntegrityError

        from app.services.import_excel.registry import risolvi_handler

        _registra_admin(client)

        def _viola(db, *args, **kwargs):
            raise IntegrityError(
                "INSERT INTO listino_categoria (coefficiente_impresa) VALUES (?)",
                {"coefficiente_impresa": "0.65"},
                Exception("UNIQUE constraint failed"),
            )

        monkeypatch.setattr(risolvi_handler("parametri"), "apply", _viola)

        response = client.post(
            f"{IMPORT_URL}/confirm",
            json={"risorsa": "parametri", "nuove": [], "modificate": []},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "coefficiente_impresa" not in detail
        assert "0.65" not in detail
        assert "vincolo di unicita'" in detail


class TestConteggioERisorsaDelConfirm:
    """IN-01 e IN-02 della review della Fase 08."""

    def test_riga_esistente_senza_cambi_non_conta_come_applicata(self, client):
        from app.models.catalogo import Moltiplicatore
        from app.services.import_excel.parametri import apply as apply_parametri

        with client._session_local() as db:
            m = db.query(Moltiplicatore).order_by(Moltiplicatore.id).first()
            riga = RigaPiattaIn(
                foglio="moltiplicatori", id=str(m.id),
                valori={"valore": float(m.valore)}, campi_da_cancellare=[],
            )
            assert apply_parametri(db, [], [riga], is_admin=True) == 0
            cambiata = riga.model_copy(update={"valori": {"valore": float(m.valore) + 0.01}})
            assert apply_parametri(db, [], [cambiata], is_admin=True) == 1
            db.rollback()

    def test_confirm_rifiuta_risorsa_del_corpo_diversa_dal_path(self, client):
        _registra_admin(client)
        payload = {"risorsa": "lead", "nuove": [], "modificate": []}
        confirm = client.post(f"{IMPORT_URL}/confirm", json=payload)
        assert confirm.status_code == 400
        assert "non corrisponde" in confirm.json()["detail"]
