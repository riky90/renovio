"""computo parametrico: domande Pro per i lavori a corpo, clima solo predisposizione

Fase 11 (v3.0), dopo la taratura sui computi reali (TAR-01). I lavori che i
computi del tecnico mettono a corpo e il wizard non chiedeva diventano
domande del pannello Pro (gruppo `configuratore_pro`): bagni nuovi, bagni
ciechi, varchi, velette, carta da parati, terrazzi. `interv_clima` ha
l'opzione "solo predisposizione", con la sua domanda sul numero di split. Domande, opzioni, grandezze nuove e valori
delle opzioni li crea il seed al boot (create-if-missing); questa migrazione
ricollega alle grandezze nuove le regole che esistono gia', aggiunge i
termini mancanti alle grandezze esistenti e porta i punti elettrici a 0,65 per
m² commerciale. Il seed aggiunge anche, ai livelli base e medio di `finitura`,
la posa dei rivestimenti in formato grande (A.6.4, includi) al posto di quella
piccola (A.6.3, escludi), come nei computi del tecnico: sono effetti nuovi, e
quelli esistenti della 0023 non si toccano.

Le regole puntano a grandezze che il seed crea subito dopo: nell'intervallo
valgono 0, come una regola spenta.

Si scrive SOLO dove il valore e' ancora quello del seed precedente: cio' che
l'admin ha gia' cambiato non si tocca. Mai DELETE: in downgrade i termini
aggiunti vanno a fattore 0.

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0030'
down_revision: Union[str, Sequence[str], None] = '0029'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DA_DOMANDA = {"tipo_regola": "fisso", "grandezza_code": None, "fattore": "0"}

# voce -> (valori prima, valori dopo, nota prima, nota dopo)
_REGOLE: tuple[tuple[str, dict, dict, str | None, str], ...] = (
    *(
        (voce, {"grandezza_code": "bagni_rifatti"}, {"grandezza_code": "bagni_smontati"}, None, None)
        for voce in ("A.0.3", "A.0.4", "A.0.5", "A.0.6", "A.0.7")
    ),
    ("A.0.11", {"condizione_grandezza_code": "bagni_rifatti"}, {"condizione_grandezza_code": "bagni_smontati"}, None, None),
    (
        "A.1.10",
        {"grandezza_code": "mq_rivestimenti"},
        {"grandezza_code": "mq_rivestimenti_demoliti"},
        "Rivestimenti di bagni e cucina rifatti.",
        "Solo i bagni da smontare: un bagno nuovo non ha rivestimenti da demolire.",
    ),
    (
        "A.10.12",
        {"tipo_regola": "grandezza", "grandezza_code": "cucina", "fattore": "0"},
        {"tipo_regola": "grandezza", "grandezza_code": "bagni_ciechi", "fattore": "1"},
        "TAR-01: assente in tre cucine rifatte su tre; c'e' solo con un bagno cieco. Da legare "
        "alla domanda 'bagni ciechi' quando ci sara'.",
        "Foro verso l'esterno, sempre insieme all'areazione forzata (nota H). TAR-01: assente "
        "nelle cucine rifatte.",
    ),
    (
        "A.10.13",
        _DA_DOMANDA,
        {"tipo_regola": "grandezza", "grandezza_code": "bagni_ciechi", "fattore": "1"},
        "Aerazione forzata: solo per bagni ciechi.",
        "Un'areazione forzata per bagno cieco.",
    ),
    (
        "A.3.8",
        _DA_DOMANDA,
        {"tipo_regola": "grandezza", "grandezza_code": "varchi", "fattore": "1"},
        "Quadratura vano: solo su sopralluogo.",
        "Una quadratura per varco nuovo o allargato.",
    ),
    (
        "A.5.3",
        _DA_DOMANDA,
        {"tipo_regola": "grandezza", "grandezza_code": "velette_ml", "fattore": "1"},
        "Velette: solo su progetto.",
        "Dalla domanda Pro sulle velette.",
    ),
    (
        "A.1.11.1",
        _DA_DOMANDA,
        {"tipo_regola": "grandezza", "grandezza_code": "carta_parati_mq", "fattore": "1"},
        "Carta da parati: solo su sopralluogo.",
        "Dalla domanda Pro sulla carta da parati.",
    ),
    (
        "A.7.2",
        _DA_DOMANDA,
        {"tipo_regola": "grandezza", "grandezza_code": "terrazzi_mq", "fattore": "1"},
        "Membrana bituminosa: terrazzi, solo su sopralluogo.",
        "Membrana sui terrazzi e balconi della domanda Pro.",
    ),
    (
        "A.1.12",
        _DA_DOMANDA,
        {"tipo_regola": "grandezza", "grandezza_code": "terrazzi_mq", "fattore": "1"},
        "Guaina: terrazzi, solo su sopralluogo.",
        "Rimozione della vecchia guaina sui terrazzi della domanda Pro.",
    ),
    (
        "A.8.21",
        {"grandezza_code": "n_split"},
        {"grandezza_code": "n_split_predisposti"},
        None,
        "Predisposizione anche quando gli split si montano piu' avanti.",
    ),
)

# (grandezza, sorgente, fattore prima, fattore dopo): termini esistenti da cambiare.
_TERMINI_CAMBIATI: tuple[tuple[str, str, str, str], ...] = (
    ("punti_luce", "mq", "0.5", "0.65"),
)

# (grandezza, sorgente, fattore): termini nuovi su grandezze esistenti.
_TERMINI_NUOVI: tuple[tuple[str, str, str], ...] = (
    ("architravi", "varchi", "1"),
    ("linee_dedicate", "clima_predisposizione", "1"),
)

# (grandezza, descrizione prima, descrizione dopo)
_DESCRIZIONI: tuple[tuple[str, str, str], ...] = (
    (
        "punti_luce",
        "Circa un punto ogni 2 m² commerciali.",
        "Circa 0,65 punti per m² commerciale (TAR-01: 0,91 e 0,43 nei due computi totali; "
        "arrotondato in su perché la stima stia sopra il reale).",
    ),
    (
        "architravi",
        "Una porta ogni 10 m² di muro nuovo.",
        "Una porta ogni 10 m² di muro nuovo. Piu' una per ogni varco nuovo.",
    ),
)

_NUMERICHE = frozenset({"fattore"})


def _uguale(colonna: str, valore: str | None, nome: str) -> tuple[str, dict]:
    if valore is None:
        return f"{colonna} IS NULL", {}
    if colonna in _NUMERICHE:
        return f"{colonna} = CAST(:{nome} AS NUMERIC)", {nome: valore}
    return f"{colonna} = :{nome}", {nome: valore}


def _aggiorna(da: int, a: int) -> None:
    bind = op.get_bind()

    for voce, *valori in _REGOLE:
        vecchi, nuovi, nota_vecchia, nota_nuova = valori[da], valori[a], valori[2 + da], valori[2 + a]
        condizioni, params = [], {"voce": voce}
        for i, (colonna, valore) in enumerate(vecchi.items()):
            cond, p = _uguale(colonna, valore, f"v{i}")
            condizioni.append(cond)
            params.update(p)
        assegnazioni = []
        for i, (colonna, valore) in enumerate(nuovi.items()):
            if colonna in _NUMERICHE and valore is not None:
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
        if nota_vecchia is not None or nota_nuova is not None:
            cond, p = _uguale("nota", nota_vecchia, "vecchia")
            bind.execute(
                sa.text(
                    "UPDATE regola_voce SET nota = :nuova, updated_at = CURRENT_TIMESTAMP"
                    f" WHERE voce_codice = :voce AND {cond}"
                ),
                {"voce": voce, "nuova": nota_nuova, **p},
            )

    for grandezza, sorgente, *fattori in _TERMINI_CAMBIATI:
        bind.execute(
            sa.text(
                "UPDATE termine_grandezza SET fattore = CAST(:nuovo AS NUMERIC),"
                " updated_at = CURRENT_TIMESTAMP"
                " WHERE grandezza_code = :g AND sorgente_code = :s"
                " AND per_grandezza_code IS NULL AND fattore = CAST(:vecchio AS NUMERIC)"
            ),
            {"g": grandezza, "s": sorgente, "vecchio": fattori[da], "nuovo": fattori[a]},
        )

    for grandezza, sorgente, fattore in _TERMINI_NUOVI:
        if a == 1:
            # Un termine lasciato a 0 da un downgrade si riaccende; altrimenti
            # si inserisce, solo se la grandezza esiste e il termine non c'e'.
            bind.execute(
                sa.text(
                    "UPDATE termine_grandezza SET fattore = CAST(:f AS NUMERIC), updated_at = CURRENT_TIMESTAMP"
                    " WHERE grandezza_code = :g AND sorgente_code = :s AND per_grandezza_code IS NULL"
                    " AND fattore = 0"
                ),
                {"g": grandezza, "s": sorgente, "f": fattore},
            )
            bind.execute(
                sa.text(
                    # Cast espliciti: Postgres deduce tipi diversi per lo stesso
                    # parametro nella lista del SELECT (text) e nei confronti
                    # con le colonne (varchar) e rifiuta la query.
                    "INSERT INTO termine_grandezza"
                    " (grandezza_code, sorgente_code, fattore, per_grandezza_code, ordine, updated_at)"
                    " SELECT CAST(:g AS VARCHAR), CAST(:s AS VARCHAR), CAST(:f AS NUMERIC), NULL,"
                    " (SELECT COALESCE(MAX(t.ordine), -1) + 1 FROM termine_grandezza t"
                    "  WHERE t.grandezza_code = CAST(:g AS VARCHAR)),"
                    " CURRENT_TIMESTAMP"
                    " WHERE EXISTS (SELECT 1 FROM grandezza WHERE code = CAST(:g AS VARCHAR))"
                    " AND NOT EXISTS (SELECT 1 FROM termine_grandezza"
                    "  WHERE grandezza_code = CAST(:g AS VARCHAR) AND sorgente_code = CAST(:s AS VARCHAR)"
                    "  AND per_grandezza_code IS NULL)"
                ),
                {"g": grandezza, "s": sorgente, "f": fattore},
            )
        else:
            bind.execute(
                sa.text(
                    "UPDATE termine_grandezza SET fattore = 0, updated_at = CURRENT_TIMESTAMP"
                    " WHERE grandezza_code = :g AND sorgente_code = :s AND per_grandezza_code IS NULL"
                ),
                {"g": grandezza, "s": sorgente},
            )

    for grandezza, *testi in _DESCRIZIONI:
        bind.execute(
            sa.text(
                "UPDATE grandezza SET descrizione = :nuova, updated_at = CURRENT_TIMESTAMP"
                " WHERE code = :g AND descrizione = :vecchia"
            ),
            {"g": grandezza, "vecchia": testi[da], "nuova": testi[a]},
        )


def upgrade() -> None:
    _aggiorna(0, 1)


def downgrade() -> None:
    _aggiorna(1, 0)
