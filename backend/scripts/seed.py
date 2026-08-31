"""Idempotent seed: loads `docs/seed-coefficienti-base.json` (+ 03-02:
`docs/seed-dettaglio-pro.json`) into the DB.

Upserts by natural key so re-running never duplicates rows:
  listino by nome, categoria by code, listino_categoria by
  (listino_id, categoria_code), tipo_ristrutturazione by code,
  moltiplicatore by (tipo_code, categoria_code), extra by code,
  comune_listino by comune_slug, sottocategoria by
  (listino_id, categoria_code, codice-o-nome), voce by
  (sottocategoria_id, codice-o-descrizione), coefficiente_qta_voce by
  (voce_id, tipo_code).

Dettaglio Pro esteso nella STESSA funzione `seed()` (D-03/D-12/Pitfall 5):
mai un secondo script di seed, per non lasciare il DB a meta' seminato dopo
un reset locale.

Run: `uv run python scripts/seed.py` (from backend/).
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

from slugify import slugify
from sqlalchemy.orm import Session

# Allow `python scripts/seed.py` direct execution (not just `-m scripts.seed`):
# ensure backend/ (parent of scripts/) is importable as the `app` package root.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import app.models  # noqa: E402, F401 - registers all ORM entities on Base.metadata
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models.catalogo import Categoria, ComuneListino, Extra, Moltiplicatore, TipoRistrutturazione  # noqa: E402
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Sottocategoria, Voce  # noqa: E402
from app.models.listino import Listino, ListinoCategoria  # noqa: E402
from app.models.testo import Testo  # noqa: E402

# I dati seed vivono in DUE posizioni possibili:
#  1) backend/seed_data/ — copia inclusa nell'immagine Docker (build context =
#     backend/, quindi docs/ alla root del repo NON e' raggiungibile in prod);
#  2) docs/ alla root del repo — sorgente storica usata in dev locale.
# Si preferisce la copia backend-local (prod) con fallback a docs/ (dev).
def _resolve_seed(filename: str) -> Path:
    local = _BACKEND_DIR / "seed_data" / filename
    if local.exists():
        return local
    return _BACKEND_DIR.parent / "docs" / filename


SEED_JSON_PATH = _resolve_seed("seed-coefficienti-base.json")
# Dati dettaglio Pro (03-02, D-03): stesso listino RE, estensione dello stesso seed idempotente.
SEED_DETTAGLIO_PRO_JSON_PATH = _resolve_seed("seed-dettaglio-pro.json")

CATEGORIA_NOMI = {
    "A-EDILE": "Edile",
    "B-FINITURE": "Finiture",
    "C-SERRAMENTI": "Serramenti/Porte",
    "D-PRODOTTI": "Prodotti",
}
CATEGORIA_ORDINE = {"A-EDILE": 1, "B-FINITURE": 2, "C-SERRAMENTI": 3, "D-PRODOTTI": 4}

# Internal margin coefficient per category (foglio `listini` del computo).
# SEGRETO server-side: mai esposto al client (D-11 / CLAUDE.md). Mappatura
# fissata in 01-RESEARCH.md Open Question 1 (A1): A->0.65, B->0.6, C->0.55, D->0.5.
COEFFICIENTE_IMPRESA = {
    "A-EDILE": Decimal("0.65"),
    "B-FINITURE": Decimal("0.6"),
    "C-SERRAMENTI": Decimal("0.55"),
    "D-PRODOTTI": Decimal("0.5"),
}

TIPO_NOMI = {"leggera": "Leggera", "moderata": "Moderata", "totale": "Totale"}
TIPO_ORDINE = {"leggera": 1, "moderata": 2, "totale": 3}

EXTRA_NOMI = {"CSE_CSP": "CSE/CSP", "pratiche": "Pratiche amministrative"}
# Provisional default (D-12 / A3), admin-editable in a later phase.
EXTRA_IVA_PCT = Decimal("0.22")

# RE aliases the free-text city input must resolve without fallback (D-06/D-07,
# Pitfall 6). "Reggio Emilia" also covers case-insensitive variants (slugify
# lowercases); "Reggio nell'Emilia" is a distinct slug and needs its own row.
RE_ALIASES = ["Reggio Emilia", "Reggio nell'Emilia"]

# Testi/disclaimer iniziali (D-14): valori identici agli hardcoded attuali,
# migrati in tabella Testo. Scope v1 SOLO backend-owned (04-RESEARCH.md Open
# Question 1) — nessuna chiave per il fallback referente D-05 (Pitfall 5).
TESTI_INIZIALI = {
    "disclaimer_fallback_citta": (
        "Stima basata sul listino di Reggio Emilia, non ancora tarata su {citta}."
    ),
    "email_conferma_lead_subject": "Conferma richiesta contatto professionista",
}


def _dec(value: int | float | str) -> Decimal:
    return Decimal(str(value))


def load_seed_data(path: Path = SEED_JSON_PATH) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_dettaglio_pro_data(path: Path = SEED_DETTAGLIO_PRO_JSON_PATH) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _upsert_sottocategoria(session: Session, listino: Listino, sotto_data: dict) -> Sottocategoria:
    """Upsert idempotente per chiave naturale (listino_id, categoria_code,
    codice-o-nome — D-03/Pitfall 1: codice nullable per B/C/D)."""
    categoria_code = sotto_data["categoria_code"]
    codice = sotto_data.get("codice")
    nome = sotto_data["nome"]
    query = session.query(Sottocategoria).filter_by(listino_id=listino.id, categoria_code=categoria_code)
    query = query.filter_by(codice=codice) if codice is not None else query.filter_by(codice=None, nome=nome)
    sotto = query.one_or_none()
    if sotto is None:
        sotto = Sottocategoria(
            listino_id=listino.id,
            categoria_code=categoria_code,
            codice=codice,
            nome=nome,
            famiglia=sotto_data["famiglia"],
            ordine=sotto_data.get("ordine", 0),
        )
        session.add(sotto)
        session.flush()
    else:
        sotto.nome = nome
        sotto.famiglia = sotto_data["famiglia"]
        sotto.ordine = sotto_data.get("ordine", 0)
    return sotto


def _upsert_voce(session: Session, sotto: Sottocategoria, voce_data: dict) -> Voce:
    """Upsert per chiave naturale (sottocategoria_id, codice-o-descrizione)."""
    codice = voce_data.get("codice")
    descrizione = voce_data["descrizione"]
    query = session.query(Voce).filter_by(sottocategoria_id=sotto.id)
    query = query.filter_by(codice=codice) if codice is not None else query.filter_by(codice=None, descrizione=descrizione)
    voce = query.one_or_none()
    if voce is None:
        voce = Voce(
            sottocategoria_id=sotto.id,
            codice=codice,
            descrizione=descrizione,
            um=voce_data["um"],
            prezzo_unitario_cliente=_dec(voce_data["prezzo_unitario_cliente"]),
            ordine=voce_data.get("ordine", 0),
        )
        session.add(voce)
        session.flush()
    else:
        voce.descrizione = descrizione
        voce.um = voce_data["um"]
        voce.prezzo_unitario_cliente = _dec(voce_data["prezzo_unitario_cliente"])
        voce.ordine = voce_data.get("ordine", 0)
    return voce


def _upsert_coefficiente_qta(session: Session, voce: Voce, tipo_code: str, coeff_data: dict) -> None:
    """Upsert per chiave naturale (voce_id, tipo_code)."""
    coeff = session.query(CoefficienteQuantitaVoce).filter_by(voce_id=voce.id, tipo_code=tipo_code).one_or_none()
    coefficiente_qta_per_mq = coeff_data.get("coefficiente_qta_per_mq")
    domanda_mirata_key = coeff_data.get("domanda_mirata_key")
    default_conteggio = coeff_data.get("default_conteggio")
    if coeff is None:
        coeff = CoefficienteQuantitaVoce(
            voce_id=voce.id,
            tipo_code=tipo_code,
            coefficiente_qta_per_mq=_dec(coefficiente_qta_per_mq) if coefficiente_qta_per_mq is not None else None,
            domanda_mirata_key=domanda_mirata_key,
            default_conteggio=default_conteggio,
        )
        session.add(coeff)
    else:
        coeff.coefficiente_qta_per_mq = _dec(coefficiente_qta_per_mq) if coefficiente_qta_per_mq is not None else None
        coeff.domanda_mirata_key = domanda_mirata_key
        coeff.default_conteggio = default_conteggio


def seed_dettaglio_pro(session: Session, listino: Listino, data: dict | None = None) -> None:
    """Idempotent upsert dei dati dettaglio Pro (sottocategoria/voce/
    coefficiente_qta_voce), stesso listino del seed Free (D-12: Free e Pro
    leggono lo STESSO listino per citta). Chiamata da `seed()` — NON un
    secondo script (D-12/Pitfall 5)."""
    data = data or load_dettaglio_pro_data()
    for sotto_data in data["sottocategorie"]:
        sotto = _upsert_sottocategoria(session, listino, sotto_data)
        session.flush()
        for voce_data in sotto_data["voci"]:
            voce = _upsert_voce(session, sotto, voce_data)
            session.flush()
            for tipo_code, coeff_data in voce_data.get("coefficienti", {}).items():
                _upsert_coefficiente_qta(session, voce, tipo_code, coeff_data)


def seed_testi(session: Session) -> None:
    """Idempotent upsert dei testi/disclaimer iniziali (D-14) nella tabella
    Testo, upsert per chiave naturale (`chiave` e' gia' la PK). Chiamata da
    `seed()` — STESSA funzione idempotente, non un secondo script
    (D-12/Pitfall 5)."""
    import datetime as _dt

    for chiave, valore in TESTI_INIZIALI.items():
        row = session.get(Testo, chiave)
        if row is None:
            row = Testo(chiave=chiave, valore=valore, updated_at=_dt.datetime.now(_dt.timezone.utc))
            session.add(row)
        else:
            row.valore = valore


def seed(session: Session, data: dict | None = None) -> Listino:
    """Idempotent upsert of the full RE dataset. Safe to call repeatedly."""
    data = data or load_seed_data()

    # 1. listino (RE, is_default=True)
    listino = session.query(Listino).filter_by(nome="Reggio Emilia").one_or_none()
    if listino is None:
        listino = Listino(
            nome="Reggio Emilia",
            citta_riferimento="Reggio Emilia",
            valuta=data.get("valuta", "EUR"),
        )
        session.add(listino)
        session.flush()
    listino.is_default = True
    listino.attivo = True

    # 2. categoria (4)
    for code, iva in data["iva_categoria"].items():
        cat = session.query(Categoria).filter_by(code=code).one_or_none()
        if cat is None:
            cat = Categoria(code=code, nome=CATEGORIA_NOMI[code], ordine=CATEGORIA_ORDINE[code], iva_pct=_dec(iva))
            session.add(cat)
        else:
            cat.nome = CATEGORIA_NOMI[code]
            cat.ordine = CATEGORIA_ORDINE[code]
            cat.iva_pct = _dec(iva)
    session.flush()

    # 3. listino_categoria (4): base_eur_mq (prezzo cliente) + coefficiente_impresa (segreto)
    for code, base in data["base_eur_mq"].items():
        lc = session.query(ListinoCategoria).filter_by(listino_id=listino.id, categoria_code=code).one_or_none()
        if lc is None:
            lc = ListinoCategoria(
                listino_id=listino.id,
                categoria_code=code,
                base_eur_mq=_dec(base),
                coefficiente_impresa=COEFFICIENTE_IMPRESA[code],
            )
            session.add(lc)
        else:
            lc.base_eur_mq = _dec(base)
            lc.coefficiente_impresa = COEFFICIENTE_IMPRESA[code]

    # 4. tipo_ristrutturazione (3)
    for code, range_pct in data["range_pct_tipo"].items():
        tipo = session.query(TipoRistrutturazione).filter_by(code=code).one_or_none()
        if tipo is None:
            tipo = TipoRistrutturazione(
                code=code, nome=TIPO_NOMI[code], ordine=TIPO_ORDINE[code], range_pct=_dec(range_pct)
            )
            session.add(tipo)
        else:
            tipo.nome = TIPO_NOMI[code]
            tipo.ordine = TIPO_ORDINE[code]
            tipo.range_pct = _dec(range_pct)
    session.flush()

    # 5. moltiplicatore (12 = 3 tipi x 4 categorie)
    for tipo_code, categorie in data["moltiplicatori_tipo"].items():
        for categoria_code, valore in categorie.items():
            m = (
                session.query(Moltiplicatore)
                .filter_by(tipo_code=tipo_code, categoria_code=categoria_code)
                .one_or_none()
            )
            if m is None:
                m = Moltiplicatore(tipo_code=tipo_code, categoria_code=categoria_code, valore=_dec(valore))
                session.add(m)
            else:
                m.valore = _dec(valore)

    # 6. extra (2: CSE_CSP, pratiche)
    for code, importo in data["extra"].items():
        extra = session.query(Extra).filter_by(code=code).one_or_none()
        if extra is None:
            extra = Extra(code=code, nome=EXTRA_NOMI.get(code, code), importo=_dec(importo), iva_pct=EXTRA_IVA_PCT)
            session.add(extra)
        else:
            extra.nome = EXTRA_NOMI.get(code, code)
            extra.importo = _dec(importo)
            extra.iva_pct = EXTRA_IVA_PCT

    # 7. comune_listino: RE aliases -> RE listino (Pitfall 6)
    for alias in RE_ALIASES:
        slug = slugify(alias)
        comune = session.query(ComuneListino).filter_by(comune_slug=slug).one_or_none()
        if comune is None:
            comune = ComuneListino(comune_nome=alias, comune_slug=slug, listino_id=listino.id)
            session.add(comune)
        else:
            comune.comune_nome = alias
            comune.listino_id = listino.id

    session.flush()

    # 8. dettaglio Pro (sottocategoria/voce/coefficiente_qta_voce) — stesso
    # listino RE, stessa funzione seed() idempotente (D-03/D-12/Pitfall 5).
    seed_dettaglio_pro(session, listino)

    # 9. testi/disclaimer (D-14) — stessa funzione seed() idempotente.
    seed_testi(session)

    session.commit()
    return listino


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        listino = seed(session)
        print(f"Seed completato: listino '{listino.nome}' (is_default={listino.is_default}).")


if __name__ == "__main__":
    main()
