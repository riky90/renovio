"""Export dei parametri del motore (CUR-03, D-08): un solo file a cinque
fogli — moltiplicatori, base €/m² + IVA per categoria, extra, coefficienti
Pro, forfait arredo. Di default il file NON è sensibile: nessuna colonna di
margine, quindi nessun foglio AVVISO necessario e nessun rischio se
l'allegato gira. `coefficiente_impresa` esiste SOLO nel ramo opt-in
`con_margine=True` — la colonna si aggiunge alla lista, non si filtra a
valle da una lista che già la conterrebbe (regola di dominio #1,
`CLAUDE.md`): se il ramo di default non conosce mai quel valore, nessuna
dimenticanza a valle può farlo uscire.

Le colonne `listino_nome`/`voce_descrizione`/`opzione_etichetta` sono
contesto in sola lettura per rendere il foglio curabile a occhio: il
re-import (08-06) le ignora.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.arredo import ForfaitArredo
from app.models.catalogo import Categoria, Extra, Moltiplicatore
from app.models.dettaglio_pro import CoefficienteQuantitaVoce, Voce
from app.models.domanda import OpzioneDomanda
from app.models.listino import Listino, ListinoCategoria
from app.services.export_excel.workbook import nuovo_workbook, scrivi_foglio_dati, serializza

COLONNE_MOLTIPLICATORI = ["id", "tipo_code", "categoria_code", "valore"]

COLONNE_LISTINO_CATEGORIA_BASE = [
    "id",
    "listino_id",
    "listino_nome",
    "categoria_code",
    "base_eur_mq",
    "iva_pct",
]
COLONNA_MARGINE = "coefficiente_impresa"

COLONNE_EXTRA = ["id", "nome", "importo", "iva_pct", "tipo_calcolo", "attivo"]

COLONNE_COEFF_PRO = [
    "id",
    "voce_id",
    "voce_descrizione",
    "tipo_code",
    "coefficiente_qta_per_mq",
    "domanda_mirata_key",
    "default_conteggio",
]

COLONNE_FORFAIT_ARREDO = [
    "id",
    "opzione_id",
    "opzione_etichetta",
    "livello_code",
    "eur_min",
    "eur_max",
    "attivo",
]


def _righe_moltiplicatori(db: Session) -> list[dict]:
    rows = db.query(Moltiplicatore).order_by(Moltiplicatore.id).all()
    return [
        {
            "id": r.id,
            "tipo_code": r.tipo_code,
            "categoria_code": r.categoria_code,
            "valore": r.valore,
        }
        for r in rows
    ]


def _righe_listino_categoria(db: Session, *, con_margine: bool) -> list[dict]:
    rows = (
        db.query(ListinoCategoria, Listino, Categoria)
        .join(Listino, ListinoCategoria.listino_id == Listino.id)
        .join(Categoria, ListinoCategoria.categoria_code == Categoria.code)
        .order_by(ListinoCategoria.listino_id, ListinoCategoria.id)
        .all()
    )
    righe = []
    for lc, listino, categoria in rows:
        riga = {
            "id": lc.id,
            "listino_id": lc.listino_id,
            "listino_nome": listino.nome,
            "categoria_code": lc.categoria_code,
            "base_eur_mq": lc.base_eur_mq,
            "iva_pct": categoria.iva_pct,
        }
        if con_margine:
            riga[COLONNA_MARGINE] = lc.coefficiente_impresa
        righe.append(riga)
    return righe


def _righe_extra(db: Session) -> list[dict]:
    rows = db.query(Extra).order_by(Extra.code).all()
    return [
        {
            "id": r.code,
            "nome": r.nome,
            "importo": r.importo,
            "iva_pct": r.iva_pct,
            "tipo_calcolo": r.tipo_calcolo,
            "attivo": r.attivo,
        }
        for r in rows
    ]


def _righe_coeff_pro(db: Session) -> list[dict]:
    rows = (
        db.query(CoefficienteQuantitaVoce, Voce)
        .join(Voce, CoefficienteQuantitaVoce.voce_id == Voce.id)
        .order_by(CoefficienteQuantitaVoce.id)
        .all()
    )
    return [
        {
            "id": c.id,
            "voce_id": c.voce_id,
            "voce_descrizione": voce.descrizione,
            "tipo_code": c.tipo_code,
            "coefficiente_qta_per_mq": c.coefficiente_qta_per_mq,
            "domanda_mirata_key": c.domanda_mirata_key,
            "default_conteggio": c.default_conteggio,
        }
        for c, voce in rows
    ]


def _righe_forfait_arredo(db: Session) -> list[dict]:
    rows = (
        db.query(ForfaitArredo, OpzioneDomanda)
        .join(OpzioneDomanda, ForfaitArredo.opzione_id == OpzioneDomanda.id)
        .order_by(ForfaitArredo.id)
        .all()
    )
    return [
        {
            "id": f.id,
            "opzione_id": f.opzione_id,
            "opzione_etichetta": opzione.etichetta,
            "livello_code": f.livello_code,
            "eur_min": f.eur_min,
            "eur_max": f.eur_max,
            "attivo": f.attivo,
        }
        for f, opzione in rows
    ]


def build_workbook_parametri(db: Session, *, con_margine: bool = False) -> tuple[bytes, int]:
    """Costruisce il workbook a cinque fogli dei parametri del motore.

    `con_margine=False` (default): la colonna `coefficiente_impresa` non
    esiste nel foglio `listino_categoria` e non c'è foglio `AVVISO` — il
    file non è sensibile. `con_margine=True`: la colonna si aggiunge e il
    foglio `AVVISO` compare in prima posizione (`nuovo_workbook`).

    Ritorna (bytes del file, numero totale di righe dati scritte sui
    cinque fogli) — il totale alimenta la riga di audit `export_log`.
    """
    wb = nuovo_workbook(con_margine=con_margine)

    colonne_listino_categoria = list(COLONNE_LISTINO_CATEGORIA_BASE)
    if con_margine:
        colonne_listino_categoria.append(COLONNA_MARGINE)

    n_righe = 0
    n_righe += scrivi_foglio_dati(
        wb, nome="moltiplicatori", colonne=COLONNE_MOLTIPLICATORI, righe=_righe_moltiplicatori(db)
    )
    n_righe += scrivi_foglio_dati(
        wb,
        nome="listino_categoria",
        colonne=colonne_listino_categoria,
        righe=_righe_listino_categoria(db, con_margine=con_margine),
    )
    n_righe += scrivi_foglio_dati(wb, nome="extra", colonne=COLONNE_EXTRA, righe=_righe_extra(db))
    n_righe += scrivi_foglio_dati(
        wb, nome="coefficienti_pro", colonne=COLONNE_COEFF_PRO, righe=_righe_coeff_pro(db)
    )
    n_righe += scrivi_foglio_dati(
        wb, nome="forfait_arredo", colonne=COLONNE_FORFAIT_ARREDO, righe=_righe_forfait_arredo(db)
    )

    return serializza(wb), n_righe
