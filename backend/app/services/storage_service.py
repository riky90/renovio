"""Storage degli avatar, con due backend intercambiabili.

Il modulo espone quattro funzioni — `avatar_key`, `upload_avatar`,
`delete_avatar`, `key_from_url` — e il chiamante non sa quale backend sta
usando. La scelta e' un dato di configurazione, non un ramo nel router:

    "r2"  cinque R2_* configurate -> Cloudflare R2 via boto3 (strada maestra)
    "db"  altrimenti              -> tabella `avatar_blob`, servita da noi

**R2 ha la precedenza** e il suo codice e' intatto: il giorno che le cinque
variabili compaiono, l'app ci torna sopra senza migrazioni ne' deploy di
codice. Il backend "db" esiste perche' aprire un bucket R2 richiede una carta
di credito anche sul piano gratuito, e l'upload avatar rispondeva 503 in
produzione dal giorno del deploy.

Perche' non il disco: il filesystem di Render e' effimero, quindi un avatar
scritto su disco sopravvive fino al primo redeploy. Il database e' l'unico
posto durevole che l'app ha gia'.

I due backend condividono lo **spazio dei nomi delle key**
(`avatars/{user_id}/{uuid4}.webp`), quindi `key_from_url` resta una funzione
sola e una key scritta sotto un backend resta leggibile sotto l'altro.

Il client boto3 e' costruito **lazy dentro le funzioni**, mai a livello di
modulo: stesso pattern dell'import lazy di WeasyPrint in `pdf_service.py`.
Cosi' l'app resta importabile e la suite gira senza credenziali ne' rete.

Un backend privo del suo prerequisito solleva `StorageNotConfigured`, che il
router traduce in un 503 esplicito: mai un 500 di boto3, mai un fallback
silenzioso su disco (D-avatar: nessun fallback locale).
"""

from __future__ import annotations

import uuid

from app.config import settings


class StorageNotConfigured(RuntimeError):
    """Il backend attivo non ha il suo prerequisito. Il chiamante risponde 503."""


class StorageError(RuntimeError):
    """L'operazione e' fallita (rete, credenziali, permessi, database)."""


# Prefisso di rotta del backend "db". Deve restare allineato a
# `routers/avatars.py`, che e' l'unico a servirlo. E' `/media` e non
# `/avatars` perche' la key comincia gia' per `avatars/`: il secondo darebbe
# URL come `/api/v1/avatars/avatars/9/xxx.webp`, e quegli URL finiscono
# scritti in `user.avatar_url` per sempre.
DB_URL_PREFIX = "/api/v1/media"


def avatar_key(user_id: int) -> str:
    """`avatars/{user_id}/{uuid4}.webp` — il nome e' casuale, quindi non
    enumerabile da chi conosce lo user_id, e cambia a ogni upload, il che da'
    il cache-busting gratis su un oggetto servito come immutable."""
    return f"avatars/{user_id}/{uuid.uuid4().hex}.webp"


def _user_id_from_key(key: str) -> int:
    """Estrae lo user_id da una key prodotta da `avatar_key`.

    Il formato della key e' di questo modulo, quindi rileggerlo qui non e' un
    accoppiamento con l'esterno. Serve al backend "db", che ha bisogno della
    FK verso `user.id` mentre `upload_avatar` riceve solo la key: preferisco
    ri-derivarla da un formato che possiedo piuttosto che allargare la firma
    e costringere anche il backend R2 a un parametro che non usa.
    """
    try:
        return int(key.split("/")[1])
    except (IndexError, ValueError) as exc:
        raise StorageError(f"Key non riconosciuta: {key}") from exc


def public_base_url() -> str:
    """Base pubblica sotto cui vive `User.avatar_url` per il backend attivo,
    senza slash finale. Vuota se il backend non e' configurato."""
    if settings.storage_backend == "r2":
        return settings.R2_PUBLIC_BASE_URL.rstrip("/")
    if not settings.BACKEND_PUBLIC_URL:
        return ""
    return settings.BACKEND_PUBLIC_URL.rstrip("/") + DB_URL_PREFIX


# --------------------------------------------------------------------------
# Backend R2
# --------------------------------------------------------------------------


def _client():
    """Costruisce il client S3 per R2. Import di boto3 dentro la funzione.

    `signature_version='s3v4'` e `region_name='auto'` sono richiesti da R2;
    `addressing_style='path'` evita il virtual-host style, che sull'endpoint
    R2 non risolve.
    """
    if not settings.storage_configured:
        raise StorageNotConfigured("Storage non configurato")

    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def _r2_upload(key: str, data: bytes) -> str:
    client = _client()
    try:
        client.put_object(
            Bucket=settings.R2_BUCKET,
            Key=key,
            Body=data,
            ContentType="image/webp",
            CacheControl="public, max-age=31536000, immutable",
        )
    except Exception as exc:  # noqa: BLE001 - boto3 alza famiglie diverse
        raise StorageError(f"Upload non riuscito: {exc}") from exc

    return f"{settings.R2_PUBLIC_BASE_URL.rstrip('/')}/{key}"


def _r2_delete(key: str) -> None:
    client = _client()
    try:
        client.delete_object(Bucket=settings.R2_BUCKET, Key=key)
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"Cancellazione non riuscita: {exc}") from exc


# --------------------------------------------------------------------------
# Backend database
# --------------------------------------------------------------------------


def _db_upload(key: str, data: bytes) -> str:
    """Scrive i byte in `avatar_blob` e ritorna l'URL assoluto da cui li
    serviremo. Sessione propria e commit immediato: il contratto di
    `upload_avatar` e' che al ritorno l'oggetto sia gia' recuperabile, esatto
    come per un `put_object` su R2, cosi' il router puo' continuare a scrivere
    `user.avatar_url` solo dopo."""
    base = public_base_url()
    if not base:
        raise StorageNotConfigured("BACKEND_PUBLIC_URL non impostato")

    from app.db import SessionLocal
    from app.models.avatar import AvatarBlob

    user_id = _user_id_from_key(key)
    try:
        with SessionLocal() as session:
            session.add(
                AvatarBlob(
                    key=key,
                    user_id=user_id,
                    content_type="image/webp",
                    dati=data,
                )
            )
            session.commit()
    except Exception as exc:  # noqa: BLE001 - SQLAlchemy alza famiglie diverse
        raise StorageError(f"Upload non riuscito: {exc}") from exc

    return f"{base}/{key}"


def _db_delete(key: str) -> None:
    from app.db import SessionLocal
    from app.models.avatar import AvatarBlob

    try:
        with SessionLocal() as session:
            blob = session.get(AvatarBlob, key)
            if blob is not None:
                session.delete(blob)
                session.commit()
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"Cancellazione non riuscita: {exc}") from exc


def load_avatar(key: str) -> tuple[bytes, str] | None:
    """Rilegge i byte di un avatar dal backend "db". Ritorna `None` se la key
    non esiste. Usata solo da `routers/avatars.py`: su R2 le immagini le serve
    la CDN e questa funzione non ha ragione di esistere."""
    from app.db import SessionLocal
    from app.models.avatar import AvatarBlob

    with SessionLocal() as session:
        blob = session.get(AvatarBlob, key)
        if blob is None:
            return None
        return blob.dati, blob.content_type


# --------------------------------------------------------------------------
# API pubblica: dispatch sul backend attivo
# --------------------------------------------------------------------------


def upload_avatar(key: str, data: bytes) -> str:
    """Carica i byte WEBP e ritorna l'URL pubblico da salvare su
    `User.avatar_url`. Su R2 la `CacheControl` e' immutable e la key e' gia'
    unica per upload, quindi la cache non va mai invalidata; il backend "db"
    manda lo stesso header da `routers/avatars.py`."""
    if settings.storage_backend == "r2":
        return _r2_upload(key, data)
    return _db_upload(key, data)


def delete_avatar(key: str) -> None:
    """Cancella un oggetto. Best-effort per costruzione: il chiamante la usa
    per rimuovere il vecchio avatar dopo che il nuovo e' gia' a posto, e un
    orfano non deve far fallire una richiesta andata a buon fine."""
    if settings.storage_backend == "r2":
        _r2_delete(key)
    else:
        _db_delete(key)


def key_from_url(url: str | None) -> str | None:
    """Ricava la key dall'URL pubblico salvato in DB. Ritorna None se l'URL
    non appartiene alla base pubblica del backend attivo: non si cancella mai
    un oggetto derivato da una stringa che non abbiamo scritto noi.

    Conseguenza voluta del confronto con la base **attiva**: se un giorno si
    accende R2, i vecchi URL serviti dal database smettono di essere
    riconosciuti e i loro blob restano in tabella invece di essere cancellati.
    Orfani, non danni — e il prezzo di non avere una colonna in piu' che
    registri con quale backend ogni avatar e' stato scritto.
    """
    base = public_base_url()
    if not url or not base:
        return None
    prefisso = base + "/"
    if not url.startswith(prefisso):
        return None
    return url[len(prefisso) :] or None
