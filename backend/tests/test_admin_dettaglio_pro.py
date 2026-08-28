"""E2E test per il CRUD manuale delle voci di dettaglio Pro
(Sottocategoria/Voce) e per la mappatura comuni extra all'upload.

Copre: guard admin (403/401), CRUD completo sottocategoria e voce,
blocco delete di sottocategoria con voci (409), 404 su parent inesistente,
assenza di campi impresa nelle risposte, e comuni_extra nel confirm upload.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app

REG_URL = "/api/v1/auth/registrati"
SOTTO_URL = "/api/v1/admin/dettaglio-pro/sottocategorie"
VOCI_URL = "/api/v1/admin/dettaglio-pro/voci"

ADMIN_EMAIL = "admin.pro@example.com"
PASSWORD = "Password123"

FORBIDDEN_KEYS = {"coefficiente_impresa", "base_eur_mq", "prezzo_impresa", "coefficiente"}


def _assert_no_forbidden_keys(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, f"forbidden key '{key}'"
            _assert_no_forbidden_keys(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_forbidden_keys(item)


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", ADMIN_EMAIL)

    db_path = tmp_path / "test_admin_dettaglio_pro.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    tsl = sessionmaker(bind=engine)

    monkeypatch.setattr(db_module, "SessionLocal", tsl)
    import app.dependencies.auth as deps_auth
    import app.routers.auth as auth_router

    monkeypatch.setattr(deps_auth, "SessionLocal", tsl)
    monkeypatch.setattr(auth_router, "SessionLocal", tsl)
    for mod_name in ("dettaglio_pro", "upload_listino"):
        mod = __import__(f"app.routers.admin.{mod_name}", fromlist=["SessionLocal"])
        if hasattr(mod, "SessionLocal"):
            monkeypatch.setattr(mod, "SessionLocal", tsl)
    import app.services.listino_upload_service as up_service

    if hasattr(up_service, "SessionLocal"):
        monkeypatch.setattr(up_service, "SessionLocal", tsl)

    return TestClient(app), tsl


def _admin(c):
    return c.post(REG_URL, json={"email": ADMIN_EMAIL, "password": PASSWORD, "nome": "Admin Pro"})


def _user(c, email="u@example.com"):
    return c.post(REG_URL, json={"email": email, "password": PASSWORD, "nome": "Utente"})


def _seed_listino_categoria(sf, *, categoria="A-EDILE") -> int:
    from app.models.catalogo import Categoria
    from app.models.listino import Listino

    with sf() as s:
        listino = Listino(nome="Reggio", citta_riferimento="Reggio Emilia", is_default=True)
        s.add(listino)
        if s.get(Categoria, categoria) is None:
            s.add(Categoria(code=categoria, nome="Edile", ordine=1, iva_pct=Decimal("0.100")))
        s.commit()
        s.refresh(listino)
        return listino.id


# --- Guard -----------------------------------------------------------------


class TestDettaglioProGuard:
    def test_get_sotto_401(self, client):
        c, _ = client
        assert c.get(SOTTO_URL).status_code == 401

    def test_post_sotto_403(self, client):
        c, sf = client
        _user(c)
        lid = _seed_listino_categoria(sf)
        r = c.post(SOTTO_URL, json={"listino_id": lid, "categoria_code": "A-EDILE", "nome": "A.1"})
        assert r.status_code == 403

    def test_delete_voce_403(self, client):
        c, _ = client
        _user(c)
        assert c.delete(f"{VOCI_URL}/1").status_code == 403


# --- CRUD ------------------------------------------------------------------


class TestDettaglioProCrud:
    def test_full_sottocategoria_e_voce_lifecycle(self, client):
        c, sf = client
        _admin(c)
        lid = _seed_listino_categoria(sf)

        # crea sottocategoria
        r = c.post(
            SOTTO_URL,
            json={"listino_id": lid, "categoria_code": "A-EDILE", "codice": "A.1", "nome": "Demolizioni", "famiglia": "gerarchica", "ordine": 1},
        )
        assert r.status_code == 201, r.text
        sid = r.json()["id"]
        _assert_no_forbidden_keys(r.json())

        # lista sottocategorie per listino
        lst = c.get(SOTTO_URL, params={"listino_id": lid})
        assert lst.status_code == 200 and len(lst.json()) == 1

        # patch sottocategoria
        rp = c.patch(f"{SOTTO_URL}/{sid}", json={"nome": "Demolizioni e rimozioni"})
        assert rp.status_code == 200 and rp.json()["nome"] == "Demolizioni e rimozioni"

        # crea voce sotto la sottocategoria
        rv = c.post(
            VOCI_URL,
            json={"sottocategoria_id": sid, "descrizione": "Demolizione tramezzi", "um": "m2", "prezzo_unitario_cliente": "25.50", "ordine": 0},
        )
        assert rv.status_code == 201, rv.text
        vid = rv.json()["id"]
        _assert_no_forbidden_keys(rv.json())
        assert rv.json()["prezzo_unitario_cliente"] == "25.50"

        # lista voci
        lv = c.get(VOCI_URL, params={"sottocategoria_id": sid})
        assert lv.status_code == 200 and len(lv.json()) == 1

        # delete sottocategoria con voce -> 409
        assert c.delete(f"{SOTTO_URL}/{sid}").status_code == 409

        # patch + delete voce
        assert c.patch(f"{VOCI_URL}/{vid}", json={"prezzo_unitario_cliente": "30.00"}).status_code == 200
        assert c.delete(f"{VOCI_URL}/{vid}").status_code == 204

        # ora la sottocategoria si elimina
        assert c.delete(f"{SOTTO_URL}/{sid}").status_code == 204

    def test_sotto_listino_inesistente_404(self, client):
        c, _ = client
        _admin(c)
        r = c.post(SOTTO_URL, json={"listino_id": 9999, "categoria_code": "A-EDILE", "nome": "X"})
        assert r.status_code == 404

    def test_voce_sotto_inesistente_404(self, client):
        c, _ = client
        _admin(c)
        r = c.post(VOCI_URL, json={"sottocategoria_id": 9999, "descrizione": "x", "um": "m2", "prezzo_unitario_cliente": "1.00"})
        assert r.status_code == 404


# --- Comuni extra all'upload ----------------------------------------------


class TestComuniExtra:
    def test_confirm_nuova_citta_con_comuni_extra(self, client):
        c, sf = client
        _admin(c)
        from app.models.catalogo import Categoria

        with sf() as s:
            if s.get(Categoria, "A-EDILE") is None:
                s.add(Categoria(code="A-EDILE", nome="Edile", ordine=1, iva_pct=Decimal("0.100")))
                s.commit()

        payload = {
            "target": {"kind": "nuova_citta", "citta": "Modena", "is_default": False},
            "nuove": [
                {
                    "categoria_code": "A-EDILE",
                    "sottocategoria_nome": "A.1 Demolizioni",
                    "sottocategoria_famiglia": "gerarchica",
                    "descrizione": "Demolizione tramezzi",
                    "um": "m2",
                    "prezzo_unitario_cliente": "25.00",
                }
            ],
            "modificate": [],
            "comuni_extra": ["Carpi", "Sassuolo", "  "],
        }
        r = c.post("/api/v1/admin/upload-listino/confirm", json=payload)
        assert r.status_code == 200, r.text
        listino_id = r.json()["listino_id"]

        # Modena (principale) + Carpi + Sassuolo mappati; blank ignorato
        from app.models.catalogo import ComuneListino

        with sf() as s:
            comuni = {row.comune_nome for row in s.query(ComuneListino).filter_by(listino_id=listino_id)}
        assert {"Modena", "Carpi", "Sassuolo"} <= comuni
        assert not any(x.strip() == "" for x in comuni)
