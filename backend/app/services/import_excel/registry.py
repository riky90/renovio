"""Registro degli handler di import generico per risorsa (piano 08-06).

`HANDLER` e' l'UNICO punto di estensione: una risorsa nuova (08-07, 08-08)
aggiunge una voce a questa mappa via `registra()`, mai una route nuova
(T-08-52 — nessuna costruzione dinamica di nome modulo o `getattr` su input
utente: il router risolve sempre attraverso `risolvi_handler`, che accetta
solo le chiavi presenti in `HANDLER`)."""

from __future__ import annotations

from datetime import datetime, timezone
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
        self, db: Session, righe: list[RigaPiattaIn], generato_il: datetime | None = None
    ) -> tuple[list[DiffRigaOut], list[DiffRigaOut], list[ScartoRowOut]]: ...

    def apply(
        self,
        db: Session,
        nuove: list[RigaPiattaIn],
        modificate: list[RigaPiattaIn],
        *,
        is_admin: bool,
    ) -> int: ...


def campi_nulli_in_valori(r: RigaPiattaIn) -> list[str]:
    """I nomi-campo che arrivano con valore `None` dentro `valori`.

    Per contratto (vedi docstring di `schemas/admin_import.py`) `valori`
    porta SOLO valori reali: una cancellazione viaggia su
    `campi_da_cancellare`, ed e' quella la struttura su cui i resolver
    distinguono "cancella il campo" da "scrivi questo valore". Un `None`
    dentro `valori` non puo' quindi venire da `parse()` — che i `None` li
    sposta sempre su `campi_da_cancellare` — ma solo da un client che
    ricostruisce male il payload di `/confirm`.

    Difesa in profondita' (CR-02): finche' nessuno controllava, un `None`
    che raggiungeva un ramo a stringa dei resolver veniva stringificato
    (`str(None) == "None"`) e la stringa letterale `"None"` finiva a
    database al posto di NULL. Meglio uno scarto descritto: un bug del
    client non deve mai poter corrompere un campo in silenzio.
    """
    return sorted(campo for campo, valore in r.valori.items() if valore is None)


def riga_modificata_dopo_export(esistente: object | None, generato_il: datetime | None) -> bool:
    """D-11: True se `esistente.updated_at` e' successivo a `generato_il`.

    T-08-71: nessuna eccezione su timestamp assente o malformato — `None`
    (da `esistente` o `generato_il`) produce sempre `False`, mai un 500;
    l'assenza di informazione non si trasforma in un allarme.
    T-08-72: legge `updated_at` dall'oggetto ORM gia' caricato dal resolver
    per il diff — nessuna query aggiuntiva per riga.

    Confronto naive->aware (stesso pattern di `dependencies/auth.py`):
    SQLite puo' restituire `updated_at` come naive anche se scritto da
    `server_default=func.now()`/`onupdate=func.now()`; qui si assume UTC,
    coerente con `leggi_timestamp_export` che scrive sempre in UTC-aware.
    """
    if esistente is None or generato_il is None:
        return False
    upd = getattr(esistente, "updated_at", None)
    if upd is None:
        return False
    if upd.tzinfo is None:
        upd = upd.replace(tzinfo=timezone.utc)
    gen = generato_il if generato_il.tzinfo is not None else generato_il.replace(tzinfo=timezone.utc)
    return upd > gen


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
