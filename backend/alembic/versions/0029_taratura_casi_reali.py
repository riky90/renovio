"""computo parametrico: taratura sui quattro computi reali (TAR-01)

Fase 11 (v3.0). Il confronto con i computi veri di `docs/casi-reali/` (report
in `.planning/prove/2026-11-taratura/`) cambia alcuni valori della bozza:

- tinteggiatura: il tecnico tinteggia pareti e soffitti con la sola A.11.3,
  circa 3,2 m² per m² calpestabile; la lavabile A.11.4 non compare mai; il
  fondo A.11.6 copre circa il 40% delle superfici; la rasatura e' circa 0,66
  m² per m² e non cresce con l'intonaco nuovo;
- battiscopa 0,65 ml per m² invece di 1,1;
- punti acqua 4 per bagno e 3 per la cucina invece di 5 e 2;
- A.0.11 (linee idriche, a corpo) una per cantiere, non una per bagno;
  impermeabilizzazione 4 m² per bagno invece di 6; sanitari montati 3 per
  bagno invece di 4;
- lampadari (A.10.11) e foro cappa (A.10.12) mai presenti: fattore 0.

Il seed v3 ha gia' i valori nuovi, ma grandezze, termini e regole sono
create-if-missing: sui DB gia' seminati serve questa migrazione. Si scrive
SOLO dove il valore e' ancora quello della bozza: una regola gia' cambiata dal
pannello admin (o dall'Excel del computo) non si tocca. Mai DELETE.

Su un DB vuoto non fa nulla.

Revision ID: 0029
Revises: 0028
Create Date: 2026-10-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0029'
down_revision: Union[str, Sequence[str], None] = '0028'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (grandezza, sorgente, fattore della bozza, fattore tarato)
_TERMINI: tuple[tuple[str, str, str, str], ...] = (
    ("mq_pareti", "superficie_calpestabile", "2.9", "2.2"),
    ("ml_battiscopa", "superficie_calpestabile", "1.1", "0.65"),
    ("punti_acqua", "bagni_rifatti", "5", "4"),
    ("punti_acqua", "cucina", "2", "3"),
    ("rasatura_mq", "intonaco_mq", "1", "0"),
)

# (grandezza, colonna, testo della bozza, testo tarato)
_TESTI_GRANDEZZE: tuple[tuple[str, str, str | None, str], ...] = (
    (
        "mq_pareti",
        "descrizione",
        "Superficie delle pareti: circa 2,9 m² per m² calpestabile (altezza 2,70).",
        "Pareti da tinteggiare, nette di rivestimenti e aperture: circa 2,2 m² per m² calpestabile "
        "(TAR-01: con 1 di soffitti fa 3,2 m² tinteggiati per m², mediana dei computi reali).",
    ),
    (
        "ml_battiscopa",
        "descrizione",
        "Perimetro dei locali, circa 1,1 ml per m².",
        "Battiscopa posato, circa 0,65 ml per m² calpestabile (TAR-01: 0,86 e 0,46 nei due "
        "appartamenti totali).",
    ),
    (
        "punti_acqua",
        "descrizione",
        "5 per bagno (lavabo, wc, bidet, doccia, lavatrice), 2 per la cucina.",
        "4 per bagno (lavabo, wc, bidet, doccia), 3 per la cucina (lavello, lavastoviglie, "
        "lavatrice). TAR-01: 15, 11 e 4 punti nei computi reali.",
    ),
    (
        "rasatura_mq",
        "descrizione",
        "30% delle pareti tinteggiate piu' tutto l'intonaco nuovo.",
        "30% delle pareti tinteggiate, circa 0,66 m² per m² calpestabile (TAR-01: 0,5-0,7 nei "
        "computi reali, anche con molti muri nuovi). Il termine sull'intonaco nuovo e' a 0.",
    ),
    ("superfici_fondo", "nome", "Superfici con fondo", "Superfici tinteggiate"),
    (
        "superfici_fondo",
        "descrizione",
        None,
        "Pareti e soffitti tinteggiati. Base della tinteggiatura (A.11.3) e del fondo (A.11.6).",
    ),
)

# voce -> (valori della bozza, valori tarati) sulle colonne numeriche e di
# riferimento della regola. Si aggiorna solo se TUTTE le colonne della bozza
# combaciano.
_REGOLE: tuple[tuple[str, dict, dict], ...] = (
    ("A.11.3", {"grandezza_code": "soffitti_tinteggiati"}, {"grandezza_code": "superfici_fondo"}),
    ("A.11.4", {"fattore": "1"}, {"fattore": "0"}),
    ("A.11.6", {"fattore": "1"}, {"fattore": "0.4"}),
    (
        "A.0.11",
        {"tipo_regola": "grandezza", "grandezza_code": "bagni_rifatti", "condizione_grandezza_code": None},
        {"tipo_regola": "fisso", "grandezza_code": None, "condizione_grandezza_code": "bagni_rifatti"},
    ),
    ("A.7.1", {"fattore": "6"}, {"fattore": "4"}),
    ("A.8.5", {"fattore": "4"}, {"fattore": "3"}),
    ("A.10.11", {"fattore": "1"}, {"fattore": "0"}),
    ("A.10.12", {"fattore": "1"}, {"fattore": "0"}),
)

# voce -> (nota della bozza, nota tarata)
_NOTE: tuple[tuple[str, str | None, str], ...] = (
    (
        "A.11.3",
        None,
        "TAR-01: nei computi reali il tecnico tinteggia pareti e soffitti con questa sola voce "
        "(in un caso la descrizione dice 'soffitti e pareti').",
    ),
    (
        "A.11.4",
        None,
        "TAR-01: lavabile su pareti mai usata nei computi reali (le pareti sono in A.11.3). Da "
        "riattivare con una domanda Pro sul tipo di pittura.",
    ),
    (
        "A.11.6",
        None,
        "TAR-01: fondo su circa il 40% delle superfici tinteggiate (150 m² su 140 m² di pavimento, "
        "400 su 195; assente nei lavori parziali).",
    ),
    (
        "A.0.11",
        "Una linea per bagno da rifare (nota H).",
        "Voce a corpo: una per cantiere se si rifa' almeno un bagno (TAR-01: 300 EUR a corpo per "
        "due bagni).",
    ),
    (
        "A.7.1",
        "6 m² per bagno; a corpo 200 € se pochi metri (nota H).",
        "4 m² per bagno, minimo 200 EUR a corpo (TAR-01: 450 EUR per tre bagni, 200 per uno).",
    ),
    ("A.8.5", "Quattro apparecchi per bagno.", "TAR-01: 10 apparecchi per tre bagni, 6 per due."),
    (
        "A.10.11",
        None,
        "TAR-01: mai presente nei computi reali, anche con l'elettrico rifatto. Da riattivare con "
        "una domanda Pro.",
    ),
    (
        "A.10.12",
        "Foro per la cappa.",
        "TAR-01: assente in tre cucine rifatte su tre; c'e' solo con un bagno cieco. Da legare "
        "alla domanda 'bagni ciechi' quando ci sara'.",
    ),
)


def _uguale(colonna: str, valore: str | None, nome_param: str) -> tuple[str, dict]:
    if valore is None:
        return f"{colonna} IS NULL", {}
    if colonna == "fattore":
        return f"{colonna} = CAST(:{nome_param} AS NUMERIC)", {nome_param: valore}
    return f"{colonna} = :{nome_param}", {nome_param: valore}


def _aggiorna(da: int, a: int) -> None:
    bind = op.get_bind()

    for grandezza, sorgente, *fattori in _TERMINI:
        bind.execute(
            sa.text(
                "UPDATE termine_grandezza SET fattore = CAST(:nuovo AS NUMERIC),"
                " updated_at = CURRENT_TIMESTAMP"
                " WHERE grandezza_code = :g AND sorgente_code = :s"
                " AND per_grandezza_code IS NULL AND fattore = CAST(:vecchio AS NUMERIC)"
            ),
            {"g": grandezza, "s": sorgente, "vecchio": fattori[da], "nuovo": fattori[a]},
        )

    for grandezza, colonna, *testi in _TESTI_GRANDEZZE:
        condizione, params = _uguale(colonna, testi[da], "vecchio")
        bind.execute(
            sa.text(
                f"UPDATE grandezza SET {colonna} = :nuovo, updated_at = CURRENT_TIMESTAMP"
                f" WHERE code = :g AND {condizione}"
            ),
            {"g": grandezza, "nuovo": testi[a], **params},
        )

    for voce, *valori in _REGOLE:
        vecchi, nuovi = valori[da], valori[a]
        condizioni, params = [], {"voce": voce}
        for i, (colonna, valore) in enumerate(vecchi.items()):
            cond, p = _uguale(colonna, valore, f"v{i}")
            condizioni.append(cond)
            params.update(p)
        assegnazioni = []
        for i, (colonna, valore) in enumerate(nuovi.items()):
            if colonna == "fattore":
                assegnazioni.append(f"{colonna} = CAST(:n{i} AS NUMERIC)")
            else:
                assegnazioni.append(f"{colonna} = :n{i}")
            params[f"n{i}"] = valore
        bind.execute(
            sa.text(
                f"UPDATE regola_voce SET {', '.join(assegnazioni)}, updated_at = CURRENT_TIMESTAMP"
                f" WHERE voce_codice = :voce AND {' AND '.join(condizioni)}"
            ),
            params,
        )

    for voce, *note in _NOTE:
        condizione, params = _uguale("nota", note[da], "vecchio")
        bind.execute(
            sa.text(
                "UPDATE regola_voce SET nota = :nuovo, updated_at = CURRENT_TIMESTAMP"
                f" WHERE voce_codice = :voce AND {condizione}"
            ),
            {"voce": voce, "nuovo": note[a], **params},
        )


def upgrade() -> None:
    _aggiorna(0, 1)


def downgrade() -> None:
    _aggiorna(1, 0)
