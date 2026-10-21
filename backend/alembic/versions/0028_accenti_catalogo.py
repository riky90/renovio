"""catalogo domande: accenti veri al posto degli apostrofi ("e'" -> "è")

I testi del catalogo domande erano scritti con l'apostrofo al posto della
vocale accentata ("Che tipo di immobile e'?", "Si'", "piu'"): nel wizard si
leggono cosi', e un sito che scrive "e'" sembra trascurato. Il seed v3 li
corregge, ma `domanda` e `opzione_domanda` sono create-if-missing: sui DB gia'
seminati serve questa migrazione.

Si scrive SOLO dove il testo e' ancora identico a quello del seed (WHERE
colonna = vecchio): un testo gia' cambiato dal pannello admin non si tocca.

Revision ID: 0028
Revises: 0027
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0028'
down_revision: Union[str, Sequence[str], None] = '0027'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (testo con l'apostrofo, testo con l'accento)
_TESTI: tuple[tuple[str, str], ...] = (
    ("C'e' qualcosa che NON vuoi rifare?", "C'è qualcosa che NON vuoi rifare?"),
    ("C'e' un ascensore utilizzabile per i materiali?", "C'è un ascensore utilizzabile per i materiali?"),
    ("Che tipo di immobile e'?", 'Che tipo di immobile è?'),
    ("Conta un'unita' interna per ogni ambiente da climatizzare. Se non vuoi la climatizzazione, lascia 0.", "Conta un'unità interna per ogni ambiente da climatizzare. Se non vuoi la climatizzazione, lascia 0."),
    ("Demolizione piu' ricostruzione, non solo intonaco. Se non ce ne sono, lascia 0.", 'Demolizione più ricostruzione, non solo intonaco. Se non ce ne sono, lascia 0.'),
    ("Di che anni e' l'immobile?", "Di che anni è l'immobile?"),
    ("Fra i muri da rifare ce n'e' qualcuno portante?", "Fra i muri da rifare ce n'è qualcuno portante?"),
    ("Fra i muri nuovi ce n'e' qualcuno portante?", "Fra i muri nuovi ce n'è qualcuno portante?"),
    ("Il cartongesso e' piu' veloce e leggero, i blocchi tipo Siporex isolano meglio.", 'Il cartongesso è più veloce e leggero, i blocchi tipo Siporex isolano meglio.'),
    ("Il costo dell'arredo resta FUORI dal totale dei lavori: te lo mostriamo a parte, perche' non e' una lavorazione e non va confrontato con un preventivo edile.", "Il costo dell'arredo resta FUORI dal totale dei lavori: te lo mostriamo a parte, perché non è una lavorazione e non va confrontato con un preventivo edile."),
    ("Il piano cottura sara' a gas?", 'Il piano cottura sarà a gas?'),
    ("Il riscaldamento e' centralizzato?", 'Il riscaldamento è centralizzato?'),
    ("Isolamento sulla facciata. Il piu' efficace, richiede ponteggio e permessi.", 'Isolamento sulla facciata. Il più efficace, richiede ponteggio e permessi.'),
    ("Materiali di fascia media, la scelta piu' frequente.", 'Materiali di fascia media, la scelta più frequente.'),
    ("Materiali e apparecchi: e' la leva che sposta di piu' il conto a parita' di lavori.", 'Materiali e apparecchi: è la leva che sposta di più il conto a parità di lavori.'),
    ("Piu' il mezzo si avvicina all'ingresso, meno costa movimentare materiali e macerie.", "Più il mezzo si avvicina all'ingresso, meno costa movimentare materiali e macerie."),
    ("Piu' l'edificio e' datato, piu' spesso impianti e murature vanno rifatti da zero invece che adeguati.", "Più l'edificio è datato, più spesso impianti e murature vanno rifatti da zero invece che adeguati."),
    ("Puoi sceglierne piu' di uno.", 'Puoi sceglierne più di uno.'),
    ("Qual e' la classe energetica attuale?", 'Qual è la classe energetica attuale?'),
    ("Quello che e' gia' a posto esce dalla stima.", 'Quello che è già a posto esce dalla stima.'),
    ("Si'", 'Sì'),
    ("Si', a split", 'Sì, a split'),
    ("Si', canalizzata", 'Sì, canalizzata'),
    ("Si', in PVC", 'Sì, in PVC'),
    ("Si', in alluminio", 'Sì, in alluminio'),
    ("Su una ristrutturazione totale gli impianti sono gia' compresi nel prezzo base: qui pesano soprattutto sugli interventi piccoli e parziali.", 'Su una ristrutturazione totale gli impianti sono già compresi nel prezzo base: qui pesano soprattutto sugli interventi piccoli e parziali.'),
    ("Una villetta ha piu' superficie disperdente e piu' murature esterne di un appartamento a parita' di metri quadri.", 'Una villetta ha più superficie disperdente e più murature esterne di un appartamento a parità di metri quadri.'),
)

_COLONNE = (
    ("domanda", "testo"),
    ("domanda", "help"),
    ("opzione_domanda", "etichetta"),
    ("opzione_domanda", "descrizione"),
)


def _aggiorna(da: int, a: int) -> None:
    bind = op.get_bind()
    for tabella, colonna in _COLONNE:
        t = sa.table(tabella, sa.column(colonna, sa.String))
        for coppia in _TESTI:
            bind.execute(t.update().where(t.c[colonna] == coppia[da]).values({colonna: coppia[a]}))


def upgrade() -> None:
    _aggiorna(0, 1)


def downgrade() -> None:
    _aggiorna(1, 0)
