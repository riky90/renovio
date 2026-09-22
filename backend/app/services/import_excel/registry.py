"""Registro degli handler di import generico per risorsa (piano 08-06).

`HANDLER` e' l'UNICO punto di estensione: una risorsa nuova (08-07, 08-08)
aggiunge una voce a questa mappa via `registra()`, mai una route nuova
(T-08-52 — nessuna costruzione dinamica di nome modulo o `getattr` su input
utente: il router risolve sempre attraverso `risolvi_handler`, che accetta
solo le chiavi presenti in `HANDLER`)."""

from __future__ import annotations

from typing import Protocol

from openpyxl.workbook import Workbook
from sqlalchemy.orm import Session

from app.schemas.admin_import import DiffRigaOut, RigaPiattaIn
from app.schemas.admin_upload import ScartoRowOut


class ImportHandler(Protocol):
    """Le tre operazioni che ogni risorsa importabile implementa. `diff` e
    `apply` risolvono autonomamente contro il database (nessuno stato
    condiviso fra le due chiamate, round-trip stateless): `apply` non si
    fida del diff calcolato in precedenza, ririsolve ogni riga.

    `ruolo_richiesto` (piano 08-07, T-08-62): `"admin"` o `"staff"`. Il
    router generico lo legge DOPO aver risolto la risorsa e PRIMA di
    leggere il file caricato — il permesso dell'import segue quello della
    pagina da cui si carica il file (D-26), mai un ruolo dichiarato dal
    client."""

    ruolo_richiesto: str

    def parse(self, wb: Workbook) -> tuple[list[RigaPiattaIn], list[ScartoRowOut]]: ...

    def diff(
        self, db: Session, righe: list[RigaPiattaIn]
    ) -> tuple[list[DiffRigaOut], list[DiffRigaOut], list[ScartoRowOut]]: ...

    def apply(
        self,
        db: Session,
        nuove: list[RigaPiattaIn],
        modificate: list[RigaPiattaIn],
        *,
        is_admin: bool,
    ) -> int: ...


class RisorsaImportSconosciuta(ValueError):
    """Risorsa nel path `{risorsa}` che non compare in `HANDLER` — il
    router la traduce in 404 con messaggio esplicito, mai un 500."""


HANDLER: dict[str, ImportHandler] = {}


def registra(risorsa: str, handler: ImportHandler) -> None:
    HANDLER[risorsa] = handler


def risolvi_handler(risorsa: str) -> ImportHandler:
    handler = HANDLER.get(risorsa)
    if handler is None:
        raise RisorsaImportSconosciuta(f"risorsa di import sconosciuta: {risorsa!r}")
    return handler
