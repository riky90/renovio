"""Export piatto dei lead (CUR-04, D-16): un foglio `lead`, una riga per
`Lead`, colonna `id` tecnica in testa, ordinate per `created_at`
decrescente (stessa lettura di default della dashboard admin).

Nessuna colonna di margine: `totale_min`/`totale_max` sono i prezzi
cliente gia' pubblici per l'utente che ha generato il lead (nessun
`coefficiente_impresa`/`base_eur_mq` esiste su `models/lead.py::Lead` per
costruzione, D-22).
"""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.services.export_excel.workbook import nuovo_workbook, scrivi_foglio_dati, serializza

COLONNE_LEAD = [
    "id",
    "created_at",
    "nome",
    "email",
    "telefono",
    "preferenza_contatto",
    "fascia_oraria",
    "messaggio",
    "citta",
    "mq",
    "tipo",
    "totale_min",
    "totale_max",
    "referente_id",
    "email_inviata",
    "stato",
    "nota",
]

_TESTO_CAMPI_MODIFICABILI = (
    "Del lead sono ricurabili dal re-import solo stato, nota e "
    "referente_id: i dati di contatto e i totali sono storia, non "
    "curatela."
)


def build_workbook_lead(db: Session) -> tuple[bytes, int]:
    """Legge tutti i `Lead` ordinati per `created_at` decrescente e scrive
    un unico foglio `lead`. Ritorna (bytes, numero di righe dati scritte)
    — il numero alimenta la riga di audit `export_log` nel router."""
    rows = db.query(Lead).order_by(desc(Lead.created_at)).all()

    righe = [
        {
            "id": lead.id,
            "created_at": lead.created_at.isoformat(),
            "nome": lead.nome,
            "email": lead.email,
            "telefono": lead.telefono,
            "preferenza_contatto": lead.preferenza_contatto,
            "fascia_oraria": lead.fascia_oraria,
            "messaggio": lead.messaggio,
            "citta": lead.citta,
            "mq": lead.mq,
            "tipo": lead.tipo,
            "totale_min": lead.totale_min,
            "totale_max": lead.totale_max,
            "referente_id": lead.referente_id,
            "email_inviata": lead.email_inviata,
            "stato": lead.stato,
            "nota": lead.nota,
        }
        for lead in rows
    ]

    wb = nuovo_workbook(con_margine=False)
    wb["ISTRUZIONI"]["A5"] = _TESTO_CAMPI_MODIFICABILI
    n_righe = scrivi_foglio_dati(wb, nome="lead", colonne=COLONNE_LEAD, righe=righe)
    return serializza(wb), n_righe
