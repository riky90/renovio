"""Avatar profilo su object storage R2 (migrazione 0013).

Tre garanzie contano piu' delle altre:

1. **La validazione MIME e' reale.** Un `.txt` rinominato `.png`, inviato con
   `content_type: image/png`, deve prendere 400: l'unica cosa fidata e' cio'
   che Pillow riesce ad aprire.
2. **Gli EXIF spariscono.** Una foto con coordinate GPS caricata come avatar
   diventerebbe la posizione di casa dell'utente pubblicata su un URL
   pubblico. La ri-encodifica WEBP li elimina.
3. **Non si scrive mai una colonna che punta a un oggetto che non esiste.**
   Se lo storage attivo fallisce, `avatar_url` resta com'era: mai un 500 di
   boto3, mai un URL che da' 404.

Dalla migrazione 0016 i backend sono due (vedi `services/storage_service.py`):
R2 quando le cinque `R2_*` ci sono, la tabella `avatar_blob` altrimenti.
`TestBackendDatabase` esercita il secondo **senza** credenziali R2 e verifica
la proprieta' che conta: il router non e' cambiato, quindi le stesse garanzie
di validazione e privacy valgono identiche sotto entrambi. Il 503 non e' piu'
il comportamento di default — e' quello che resta quando anche il secondo
backend non ha il suo prerequisito.

Il client boto3 e' monkeypatchato: la suite non tocca la rete.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine

import app.db as db_module
import app.services.storage_service as storage_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.avatar import AvatarBlob
from app.models.user import User
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
ME_URL = "/api/v1/auth/me"
AVATAR_URL = "/api/v1/auth/me/avatar"

PUBLIC_BASE = "https://pub-test.r2.dev"
BACKEND_BASE = "https://api.test.renovio"
DB_BASE = BACKEND_BASE + "/api/v1/media"


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
def storage_db(monkeypatch):
    """Nessuna credenziale R2: il dispatch sceglie il backend `avatar_blob`."""
    for campo in (
        "R2_ENDPOINT_URL",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
        "R2_PUBLIC_BASE_URL",
    ):
        monkeypatch.setattr(settings, campo, "")
    monkeypatch.setattr(settings, "BACKEND_PUBLIC_URL", BACKEND_BASE)


@pytest.fixture()
def storage_off(monkeypatch, storage_db):
    """Nemmeno il backend db ha il suo prerequisito: niente R2 e nessun
    `BACKEND_PUBLIC_URL`, quindi non sapremmo da quale URL servire i byte che
    stiamo per scrivere. E' l'unico caso rimasto in cui si risponde 503."""
    monkeypatch.setattr(settings, "BACKEND_PUBLIC_URL", "")


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()

    db_path = tmp_path / "test_avatar.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

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
    def test_upload_senza_nessun_backend_ritorna_503_e_non_scrive_in_db(self, client, storage_off):
        """Ne' R2 ne' `BACKEND_PUBLIC_URL`: non c'e' un posto da cui servire
        l'immagine, quindi non ha senso scriverla. 503, e la colonna resta
        vuota."""
        response = _upload(client, _png())

        assert response.status_code == 503
        assert "storage" in response.json()["detail"].lower()
        assert _db_user(client).avatar_url is None


class TestBackendDatabase:
    """Il backend che si usa in produzione oggi: nessuna credenziale R2, i
    byte in `avatar_blob`, le immagini servite da `GET /api/v1/avatars/{key}`.

    Il punto di questi test non e' che il database sappia tenere dei byte —
    lo sapevamo. E' che **il router non e' cambiato**: la scelta del backend
    vive tutta in `storage_service`, quindi il 503 in produzione si e' chiuso
    senza toccare una riga di `routers/auth.py`.
    """

    def test_senza_credenziali_r2_il_backend_attivo_e_il_database(self, storage_db):
        assert settings.storage_backend == "db"

    def test_upload_ritorna_200_e_un_url_servito_da_noi(self, client, storage_db):
        response = _upload(client, _png())

        assert response.status_code == 200
        url = response.json()["avatar_url"]
        assert url.startswith(DB_BASE + "/avatars/")
        assert url.endswith(".webp")
        assert _db_user(client).avatar_url == url

    def test_i_byte_scritti_sono_il_webp_normalizzato(self, client, storage_db):
        """Stessa pipeline del backend R2: 512px massimo e formato WEBP. Se
        questa cambiasse fra i due backend, la scelta dello storage smetterebbe
        di essere invisibile al resto dell'app."""
        _upload(client, _png(size=(900, 600)))

        with client.session_local() as session:  # type: ignore[attr-defined]
            blob = session.query(AvatarBlob).one()

        assert blob.content_type == "image/webp"
        assert blob.user_id == _db_user(client).id
        immagine = Image.open(io.BytesIO(blob.dati))
        assert immagine.format == "WEBP"
        assert max(immagine.size) <= 512

    def test_la_get_serve_i_byte_con_cache_immutable(self, client, storage_db):
        url = _upload(client, _png()).json()["avatar_url"]
        key = url.removeprefix(DB_BASE + "/")

        response = client.get(f"/api/v1/media/{key}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert "immutable" in response.headers["cache-control"]
        assert Image.open(io.BytesIO(response.content)).format == "WEBP"

    def test_una_key_inesistente_e_404_non_500(self, client, storage_db):
        response = client.get("/api/v1/media/avatars/999/inventata.webp")

        assert response.status_code == 404

    def test_il_secondo_upload_cancella_la_riga_vecchia(self, client, storage_db):
        """La key cambia a ogni upload: senza la cancellazione del vecchio
        blob la tabella crescerebbe per sempre, e a differenza di un bucket
        qui i byte pesano sul database di produzione."""
        primo = _upload(client, _png(colore="red")).json()["avatar_url"]
        secondo = _upload(client, _png(colore="blue")).json()["avatar_url"]

        assert primo != secondo
        with client.session_local() as session:  # type: ignore[attr-defined]
            chiavi = [k for (k,) in session.query(AvatarBlob.key).all()]

        assert chiavi == [secondo.removeprefix(DB_BASE + "/")]

    def test_delete_azzera_la_colonna_e_svuota_la_tabella(self, client, storage_db):
        _upload(client, _png())

        response = client.delete(AVATAR_URL)

        assert response.status_code == 200
        assert _db_user(client).avatar_url is None
        with client.session_local() as session:  # type: ignore[attr-defined]
            assert session.query(AvatarBlob).count() == 0

    def test_la_validazione_vale_identica_sotto_questo_backend(self, client, storage_db):
        """Il `.txt` rinominato `.png` prende 400 anche qui, e non lascia
        residui: la validazione sta a monte del dispatch, non dentro un
        backend."""
        response = _upload(client, b"non sono un'immagine", filename="finta.png")

        assert response.status_code == 400
        with client.session_local() as session:  # type: ignore[attr-defined]
            assert session.query(AvatarBlob).count() == 0
        assert _db_user(client).avatar_url is None

    def test_gli_exif_gps_non_sopravvivono_nemmeno_qui(self, client, storage_db):
        """La garanzia di privacy e' del `avatar_service`, non dello storage:
        va verificata sotto ogni backend, altrimenti e' vera per accidente."""
        _upload(client, _jpeg_con_gps(), filename="foto.jpg", content_type="image/jpeg")

        with client.session_local() as session:  # type: ignore[attr-defined]
            blob = session.query(AvatarBlob).one()

        assert Image.open(io.BytesIO(blob.dati)).getexif().get(0x8825) is None


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
