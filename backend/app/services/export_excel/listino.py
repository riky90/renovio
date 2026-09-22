"""Export piatto del listino (D-01, D-03, D-12): un foglio `voci`, una riga
per `Voce`, colonna `id` tecnica in testa. Nessuna colonna di margine:
`Voce` non ne ha per costruzione (D-10, `models/dettaglio_pro.py`).

Le colonne includono deliberatamente `livello`, `um` e `ordine` — sono i tre
campi che il test di round-trip esistente (`test_dettaglio_pro_livelli.py`)
non copre, e il debito noto della v2 ("la curatela di `voce.livello` esiste
solo nel dev.db locale") si chiude solo se il file esportato le porta con se'.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.dettaglio_pro import Sottocategoria, Voce
from app.services.export_excel.workbook import nuovo_workbook, scrivi_foglio_dati, serializza

COLONNE_VOCI = [
    "id",
    "categoria_code",
    "sottocategoria_codice",
    "sottocategoria_nome",
    "sottocategoria_famiglia",
    "sottocategoria_ordine",
    "codice",
    "descrizione",
    "um",
    "prezzo_unitario_cliente",
    "ordine",
    "livello",
]


def build_workbook_listino(db: Session, listino_id: int) -> tuple[bytes, int]:
    """Legge le `Voce` del listino (join su `Sottocategoria`, stessa query
    di `compute_diff`) e scrive un unico foglio `voci`. Ritorna (bytes,
    numero di righe dati scritte) — il numero alimenta la riga di audit
    `export_log` nel router."""
    rows = (
        db.query(Voce, Sottocategoria)
        .join(Sottocategoria, Voce.sottocategoria_id == Sottocategoria.id)
        .filter(Sottocategoria.listino_id == listino_id)
        .order_by(Sottocategoria.ordine, Sottocategoria.id, Voce.ordine, Voce.id)
        .all()
    )

    righe = [
        {
            "id": voce.id,
            "categoria_code": sotto.categoria_code,
            "sottocategoria_codice": sotto.codice,
            "sottocategoria_nome": sotto.nome,
            "sottocategoria_famiglia": sotto.famiglia,
            "sottocategoria_ordine": sotto.ordine,
            "codice": voce.codice,
            "descrizione": voce.descrizione,
            "um": voce.um,
            "prezzo_unitario_cliente": voce.prezzo_unitario_cliente,
            "ordine": voce.ordine,
            "livello": voce.livello,
        }
        for voce, sotto in rows
    ]

    wb = nuovo_workbook(con_margine=False)
    n_righe = scrivi_foglio_dati(wb, nome="voci", colonne=COLONNE_VOCI, righe=righe)
    return serializza(wb), n_righe
