"""Avatar profilo su object storage R2 (migrazione 0013).

Tre garanzie contano piu' delle altre:

1. **La validazione MIME e' reale.** Un `.txt` rinominato `.png`, inviato con
   `content_type: image/png`, deve prendere 400: l'unica cosa fidata e' cio'
   che Pillow riesce ad aprire.
2. **Gli EXIF spariscono.** Una foto con coordinate GPS caricata come avatar
   diventerebbe la posizione di casa dell'utente pubblicata su un URL
   pubblico. La ri-encodifica WEBP li elimina.
3. **Senza credenziali si risponde 503 e non si scrive in DB.** Mai un 500 di
   boto3, mai una colonna che punta a un oggetto che non esiste.

Il client boto3 e' monkeypatchato: la suite non tocca la rete.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
import app.services.storage_service as storage_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.user import User

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
ME_URL = "/api/v1/auth/me"
AVATAR_URL = "/api/v1/auth/me/avatar"

PUBLIC_BASE = "https://pub-test.r2.dev"


class FakeS3:
    """Doppio del client boto3: registra le chiamate invece di fare rete."""

    def __init__(self) -> None:
        self.put: list[dict] = []
        self.deleted: list[str] = []

    def put_object(self, **kwargs) -> dict:
        self.put.append(kwargs)
        return {}

    def delete_object(self, **kwargs) -> dict:
        self.deleted.append(kwargs["Key"])
        return {}


@pytest.fixture()
def fake_s3(monkeypatch):
    """Storage configurato e funzionante, senza rete."""
    fake = FakeS3()
    monkeypatch.setattr(settings, "R2_ENDPOINT_URL", "https://example.r2.cloudflarestorage.com")
    monkeypatch.setattr(settings, "R2_ACCESS_KEY_ID", "key")
    monkeypatch.setattr(settings, "R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setattr(settings, "R2_BUCKET", "avatars")
    monkeypatch.setattr(settings, "R2_PUBLIC_BASE_URL", PUBLIC_BASE)
    monkeypatch.setattr(storage_module, "_client", lambda: fake)
    return fake


@pytest.fixture()
def storage_off(monkeypatch):
    """Nessuna credenziale: `storage_configured` e' False."""
    for campo in (
        "R2_ENDPOINT_URL",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
        "R2_PUBLIC_BASE_URL",
    ):
        monkeypatch.setattr(settings, campo, "")


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()

    db_path = tmp_path / "test_avatar.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    test_client = TestClient(app)
    test_client.post(
        REGISTRAZIONE_URL,
        json={"email": "avatar@example.com", "password": "Password123", "nome": "Ava"},
    )
    test_client.session_local = testing_session_local  # type: ignore[attr-defined]
    return test_client


def _png(size=(900, 600), colore="red") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, colore).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_con_gps() -> bytes:
    """JPEG con un blocco EXIF che contiene coordinate GPS."""
    exif = Image.Exif()
    exif[0x8825] = {1: "N", 2: (44.0, 41.0, 0.0), 3: "E", 4: (10.0, 37.0, 0.0)}
    buffer = io.BytesIO()
    Image.new("RGB", (300, 300), "blue").save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def _upload(client, content: bytes, filename="foto.png", content_type="image/png"):
    return client.post(AVATAR_URL, files={"file": (filename, content, content_type)})


def _db_user(client) -> User:
    with client.session_local() as session:  # type: ignore[attr-defined]
        return session.query(User).filter_by(email="avatar@example.com").one()


class TestUploadRiuscito:
    def test_png_valido_ritorna_200_e_carica_un_webp(self, client, fake_s3):
        response = _upload(client, _png())

        assert response.status_code == 200
        assert len(fake_s3.put) == 1
        chiamata = fake_s3.put[0]
        assert chiamata["ContentType"] == "image/webp"
        assert chiamata["Key"].endswith(".webp")
        assert "immutable" in chiamata["CacheControl"]
        caricata = Image.open(io.BytesIO(chiamata["Body"]))
        assert caricata.format == "WEBP"
        assert max(caricata.size) <= 512

    def test_avatar_url_torna_in_userout_e_finisce_in_db(self, client, fake_s3):
        response = _upload(client, _png())

        url = response.json()["avatar_url"]
        assert url.startswith(PUBLIC_BASE + "/avatars/")
        assert _db_user(client).avatar_url == url
        assert client.get(ME_URL).json()["avatar_url"] == url

    def test_la_chiave_cambia_a_ogni_upload(self, client, fake_s3):
        prima = _upload(client, _png()).json()["avatar_url"]
        seconda = _upload(client, _png(colore="green")).json()["avatar_url"]

        assert prima != seconda

    def test_il_secondo_upload_cancella_il_vecchio_oggetto(self, client, fake_s3):
        prima = _upload(client, _png()).json()["avatar_url"]
        _upload(client, _png(colore="green"))

        assert fake_s3.deleted == [prima.removeprefix(PUBLIC_BASE + "/")]


class TestValidazione:
    def test_txt_rinominato_png_prende_400(self, client, fake_s3):
        """La validazione MIME reale: estensione e content_type dichiarato
        sono entrambi `png`, ma il contenuto non e' un'immagine."""
        response = _upload(client, b"Questo non e' un PNG.", filename="finta.png")

        assert response.status_code == 400
        assert fake_s3.put == []

    def test_file_oltre_5mb_prende_400_senza_decodifica(self, client, fake_s3):
        response = _upload(client, b"\x89PNG\r\n\x1a\n" + b"\x00" * (5 * 1024 * 1024 + 1))

        assert response.status_code == 400
        assert "5MB" in response.json()["detail"]
        assert fake_s3.put == []

    def test_gif_valida_ma_formato_non_ammesso_prende_400(self, client, fake_s3):
        buffer = io.BytesIO()
        Image.new("RGB", (100, 100), "red").save(buffer, format="GIF")

        response = _upload(client, buffer.getvalue(), filename="anim.gif", content_type="image/gif")

        assert response.status_code == 400
        assert fake_s3.put == []

    def test_file_vuoto_prende_400(self, client, fake_s3):
        response = _upload(client, b"")

        assert response.status_code == 400


class TestPrivacy:
    def test_gli_exif_gps_non_sopravvivono_alla_ri_encodifica(self, client, fake_s3):
        originale = _jpeg_con_gps()
        assert Image.open(io.BytesIO(originale)).getexif().get_ifd(0x8825), "il fixture deve avere il GPS"

        _upload(client, originale, filename="vacanza.jpg", content_type="image/jpeg")

        caricata = Image.open(io.BytesIO(fake_s3.put[0]["Body"]))
        assert not caricata.getexif().get_ifd(0x8825)

    def test_avatar_url_non_e_scrivibile_dal_patch_profilo(self, client, fake_s3):
        response = client.patch(
            ME_URL,
            json={"nome": "Ava", "avatar_url": "https://evil.example.com/tracker.png"},
        )

        assert response.status_code == 200
        assert response.json()["avatar_url"] is None
        assert _db_user(client).avatar_url is None


class TestStorageNonConfigurato:
    def test_upload_senza_credenziali_ritorna_503_e_non_scrive_in_db(self, client, storage_off):
        response = _upload(client, _png())

        assert response.status_code == 503
        assert "storage" in response.json()["detail"].lower()
        assert _db_user(client).avatar_url is None


class TestAutorizzazione:
    def test_anonimo_prende_401(self, client, fake_s3):
        client.cookies.clear()

        response = _upload(client, _png())

        assert response.status_code == 401

    def test_delete_anonimo_prende_401(self, client, fake_s3):
        client.cookies.clear()

        assert client.delete(AVATAR_URL).status_code == 401


class TestRimozione:
    def test_delete_azzera_la_colonna_e_cancella_la_key_giusta(self, client, fake_s3):
        url = _upload(client, _png()).json()["avatar_url"]

        response = client.delete(AVATAR_URL)

        assert response.status_code == 200
        assert response.json()["avatar_url"] is None
        assert _db_user(client).avatar_url is None
        assert fake_s3.deleted == [url.removeprefix(PUBLIC_BASE + "/")]

    def test_delete_senza_avatar_e_idempotente(self, client, fake_s3):
        response = client.delete(AVATAR_URL)

        assert response.status_code == 200
        assert response.json()["avatar_url"] is None
        assert fake_s3.deleted == []

    def test_delete_con_storage_rotto_azzera_comunque_la_colonna(self, client, fake_s3, monkeypatch):
        _upload(client, _png())

        def esplode(**kwargs):
            raise RuntimeError("R2 irraggiungibile")

        monkeypatch.setattr(fake_s3, "delete_object", esplode)

        assert client.delete(AVATAR_URL).status_code == 200
        assert _db_user(client).avatar_url is None
