"""Validazione e normalizzazione dell'immagine avatar.

L'ordine della pipeline non e' negoziabile: si valida **prima** di aprire il
contenuto, come `listino_upload_service.validate_upload` (D-20).

    dimensione <= 5 MB
      -> guardia decompression bomb (Image.MAX_IMAGE_PIXELS)
      -> Image.open().verify() e format in {JPEG, PNG, WEBP}
      -> riapertura, exif_transpose, convert("RGB"), thumbnail 512x512
      -> salvataggio WEBP q=82

Il controllo del formato fatto da Pillow **e' la validazione MIME reale**:
l'estensione del file e il `content_type` dichiarato dal client non sono mai
fidati (un `.txt` rinominato `.png` arriva qui con `image/png`).

La ri-encodifica non e' solo un ridimensionamento: normalizza il formato,
**elimina tutti gli EXIF, coordinate GPS incluse**, e neutralizza payload
nascosti nei metadati dell'originale.

Ogni fallimento e' un `AvatarValidationError` -> 400. Mai un 500.
"""

from __future__ import annotations

import io

MAX_AVATAR_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 50_000_000
FORMATI_AMMESSI = {"JPEG", "PNG", "WEBP"}
LATO_MAX = 512
WEBP_QUALITY = 82


class AvatarValidationError(ValueError):
    """Immagine rifiutata. Il router la traduce in 400 con questo messaggio."""


def process_avatar(content: bytes) -> bytes:
    """Ritorna i byte WEBP normalizzati, o alza `AvatarValidationError`."""
    if not content:
        raise AvatarValidationError("File vuoto")
    if len(content) > MAX_AVATAR_BYTES:
        raise AvatarValidationError("Immagine troppo grande (limite 5MB)")

    from PIL import Image, ImageOps, UnidentifiedImageError

    # Decompression bomb: un PNG di pochi KB puo' dichiarare 40.000x40.000
    # pixel e far esplodere la RAM alla decodifica. La guardia va messa
    # PRIMA di qualunque open().
    precedente = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        try:
            with Image.open(io.BytesIO(content)) as probe:
                formato = probe.format
                probe.verify()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise AvatarValidationError("File non riconosciuto come immagine") from exc

        if formato not in FORMATI_AMMESSI:
            raise AvatarValidationError("Formato non ammesso: usa JPEG, PNG o WEBP")

        # `verify()` consuma il file object: per lavorare sui pixel serve una
        # riapertura da capo (comportamento documentato di Pillow).
        try:
            with Image.open(io.BytesIO(content)) as img:
                img = ImageOps.exif_transpose(img)
                img = img.convert("RGB")
                img.thumbnail((LATO_MAX, LATO_MAX))
                out = io.BytesIO()
                img.save(out, format="WEBP", quality=WEBP_QUALITY)
        except (OSError, ValueError) as exc:
            raise AvatarValidationError("Immagine non elaborabile") from exc
    finally:
        Image.MAX_IMAGE_PIXELS = precedente

    return out.getvalue()
