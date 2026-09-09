"""Client object storage S3-compatibile (Cloudflare R2) per gli avatar.

Il client boto3 e' costruito **lazy dentro le funzioni**, mai a livello di
modulo: stesso pattern dell'import lazy di WeasyPrint in `pdf_service.py`.
Cosi' l'app resta importabile e la suite gira senza credenziali ne' rete.

Senza configurazione completa le funzioni sollevano `StorageNotConfigured`,
che il router traduce in un 503 esplicito: mai un 500 di boto3, mai un
fallback silenzioso su disco (D-avatar: nessun fallback locale).
"""

from __future__ import annotations

import uuid

from app.config import settings


class StorageNotConfigured(RuntimeError):
    """Le variabili R2_* non sono impostate. Il chiamante risponde 503."""


class StorageError(RuntimeError):
    """L'operazione sul bucket e' fallita (rete, credenziali, permessi)."""


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


def avatar_key(user_id: int) -> str:
    """`avatars/{user_id}/{uuid4}.webp` — il nome e' casuale, quindi non
    enumerabile da chi conosce lo user_id, e cambia a ogni upload, il che da'
    il cache-busting gratis su un oggetto servito come immutable."""
    return f"avatars/{user_id}/{uuid.uuid4().hex}.webp"


def upload_avatar(key: str, data: bytes) -> str:
    """Carica i byte WEBP e ritorna l'URL pubblico da salvare su
    `User.avatar_url`. `CacheControl` immutable: la chiave e' gia' unica per
    upload, quindi la cache non va mai invalidata."""
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


def delete_avatar(key: str) -> None:
    """Cancella un oggetto. Best-effort per costruzione: il chiamante la usa
    per rimuovere il vecchio avatar dopo che il nuovo e' gia' a posto, e un
    orfano nel bucket non deve far fallire una richiesta andata a buon fine."""
    client = _client()
    try:
        client.delete_object(Bucket=settings.R2_BUCKET, Key=key)
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"Cancellazione non riuscita: {exc}") from exc


def key_from_url(url: str | None) -> str | None:
    """Ricava la key dall'URL pubblico salvato in DB. Ritorna None se l'URL
    non appartiene alla base pubblica configurata: non si cancella mai un
    oggetto derivato da una stringa che non abbiamo scritto noi."""
    if not url or not settings.R2_PUBLIC_BASE_URL:
        return None
    base = settings.R2_PUBLIC_BASE_URL.rstrip("/") + "/"
    if not url.startswith(base):
        return None
    return url[len(base) :] or None
