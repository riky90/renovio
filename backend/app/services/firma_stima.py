"""Firma HMAC del risultato di `POST /stima`.

Lo snapshot di una stima salvata arriva dal CLIENT (D-09: si congela cio' che
l'utente ha visto, mai ricalcolato). Senza firma chiunque poteva salvare
`totale_min=1000` o un disclaimer inventato e scaricare un PDF col nostro logo
e numeri falsi. Ora `POST /stima` firma il risultato e `POST/PUT /me/stime`
rifiuta uno snapshot la cui firma non torna: il client puo' solo restituire
cio' che il server ha calcolato.

FORMA CANONICA
--------------
Il frontend converte i decimali (stringhe JSON) in numeri JavaScript e rimanda
l'oggetto convertito: `"47985.00"` torna come `47985`, `"0.10"` come `0.1`.
La firma si calcola quindi su una forma canonica in cui ogni numero e' il suo
`Decimal` normalizzato (`47985.00` e `47985` coincidono), le chiavi sono
ordinate e gli enum valgono il loro `value`. Parametri che non sono risultati
(`preferenze_pro`, `budget_eur`) e la firma stessa restano fuori.

Chiave: derivata da SECRET_KEY con un'etichetta dedicata, cosi' una firma di
stima non vale mai come token di reset (e viceversa).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.config import settings

#: Campi del risultato coperti dalla firma: tutti quelli di `StimaResponse`.
CAMPI_FIRMATI = frozenset(
    {
        "input",
        "fallback",
        "disclaimer",
        "valuta",
        "categorie",
        "extra",
        "totale",
        "bonus",
        "arredo",
        "confronto_finiture",
        "finiture_al_minimo",
        "tipo_effettivo",
    }
)


def _canonico(valore: Any) -> Any:
    if isinstance(valore, bool) or valore is None:
        return valore
    if isinstance(valore, (int, float, Decimal)):
        numero = Decimal(str(valore)) if isinstance(valore, float) else Decimal(valore)
        # "n:" distingue il numero 10 dalla stringa "10".
        return "n:" + format(numero.normalize(), "f")
    if isinstance(valore, Enum):
        return _canonico(valore.value)
    if isinstance(valore, BaseModel):
        return _canonico(valore.model_dump(mode="python"))
    if isinstance(valore, dict):
        return {str(k): _canonico(v) for k, v in sorted(valore.items(), key=lambda kv: str(kv[0]))}
    if isinstance(valore, (list, tuple)):
        return [_canonico(v) for v in valore]
    return valore


def _chiave() -> bytes:
    return hmac.new(settings.SECRET_KEY.encode(), b"firma-stima-v1", hashlib.sha256).digest()


def firma(risultato: BaseModel) -> str:
    dati = {campo: getattr(risultato, campo, None) for campo in sorted(CAMPI_FIRMATI)}
    corpo = json.dumps(_canonico(dati), separators=(",", ":"), ensure_ascii=False)
    digest = hmac.new(_chiave(), corpo.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def firma_valida(risultato: BaseModel, firma_ricevuta: str | None) -> bool:
    if not firma_ricevuta:
        return False
    return hmac.compare_digest(firma(risultato), firma_ricevuta)
