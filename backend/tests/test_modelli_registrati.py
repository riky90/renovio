"""Un modello dimenticato in `app/models/__init__.py` deve far fallire un
test, non una migrazione (WR-05).

`alembic/env.py` costruisce `target_metadata = Base.metadata` fidandosi del
solo `from app import models`: una entita' il cui modulo non e' riesportato
la' dentro non finisce nel metadata, e il prossimo
`alembic revision --autogenerate` scrive un `drop_table` per la sua tabella.
Con `lead` fra le tabelle in gioco, il danno possibile e' la perdita dei
contatti commerciali.

I due test girano in un SOTTOPROCESSO, e non e' un vezzo: nella stessa
sessione pytest decine di altri file importano `app.models.lead` e
`app.models.testo` direttamente, quindi `Base.metadata` e' gia' popolato
quando questo modulo viene eseguito e la verifica passerebbe anche con il
difetto in piedi. Solo un interprete pulito che importa `app.models` e
nient'altro dice la verita'.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _esegui(codice: str) -> str:
    """Esegue `codice` in un interprete pulito con cwd sul backend, cosi'
    che `app` si risolva dal sorgente e nessun import di un altro test
    abbia gia' popolato `Base.metadata`."""
    esito = subprocess.run(
        [sys.executable, "-c", codice],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    assert esito.returncode == 0, f"sottoprocesso fallito:\nSTDOUT:\n{esito.stdout}\nSTDERR:\n{esito.stderr}"
    return esito.stdout.strip()


def test_ogni_modulo_di_app_models_e_registrato_in_metadata() -> None:
    """Per ogni modulo sotto `app/models/`, ogni entita' ORM che vi e'
    DEFINITA deve risultare in `Base.metadata` dopo il solo
    `from app import models`. Il confronto usa lo snapshot preso PRIMA di
    importare i singoli moduli: e' l'import esplicito a rivelare le tabelle
    che il package non porta con se'."""
    codice = """
import importlib
import pkgutil

from app.db import Base
from app import models

registrate = set(Base.metadata.tables)

mancanti = []
for info in pkgutil.iter_modules(models.__path__):
    nome_modulo = f"app.models.{info.name}"
    modulo = importlib.import_module(nome_modulo)
    for oggetto in vars(modulo).values():
        if not isinstance(oggetto, type) or not issubclass(oggetto, Base) or oggetto is Base:
            continue
        # Solo le entita' DEFINITE qui: una classe soltanto importata dal
        # modulo appartiene al modulo che la definisce, non a questo.
        if oggetto.__module__ != nome_modulo:
            continue
        tabella = getattr(oggetto, "__tablename__", None)
        if tabella is not None and tabella not in registrate:
            mancanti.append(f"{nome_modulo}.{oggetto.__name__} -> tabella {tabella!r}")

print("\\n".join(sorted(mancanti)))
"""
    mancanti = _esegui(codice)
    assert mancanti == "", (
        "Entita' ORM non registrate su Base.metadata da `from app import models`.\n"
        "Aggiungile a `app/models/__init__.py` (import + __all__), altrimenti il\n"
        "prossimo `alembic revision --autogenerate` emettera' un drop_table per le\n"
        "loro tabelle:\n" + mancanti
    )


def test_le_tabelle_lead_e_testo_sono_nel_metadata() -> None:
    """Il caso concreto che ha motivato il test: `lead` (i contatti
    commerciali) e `testo`. Tenuto separato dal test generico perche' il
    messaggio di fallimento nomini subito le due tabelle che contano."""
    codice = """
from app.db import Base
from app import models  # noqa: F401  (import per side-effect: registra le entita')

print('lead' in Base.metadata.tables, 'testo' in Base.metadata.tables)
"""
    assert _esegui(codice) == "True True"
