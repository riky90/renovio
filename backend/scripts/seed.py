"""Idempotent seed: loads `docs/seed-coefficienti-base.json` into the DB.

Upserts by natural key so re-running never duplicates rows:
  listino by nome, categoria by code, listino_categoria by
  (listino_id, categoria_code), tipo_ristrutturazione by code,
  moltiplicatore by (tipo_code, categoria_code), extra by code,
  comune_listino by comune_slug.

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
from app.models.listino import Listino, ListinoCategoria  # noqa: E402

# docs/ lives at the project root, two levels above this file (backend/scripts/).
SEED_JSON_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "seed-coefficienti-base.json"

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


def _dec(value: int | float | str) -> Decimal:
    return Decimal(str(value))


def load_seed_data(path: Path = SEED_JSON_PATH) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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

    session.commit()
    return listino


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        listino = seed(session)
        print(f"Seed completato: listino '{listino.nome}' (is_default={listino.is_default}).")


if __name__ == "__main__":
    main()
