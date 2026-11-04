"""pompa di calore: taglie per m2, radiatori esistenti, sistema ibrido, smontaggio caldaia

Seguito della 0033. Quattro cose:

  - TAGLIE: la fornitura della pompa (D.1.11, 8 kW) e il bollitore 200 l
    (D.1.12) diventano regole a scaglioni sui m2, con condizione
    `pompa_calore`. Le taglie 6 e 12 kW (D.1.14, D.1.15) e il bollitore
    300 l (D.1.16) li crea il seed;
  - RADIATORI ESISTENTI: con la pompa pura e senza radiatori nuovi ne'
    pavimento radiante, circa un radiatore su tre diventa un ventilradiatore
    (D.1.18, A.10.17 sulla grandezza `terminali_da_adeguare`, dal seed);
  - IBRIDO: opzione `ibrido` nelle due domande (dal seed). Accende la caldaia
    a gas (via `caldaia_nuova`) e il modulo pompa da 4 kW (D.1.17, A.10.16).
    Linea elettrica (A.8.23) e assistenza muraria (A.9.7) passano a
    `pdc_esterna` = pompa pura o ibrido;
  - SMONTAGGIO: A.1.17 passa a `generatore_nuovo`, cioe' vale anche per la
    caldaia a gas.

Come la 0033: si scrive SOLO dove il valore e' ancora quello del seed
precedente, mai DELETE. Gli scaglioni di D.1.11 e D.1.12 si inseriscono solo
se la voce non ne ha; in downgrade restano, inerti su una regola `grandezza`.

Su un DB vuoto non fa nulla: il seed crea tutto gia' nella forma nuova.

Revision ID: 0034
Revises: 0033
Create Date: 2026-11-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0034'
down_revision: Union[str, Sequence[str], None] = '0033'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NOTA_0033 = "Pompa di calore: prezzi da indagine di mercato 2026, da tarare su preventivi reali."
_MERCATO = "Prezzi da indagine di mercato 2026, da tarare su preventivi reali."

# (tabella, chiave WHERE, colonna, valore prima, valore dopo)
_CAMPI: tuple[tuple[str, dict, str, str | None, str | None], ...] = (
    ("domanda", {"code": "interv_caldaia"}, "help",
     "La caldaia a gas comprende fornitura, posa e allaccio gas. La pompa di calore "
     "comprende macchina esterna, bollitore per l'acqua calda, posa, linea elettrica "
     "e smontaggio della vecchia caldaia.",
     "La caldaia a gas comprende fornitura, posa e allaccio gas. La pompa di calore "
     "comprende macchina esterna dimensionata sui metri quadri, bollitore, posa, linea "
     "elettrica e smontaggio della vecchia caldaia. Il sistema ibrido affianca una piccola "
     "pompa di calore a una caldaia nuova."),
    ("opzione_domanda", {"domanda_code": "interv_caldaia", "code": "pompa_calore"}, "descrizione",
     "Aria-acqua, al posto della caldaia a gas, con bollitore per l'acqua calda.",
     "Aria-acqua, al posto della caldaia a gas, con bollitore per l'acqua calda. "
     "Con i radiatori esistenti include l'adeguamento di alcuni terminali."),
    ("grandezza", {"code": "caldaia_nuova"}, "descrizione",
     "Da 'Cambi caldaia o pompa di calore?' (caldaia a condensazione) o "
     "dall'efficientamento 'caldaia a condensazione'.",
     "Da 'Cambi caldaia o pompa di calore?' (caldaia a condensazione o sistema ibrido) o "
     "dall'efficientamento (caldaia a condensazione o sistema ibrido)."),
)

# voce -> (regola prima, regola dopo, nota prima, nota dopo)
_REGOLE: tuple[tuple[str, dict, dict, str, str], ...] = (
    ("A.1.17",
     {"grandezza_code": "pompa_calore"}, {"grandezza_code": "generatore_nuovo"},
     _NOTA_0033, "Smontaggio della vecchia caldaia con ogni generatore nuovo (gas, ibrido o pompa)."),
    ("A.8.23",
     {"grandezza_code": "pompa_calore"}, {"grandezza_code": "pdc_esterna"},
     _NOTA_0033, "Pompa di calore pura o sistema ibrido. " + _MERCATO),
    ("A.9.7",
     {"grandezza_code": "pompa_calore"}, {"grandezza_code": "pdc_esterna"},
     _NOTA_0033, "Pompa di calore pura o sistema ibrido. " + _MERCATO),
    ("D.1.11",
     {"tipo_regola": "grandezza", "grandezza_code": "pompa_calore", "condizione_grandezza_code": None},
     {"tipo_regola": "scaglioni", "grandezza_code": "mq", "condizione_grandezza_code": "pompa_calore"},
     _NOTA_0033, "Taglia 8 kW: da 81 a 120 m². " + _MERCATO),
    ("D.1.12",
     {"tipo_regola": "grandezza", "grandezza_code": "pompa_calore", "condizione_grandezza_code": None},
     {"tipo_regola": "scaglioni", "grandezza_code": "mq", "condizione_grandezza_code": "pompa_calore"},
     _NOTA_0033, "Bollitore 200 l fino a 120 m². " + _MERCATO),
)

# voce -> scaglioni (fino_a, valore), inseriti solo se la voce non ne ha.
_SCAGLIONI: dict[str, tuple[tuple[str | None, str], ...]] = {
    "D.1.11": (("80", "0"), ("120", "1"), (None, "0")),
    "D.1.12": (("120", "1"), (None, "0")),
}


def _cond(colonna: str, valore: str | None, nome: str) -> tuple[str, dict]:
    if valore is None:
        return f"{colonna} IS NULL", {}
    return f"{colonna} = :{nome}", {nome: valore}


def _aggiorna(da: int, a: int) -> None:
    bind = op.get_bind()

    for tabella, chiave, colonna, *valori in _CAMPI:
        condizioni = [f"{k} = :k_{k}" for k in chiave]
        params = {f"k_{k}": v for k, v in chiave.items()}
        c, p = _cond(colonna, valori[da], "vecchio")
        condizioni.append(c)
        params.update(p)
        params["nuovo"] = valori[a]
        bind.execute(
            sa.text(
                f"UPDATE {tabella} SET {colonna} = :nuovo, updated_at = CURRENT_TIMESTAMP"
                f" WHERE {' AND '.join(condizioni)}"
            ),
            params,
        )

    for voce, *valori in _REGOLE:
        vecchi, nuovi, nota_vecchia, nota_nuova = valori[da], valori[a], valori[2 + da], valori[2 + a]
        condizioni, params = ["voce_codice = :voce"], {"voce": voce}
        for i, (colonna, valore) in enumerate(vecchi.items()):
            c, p = _cond(colonna, valore, f"v{i}")
            condizioni.append(c)
            params.update(p)
        assegnazioni = []
        for i, (colonna, valore) in enumerate(nuovi.items()):
            assegnazioni.append(f"{colonna} = :n{i}")
            params[f"n{i}"] = valore
        bind.execute(
            sa.text(
                f"UPDATE regola_voce SET {', '.join(assegnazioni)}, updated_at = CURRENT_TIMESTAMP"
                f" WHERE {' AND '.join(condizioni)}"
            ),
            params,
        )
        bind.execute(
            sa.text(
                "UPDATE regola_voce SET nota = :nuova, updated_at = CURRENT_TIMESTAMP"
                " WHERE voce_codice = :voce AND nota = :vecchia"
            ),
            {"voce": voce, "nuova": nota_nuova, "vecchia": nota_vecchia},
        )

    if a == 1:
        for voce, scaglioni in _SCAGLIONI.items():
            regola = bind.execute(
                sa.text("SELECT tipo_regola FROM regola_voce WHERE voce_codice = :voce"),
                {"voce": voce},
            ).scalar_one_or_none()
            if regola != "scaglioni":
                continue  # regola assente o curata diversamente: non si tocca
            esistenti = bind.execute(
                sa.text("SELECT COUNT(*) FROM scaglione_regola WHERE voce_codice = :voce"),
                {"voce": voce},
            ).scalar_one()
            if esistenti:
                continue
            for fino_a, valore in scaglioni:
                bind.execute(
                    sa.text(
                        "INSERT INTO scaglione_regola (voce_codice, fino_a, valore)"
                        " VALUES (:voce, CAST(:fino_a AS NUMERIC), CAST(:valore AS NUMERIC))"
                    ),
                    {"voce": voce, "fino_a": fino_a, "valore": valore},
                )


def upgrade() -> None:
    _aggiorna(0, 1)


def downgrade() -> None:
    _aggiorna(1, 0)
