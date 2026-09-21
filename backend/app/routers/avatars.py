"""`GET /api/v1/media/{key}` — serve gli avatar del backend "db".

Esiste solo perche' senza R2 i byte stanno in `avatar_blob` e qualcuno deve
metterli su HTTP. Con R2 configurato le immagini le serve la CDN di
Cloudflare e questa rotta non viene mai interrogata: nessun URL la nomina,
perche' `storage_service.public_base_url()` in quel caso ritorna la base R2.

**Pubblica di proposito, e non e' una svista.** La key contiene un `uuid4`
casuale generato a ogni upload, quindi conoscere lo user_id non basta a
indovinarla: e' lo stesso modello di riservatezza degli URL R2 pubblici che
questa rotta sostituisce, e un avatar profilo non e' un dato che meriti un
token per ogni `<img>`. Aggiungere qui un'autenticazione cambierebbe il
comportamento fra i due backend, che e' esattamente cio' che il dispatch in
`storage_service` esiste per evitare.

Una key inesistente e' un 404 asciutto: non si distingue mai fra "utente che
non esiste" e "utente senza avatar", perche' la differenza sarebbe un canale
di enumerazione gratuito.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

router = APIRouter(tags=["avatars"])

# Un anno, immutable: la key cambia a ogni upload (`uuid4`), quindi il
# contenuto dietro un dato URL non cambia mai e la cache non va invalidata.
# Stesso header che il backend R2 scrive come `CacheControl` sull'oggetto.
CACHE_CONTROL = "public, max-age=31536000, immutable"


@router.get("/media/{key:path}")
def leggi_avatar(key: str) -> Response:
    """`key:path` e non `key`: la key contiene slash
    (`avatars/{user_id}/{uuid4}.webp`) e un parametro normale si fermerebbe
    al primo."""
    from app.services.storage_service import load_avatar

    trovato = load_avatar(key)
    if trovato is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Avatar non trovato")

    dati, content_type = trovato
    return Response(
        content=dati,
        media_type=content_type,
        headers={"Cache-Control": CACHE_CONTROL},
    )
