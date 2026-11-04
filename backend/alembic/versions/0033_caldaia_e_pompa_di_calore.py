"""caldaia e pompa di calore separate

Fino alla 0032 "caldaia" e "pompa di calore" erano la stessa risposta: tutte e
due accendevano `caldaia_nuova`, cioe' le tre voci della caldaia a GAS (A.8.8
allaccio gas, A.10.3 posa, D.1.7 fornitura). Chi sceglieva la pompa di calore
riceveva il prezzo di una caldaia a gas.

Ora sono due cose diverse:

  - `interv_caldaia` diventa una scelta singola "Cambi caldaia o pompa di
    calore?" (no / caldaia a condensazione / pompa di calore). Il codice `si`
    resta quello della caldaia, cosi' preset, valori e risposte salvate non
    cambiano significato;
  - `interventi_efficientamento.cambio_caldaia` diventa "Caldaia a
    condensazione", e accanto nasce l'opzione `pompa_calore`;
  - la grandezza nuova `pompa_calore` accende le voci della pompa (A.1.17,
    A.8.23, A.8.24, A.9.7, A.10.14, A.10.15, D.1.11-13);
  - le tre voci del gas passano da `caldaia_nuova` a `caldaia_gas` =
    caldaia_nuova - pompa_calore (minimo 0): la pompa sostituisce la caldaia,
    anche quando il preset della ristrutturazione totale dice "caldaia".

Opzioni, voci, grandezze, regole e valori nuovi li crea il seed al boot
(create-if-missing). Questa migrazione cambia solo le righe che esistono gia',
e SOLO dove il valore e' ancora quello del seed precedente: cio' che l'admin ha
gia' cambiato dal pannello non si tocca. Le tre regole puntano a `caldaia_gas`
prima che il seed la crei: nell'intervallo vale 0, come una regola spenta.

Su un DB vuoto non fa nulla: il seed crea il catalogo gia' nella forma nuova.

Revision ID: 0033
Revises: 0032
Create Date: 2026-11-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0033'
down_revision: Union[str, Sequence[str], None] = '0032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (tabella, chiave WHERE, colonna, valore prima, valore dopo)
_CAMPI: tuple[tuple[str, dict, str, str | None, str | None], ...] = (
    ("domanda", {"code": "interv_caldaia"}, "testo",
     "Sostituisci la caldaia?", "Cambi caldaia o pompa di calore?"),
    ("domanda", {"code": "interv_caldaia"}, "tipo_controllo", "toggle", "scelta_singola"),
    ("domanda", {"code": "interv_caldaia"}, "help",
     "Fornitura, posa e allaccio gas della caldaia.",
     "La caldaia a gas comprende fornitura, posa e allaccio gas. La pompa di calore "
     "comprende macchina esterna, bollitore per l'acqua calda, posa, linea elettrica "
     "e smontaggio della vecchia caldaia."),
    ("opzione_domanda", {"domanda_code": "interv_caldaia", "code": "si"}, "etichetta",
     "Sì", "Caldaia a condensazione"),
    ("opzione_domanda", {"domanda_code": "interv_caldaia", "code": "si"}, "descrizione",
     None, "Caldaia a gas nuova al posto della vecchia."),
    ("opzione_domanda", {"domanda_code": "interventi_efficientamento", "code": "cambio_caldaia"},
     "etichetta", "Cambio caldaia o pompa di calore", "Caldaia a condensazione"),
    ("opzione_domanda", {"domanda_code": "interventi_efficientamento", "code": "cambio_caldaia"},
     "descrizione",
     "Costo una tantum: una caldaia costa quel che costa, non 45 euro al metro quadro.",
     "Caldaia a gas nuova. Costo una tantum, non proporzionale ai metri quadri."),
    ("grandezza", {"code": "caldaia_nuova"}, "descrizione",
     "Da 'Sostituisci la caldaia?' o dall'efficientamento 'cambio caldaia'.",
     "Da 'Cambi caldaia o pompa di calore?' (caldaia a condensazione) o "
     "dall'efficientamento 'caldaia a condensazione'."),
    *(
        ("regola_voce", {"voce_codice": voce}, "grandezza_code", "caldaia_nuova", "caldaia_gas")
        for voce in ("A.8.8", "A.10.3", "D.1.7")
    ),
)


def _aggiorna(da: int, a: int) -> None:
    bind = op.get_bind()
    for tabella, chiave, colonna, *valori in _CAMPI:
        vecchio, nuovo = valori[da], valori[a]
        condizioni = [f"{k} = :k_{k}" for k in chiave]
        params = {f"k_{k}": v for k, v in chiave.items()}
        if vecchio is None:
            condizioni.append(f"{colonna} IS NULL")
        else:
            condizioni.append(f"{colonna} = :vecchio")
            params["vecchio"] = vecchio
        params["nuovo"] = nuovo
        bind.execute(
            sa.text(
                f"UPDATE {tabella} SET {colonna} = :nuovo, updated_at = CURRENT_TIMESTAMP"
                f" WHERE {' AND '.join(condizioni)}"
            ),
            params,
        )


def upgrade() -> None:
    _aggiorna(0, 1)


def downgrade() -> None:
    # Le righe nuove create dal seed (opzioni `pompa_calore`, voci, grandezze,
    # regole) restano: mai DELETE di curatela. Senza le etichette e le regole
    # nuove tornano solo inerti.
    _aggiorna(1, 0)
