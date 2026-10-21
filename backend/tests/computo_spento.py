"""Spegne il computo parametrico su un DB di test.

Dalla Fase 11 il Free e il Pro calcolano col computo parametrico
(`services/computo.py`). Il calcolo v1/v2 — EUR/m2 x moltiplicatore piu' gli
effetti in euro per il Free, catena `CoefficienteQuantitaVoce` per il Pro —
resta come ripiego per un listino senza regole (MOT-03). I test che fissano
l'aritmetica di quel percorso (oracolo 47.985-70.575, ordine degli effetti,
scostamento, oracolo per voce) lo verificano qui: con le regole disattivate
il listino non ha regole e il motore prende il ripiego.

Il computo parametrico ha i suoi test in `tests/test_computo*.py`.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.computo import RegolaVoce


def spegni_computo(session: Session) -> None:
    session.query(RegolaVoce).update({RegolaVoce.attiva: False})
    session.commit()


# Gli effetti Free in euro che la v3 ha spento (migrazione 0026) perche' ora
# sono voci del computo. Valori del seed v2, copiati qui come dati di test:
# servono ai test dell'aritmetica degli effetti, non al prodotto.
_EFFETTI_V2: tuple[tuple[str, str, str, str, str, str | None], ...] = (
    ("piano", "valore", "eur_per_scostamento", "A-EDILE", "350", None),
    ("locali", "valore", "eur_per_scostamento", "A-EDILE", "900", None),
    ("bagni", "valore", "eur_per_scostamento", "A-EDILE", "1900", None),
    ("bagni", "valore", "eur_per_scostamento", "D-PRODOTTI", "1400", None),
    ("finestre", "valore", "eur_per_scostamento", "C-SERRAMENTI", "650", None),
    ("portefinestre", "valore", "eur_per_scostamento", "C-SERRAMENTI", "950", None),
    ("porte", "valore", "eur_per_scostamento", "C-SERRAMENTI", "480", None),
    ("condizionatori", "valore", "eur_per_scostamento", "A-EDILE", "700", None),
    ("condizionatori", "valore", "eur_per_scostamento", "D-PRODOTTI", "900", None),
    ("muri_da_recuperare", "valore", "eur_per_scostamento", "A-EDILE", "28", None),
    ("muri_da_rifare_mq", "valore", "eur_per_scostamento", "A-EDILE", "95", None),
    ("muri_da_creare_mq", "valore", "eur_per_scostamento", "A-EDILE", "110", None),
    ("impianti", "elettrico", "moltiplicatore_categoria", "A-EDILE", "1.14", "leggera"),
    ("impianti", "elettrico", "moltiplicatore_categoria", "A-EDILE", "1.07", "moderata"),
    ("impianti", "elettrico", "moltiplicatore_categoria", "A-EDILE", "1.00", "totale"),
    ("impianti", "idrico", "moltiplicatore_categoria", "A-EDILE", "1.10", "leggera"),
    ("impianti", "idrico", "moltiplicatore_categoria", "A-EDILE", "1.05", "moderata"),
    ("impianti", "idrico", "moltiplicatore_categoria", "A-EDILE", "1.00", "totale"),
    ("impianti", "gas", "moltiplicatore_categoria", "A-EDILE", "1.04", "leggera"),
    ("impianti", "gas", "moltiplicatore_categoria", "A-EDILE", "1.02", "moderata"),
    ("impianti", "gas", "moltiplicatore_categoria", "A-EDILE", "1.00", "totale"),
    ("impianti", "termico", "moltiplicatore_categoria", "A-EDILE", "1.16", "leggera"),
    ("impianti", "termico", "moltiplicatore_categoria", "A-EDILE", "1.09", "moderata"),
    ("impianti", "termico", "moltiplicatore_categoria", "A-EDILE", "1.00", "totale"),
    ("livello_finiture", "base", "moltiplicatore_categoria", "B-FINITURE", "0.85", None),
    ("livello_finiture", "base", "moltiplicatore_categoria", "C-SERRAMENTI", "0.88", None),
    ("livello_finiture", "base", "moltiplicatore_categoria", "D-PRODOTTI", "0.85", None),
    ("livello_finiture", "alto", "moltiplicatore_categoria", "B-FINITURE", "1.30", None),
    ("livello_finiture", "alto", "moltiplicatore_categoria", "C-SERRAMENTI", "1.25", None),
    ("livello_finiture", "alto", "moltiplicatore_categoria", "D-PRODOTTI", "1.35", None),
    ("interventi_efficientamento", "cambio_caldaia", "eur_fisso_categoria", "A-EDILE", "6500", None),
)


def catalogo_v2(session: Session) -> None:
    """Riporta il catalogo Free alla forma v2 sopra un seed v3: computo spento,
    effetti in euro e moltiplicatori sostituiti riaccesi, domanda `impianti`
    attiva, stepper dei muri senza `attributo_code`.

    Le domande d'intervento della v3 restano a DB ma non hanno effetti Free:
    sul percorso EUR/m2 sono neutre."""
    from decimal import Decimal

    from app.models.domanda import Domanda, EffettoOpzione, OpzioneDomanda

    spegni_computo(session)
    session.get(Domanda, "impianti").attiva = True
    for code in ("muri_da_recuperare", "muri_da_rifare_mq", "muri_da_creare_mq"):
        session.get(Domanda, code).attributo_code = None
    for domanda, opzione, tipo_effetto, categoria, valore, tipo_code in _EFFETTI_V2:
        opz = session.query(OpzioneDomanda).filter_by(domanda_code=domanda, code=opzione).one()
        esiste = (
            session.query(EffettoOpzione)
            .filter_by(
                opzione_id=opz.id,
                tipo_effetto=tipo_effetto,
                target_categoria_code=categoria,
                tipo_code=tipo_code,
            )
            .one_or_none()
        )
        if esiste is None:
            session.add(
                EffettoOpzione(
                    opzione_id=opz.id,
                    tipo_effetto=tipo_effetto,
                    target_categoria_code=categoria,
                    tipo_code=tipo_code,
                    valore=Decimal(valore),
                )
            )
        else:
            esiste.attivo = True
            esiste.valore = Decimal(valore)
    session.commit()
