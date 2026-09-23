"""Test che contano per la guardia di staleness D-11 (08-08-PLAN.md):
`riga_modificata_dopo_export` marca riga per riga cosa e' cambiato nel
database DOPO che il file scaricato e' stato generato, senza mai bloccare
`/confirm` — l'avviso e' informativo, la decisione resta dell'admin.

Percorso `parametri` (registro HANDLER, admin-only) coperto via HTTP con lo
stesso fixture `client` di `test_import_parametri.py`; percorso `listino`
(endpoint separato `/upload-listino`) coperto a livello di servizio, stesso
fixture `session` di `test_export_import_roundtrip.py`.
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
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
from app.models.listino import ListinoCategoria
from app.services.export_excel.listino import build_workbook_listino
from app.services.export_excel.parametri import build_workbook_parametri
from app.services.import_excel.flat import leggi_timestamp_export
from app.services.listino_upload_service import compute_diff, parse_flat_listino
from app.services.city_resolver import resolve_listino
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
IMPORT_URL = "/api/v1/admin/import-excel/parametri"

ADMIN_EMAIL = "admin.import.stale@example.com"

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    db_path = tmp_path / "test_import_stale.db"
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


@pytest.fixture()
def session():
    """Sessione a livello di servizio (sqlite in-memoria + seed reale) —
    stesso pattern di `test_export_import_roundtrip.py`."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()
        yield s


def _registra_admin(client, email=ADMIN_EMAIL, nome="Admin Import Stale"):
    return client.post(REGISTRAZIONE_URL, json={"email": email, "password": "Password123", "nome": nome})


def _workbook_default(client) -> bytes:
    with client._session_local() as db:
        file_bytes, _ = build_workbook_parametri(db, con_margine=False)
    return file_bytes


def _post_preview(client, xlsx_bytes: bytes):
    return client.post(
        f"{IMPORT_URL}/preview",
        files={"file": ("parametri.xlsx", xlsx_bytes, MIME_XLSX)},
    )


def _a_riga_piatta_in(diff_riga: dict) -> dict:
    return {
        "foglio": diff_riga["foglio"],
        "id": diff_riga["id"],
        "valori": diff_riga["valori_nuovi"],
        "campi_da_cancellare": [],
    }


def _post_confirm(client, preview_body: dict):
    nuove = [_a_riga_piatta_in(r) for r in preview_body["nuove"]]
    modificate = [_a_riga_piatta_in(r) for r in preview_body["modificate"]]
    return client.post(
        f"{IMPORT_URL}/confirm",
        json={"risorsa": "parametri", "nuove": nuove, "modificate": modificate},
    )


class TestRigaModificataDopoExportEMarcata:
    def test_riga_modificata_dopo_export_e_marcata(self, client):
        """Genera l'export, poi modifica DUE righe a database (una con
        `updated_at` forzato a un istante SUCCESSIVO all'export, l'altra a
        un istante ANTERIORE), poi ricarica il file originale: entrambe
        risultano 'modificate' (il valore diverge dal file), ma SOLO la
        prima porta `riga_modificata_dopo_export`. Un conteggio, non
        un'ispezione."""
        _registra_admin(client)
        xlsx = _workbook_default(client)  # generato_il ~= ora

        with client._session_local() as db:
            righe = db.query(ListinoCategoria).order_by(ListinoCategoria.id).all()
            assert len(righe) >= 2, "seed atteso: almeno due righe listino_categoria"

            riga_stale, riga_non_stale = righe[0], righe[1]
            riga_stale.base_eur_mq = riga_stale.base_eur_mq + Decimal("1.00")
            riga_stale.updated_at = datetime.now(timezone.utc) + timedelta(hours=1)

            riga_non_stale.base_eur_mq = riga_non_stale.base_eur_mq + Decimal("1.00")
            riga_non_stale.updated_at = datetime(2020, 1, 1, tzinfo=timezone.utc)

            db.commit()

        preview = _post_preview(client, xlsx).json()
        modificate = [r for r in preview["modificate"] if r["foglio"] == "listino_categoria"]
        assert len(modificate) == 2

        marcate = [r for r in modificate if r["riga_modificata_dopo_export"]]
        assert len(marcate) == 1
        assert sum(1 for r in modificate if r["riga_modificata_dopo_export"]) == 1


class TestFileSenzaTimestampNonMarcaNulla:
    def test_file_senza_timestamp_non_marca_nulla(self, client):
        """Un workbook la cui cella del timestamp e' vuota produce
        `generato_il=None` e ZERO righe marcate, anche quando righe
        risultano davvero modificate."""
        _registra_admin(client)
        xlsx = _workbook_default(client)

        wb = openpyxl.load_workbook(io.BytesIO(xlsx))
        wb["ISTRUZIONI"]["B4"] = None
        buf = io.BytesIO()
        wb.save(buf)
        xlsx_senza_timestamp = buf.getvalue()

        with client._session_local() as db:
            riga = db.query(ListinoCategoria).order_by(ListinoCategoria.id).first()
            riga.base_eur_mq = riga.base_eur_mq + Decimal("1.00")
            riga.updated_at = datetime.now(timezone.utc) + timedelta(hours=1)
            db.commit()

        preview = _post_preview(client, xlsx_senza_timestamp).json()
        assert preview["generato_il"] is None
        assert len(preview["modificate"]) >= 1
        assert all(not r["riga_modificata_dopo_export"] for r in preview["modificate"])


class TestAvvisoNonBloccaIlConfirm:
    def test_avviso_non_blocca_il_confirm(self, client):
        """Una riga marcata come stale non impedisce `/confirm`: applica
        comunque e restituisce il numero di righe atteso."""
        _registra_admin(client)
        xlsx = _workbook_default(client)

        with client._session_local() as db:
            riga = db.query(ListinoCategoria).order_by(ListinoCategoria.id).first()
            riga.base_eur_mq = riga.base_eur_mq + Decimal("1.00")
            riga.updated_at = datetime.now(timezone.utc) + timedelta(hours=1)
            db.commit()

        preview = _post_preview(client, xlsx).json()
        assert any(r["riga_modificata_dopo_export"] for r in preview["modificate"])

        confirm = _post_confirm(client, preview)
        assert confirm.status_code == 200
        assert confirm.json()["righe_applicate"] == len(preview["nuove"]) + len(preview["modificate"])


class TestStaleSuPercorsoListino:
    def test_stale_su_percorso_listino(self, session):
        """Stesso comportamento sul percorso `/upload-listino` (endpoint
        diverso, `compute_diff` invece di `diff` dell'handler generico):
        una `Voce` modificata a database dopo l'export si marca, le altre
        no."""
        listino, _ = resolve_listino(session, "Reggio Emilia")
        xlsx_bytes, _ = build_workbook_listino(session, listino.id)
        generato_il = leggi_timestamp_export(openpyxl.load_workbook(io.BytesIO(xlsx_bytes)))
        assert generato_il is not None

        from app.models.dettaglio_pro import Sottocategoria, Voce

        voce, _sotto = (
            session.query(Voce, Sottocategoria)
            .join(Sottocategoria, Voce.sottocategoria_id == Sottocategoria.id)
            .filter(Sottocategoria.listino_id == listino.id)
            .order_by(Voce.id)
            .first()
        )
        voce.prezzo_unitario_cliente = voce.prezzo_unitario_cliente + Decimal("1.00")
        voce.updated_at = datetime.now(timezone.utc) + timedelta(hours=1)
        session.commit()

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino, generato_il)
        assert scarti_diff == []
        marcate = [r for r in modificate if r.riga_modificata_dopo_export]
        assert len(marcate) == 1
        assert marcate[0].riga.id == voce.id
