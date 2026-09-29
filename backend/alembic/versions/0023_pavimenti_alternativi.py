"""pavimenti alternativi + A.6 intera governata (gap G1/G2, 09-14)

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-28T00:00:00.000000

Porta su ogni DB ESISTENTE (dev.db oggi, Postgres di produzione al push) gli
effetti che il 09-09/09-10 hanno aggiunto al seed per chiudere G1 (i pavimenti
alternativi — laminato, vinilico LVT, moquette, sottofondo — comparivano
sempre insieme al pavimento scelto, mai esclusi) e G2 (in A.6 PAVIMENTI E
RIVESTIMENTI entravano sempre battiscopa/levigature/pose alternative, non
solo quella del pavimento scelto). Un DB nuovo non ha bisogno di questa
migrazione: il seed create-if-missing (D-41) crea tutto da zero al boot. Un
DB esistente invece non ripassa mai dal seed per righe gia' seminate in una
versione precedente del catalogo (stessa lezione della 0021/0022): senza
questa migrazione, in produzione i pavimenti alternativi e le lavorazioni di
A.6 resterebbero sommati fino al prossimo `--solo-assi` applicato a mano.

Le costanti sotto sono il diff fra `git show 2b6e29b:backend/seed_data/
seed-domande.json` (stato 0022) e il file committato dopo il 09-10, limitato
alle domande `tipo_pavimento` e `finitura` — generato da uno script usa-e-
getta (non versionato) che carica entrambi i JSON con `encoding="utf-8"`
esplicito. `_OPZIONI_NUOVE`: 3 opzioni (laminato/vinilico_lvt/moquette) di
`tipo_pavimento`, assenti dalla base. `_EFFETTI_AGGIUNTI`: 175 effetti a
bersaglio naturale (voce), chiave (domanda, opzione, tipo_effetto,
categoria_code, sottocategoria, voce, tipo_code) + valore fuori chiave —
includi/escludi sui pavimenti alternativi e su A.6.3/A.6.9, piu' i
`fattore_quantita` di quota bagno (D-02) sulle voci individuali del gres a
pavimento per ognuna delle sei opzioni non-gres. `_EFFETTI_RIMOSSI`: vuoto
(nessun effetto della base e' sparito dal nuovo seed per queste due domande).

Lezione del 09-06 (WR di fase, poi T-09-57 di questo piano): una migrazione
con chiavi non risolte non deve restare inerte in silenzio. Qui la guardia e'
a due fasi come nel template di `applica_taratura.py::emetti_migrazione`:
prima si risolvono TUTTE le chiavi naturali (voce sempre per codice/
descrizione esatta dentro la sua sottocategoria; opzione o gia' presente in
DB o fra quelle appena create da `_OPZIONI_NUOVE`), poi — solo se il catalogo
e' presente (la domanda `tipo_pavimento` esiste gia') — si solleva
`RuntimeError` se anche una sola chiave non si risolve, PRIMA di qualunque
scrittura. Su un DB vergine o popolato di sole righe fittizie (nessuna
domanda `tipo_pavimento`) la migrazione e' un no-op esplicito: ci pensa il
seed al boot.

Idempotente: ogni scrittura e' create-if-missing sulla stessa chiave naturale
del seed (`scripts/seed.py::_crea_effetto_se_manca`), cosi' un seed
successivo o una riapplicazione della migrazione non duplica nulla.
Reversibile: il downgrade toglie solo cio' che l'upgrade ha scritto (stesso
principio del WR-02 applicato alla 0021 in questo stesso piano) — mai un
DELETE di `domanda`/opzioni preesistenti, le tre opzioni nuove sono
cancellate solo se restano senza alcun effetto residuo.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0023"
down_revision: Union[str, Sequence[str], None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DOMANDA_PAVIMENTO = "tipo_pavimento"

_OPZIONI_NUOVE: tuple[tuple, ...] = (('tipo_pavimento', 'laminato', 'Laminato', 'Listoni in laminato posati flottanti', 5, False), ('tipo_pavimento', 'moquette', 'Moquette', 'Quadrotte di moquette autoposanti', 7, False), ('tipo_pavimento', 'vinilico_lvt', 'Vinilico LVT', 'Listoni vinilici multistrato a incastro', 6, False))

_EFFETTI_AGGIUNTI: tuple[tuple, ...] = (('finitura', 'alto', 'escludi', 'A-EDILE', 'A.6', 'A.6.9', None, None), ('finitura', 'alto', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:120 × 278 cm, spessore 6 mm:effetto marmo, superficie lucida', None, None), ('finitura', 'alto', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:160 × 320 cm, spessore 6 mm:effetto marmo, superficie lucida', None, None), ('finitura', 'alto', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', None, None), ('finitura', 'alto', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto cemento:120 × 120 cm, rettificato, spessore 10,5 mm', None, None), ('finitura', 'alto', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm: 90 × 90 cm', None, None), ('finitura', 'alto', 'includi', 'A-EDILE', 'A.6', 'A.6.4', None, None), ('finitura', 'base', 'escludi', 'A-EDILE', 'A.6', 'A.6.9', None, None), ('finitura', 'base', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 60 cm, spessore 15 mm', None, None), ('finitura', 'base', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, effetto marmetta grana media antiscivolo (R11), spessore 8,5 mm', None, None), ('finitura', 'base', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, superficie bocciardata antiscivolo (R12 B), spessore 8,5 mm', None, None), ('finitura', 'base', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):dimensioni 60 × 60 cm, spessore 15 mm', None, None), ('finitura', 'base', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 60 cm, spessore 10 mm', None, None), ('finitura', 'base', 'includi', 'A-EDILE', 'A.6', 'A.6.3', None, None), ('finitura', 'medio', 'escludi', 'A-EDILE', 'A.6', 'A.6.9', None, None), ('finitura', 'medio', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):60 × 120 cm, naturale, spessore 10 mm', None, None), ('finitura', 'medio', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 120 cm, spessore 10,5 mm', None, None), ('finitura', 'medio', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:30 × 60 cm', None, None), ('finitura', 'medio', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:60 × 120 cm', None, None), ('finitura', 'medio', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 60 cm, spessore 10 mm', None, None), ('finitura', 'medio', 'escludi', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9):60 × 120 cm, spessore 10,5 mm', None, None), ('finitura', 'medio', 'includi', 'A-EDILE', 'A.6', 'A.6.3', None, None), ('tipo_pavimento', 'gres', 'includi', 'A-EDILE', 'A.6', 'A.6.8', None, None), ('tipo_pavimento', 'laminato', 'escludi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: essenza', None, None), ('tipo_pavimento', 'laminato', 'escludi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: multistrato bianco', None, None), ('tipo_pavimento', 'laminato', 'escludi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 75 × 10 mm: multistrato bianco', None, None), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'A-EDILE', 'A.6', 'A.6.1', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 120 cm, naturale, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 60 cm, spessore 15 mm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A):30 × 60 cm, naturale o bocciardato, spessore 10', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, effetto marmetta grana media antiscivolo (R11), spessore 8,5 mm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, superficie bocciardata antiscivolo (R12 B), spessore 8,5 mm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:120 × 278 cm, spessore 6 mm:effetto marmo, superficie lucida', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:160 × 320 cm, spessore 6 mm:effetto marmo, superficie lucida', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):60 × 120 cm, naturale, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):dimensioni 60 × 60 cm, spessore 15 mm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto cemento:120 × 120 cm, rettificato, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 30 cm, disegno mosaico', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 60 cm, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 120 cm, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm: 90 × 90 cm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:30 × 60 cm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:60 × 120 cm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 60 cm, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'laminato', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9):60 × 120 cm, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'laminato', 'includi', 'A-EDILE', 'A.6', 'A.6.2', None, None), ('tipo_pavimento', 'laminato', 'includi', 'A-EDILE', 'A.6', 'A.6.7', None, None), ('tipo_pavimento', 'laminato', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: essenza', None, None), ('tipo_pavimento', 'laminato', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: multistrato bianco', None, None), ('tipo_pavimento', 'laminato', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 75 × 10 mm: essenza', None, None), ('tipo_pavimento', 'laminato', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 75 × 10 mm: multistrato bianco', None, None), ('tipo_pavimento', 'laminato', 'includi', 'B-FINITURE', 'PAVIMENTI', "Pavimento in laminato antistatico (< 2 kV - UNI EN 1815 ed UNI EN 14041), con supporto di base in fibra di legno ad elevata densità (HDF) con superficie ad effetto legno, resistenza all'abrasione superficiale in classe AC4 (UNI EN 13329), rigonfiamento del bordo ≤ 18% (valore medio 11% UNI EN 13329)", None, None), ('tipo_pavimento', 'laminato', 'includi', 'B-FINITURE', 'PAVIMENTI', 'Unilin sottofondo in schiuma senza barriera vapore', None, None), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 120 cm, naturale, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 60 cm, spessore 15 mm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A):30 × 60 cm, naturale o bocciardato, spessore 10', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, effetto marmetta grana media antiscivolo (R11), spessore 8,5 mm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, superficie bocciardata antiscivolo (R12 B), spessore 8,5 mm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:120 × 278 cm, spessore 6 mm:effetto marmo, superficie lucida', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:160 × 320 cm, spessore 6 mm:effetto marmo, superficie lucida', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):60 × 120 cm, naturale, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):dimensioni 60 × 60 cm, spessore 15 mm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto cemento:120 × 120 cm, rettificato, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 30 cm, disegno mosaico', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 60 cm, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 120 cm, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm: 90 × 90 cm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:30 × 60 cm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:60 × 120 cm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 60 cm, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9):60 × 120 cm, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'maxi_lastra', 'includi', 'A-EDILE', 'A.6', 'A.6.8', None, None), ('tipo_pavimento', 'maxi_lastra', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino di gres porcellanato colorato in massa, superficie naturale o bocciardata:effetto cemento, 10 × 30 cm, spessore 8,5 mm con sguscia', None, None), ('tipo_pavimento', 'moquette', 'escludi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: essenza', None, None), ('tipo_pavimento', 'moquette', 'escludi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: multistrato bianco', None, None), ('tipo_pavimento', 'moquette', 'escludi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 75 × 10 mm: multistrato bianco', None, None), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 120 cm, naturale, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 60 cm, spessore 15 mm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A):30 × 60 cm, naturale o bocciardato, spessore 10', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, effetto marmetta grana media antiscivolo (R11), spessore 8,5 mm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, superficie bocciardata antiscivolo (R12 B), spessore 8,5 mm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:120 × 278 cm, spessore 6 mm:effetto marmo, superficie lucida', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:160 × 320 cm, spessore 6 mm:effetto marmo, superficie lucida', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):60 × 120 cm, naturale, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):dimensioni 60 × 60 cm, spessore 15 mm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto cemento:120 × 120 cm, rettificato, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 30 cm, disegno mosaico', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 60 cm, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 120 cm, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm: 90 × 90 cm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:30 × 60 cm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:60 × 120 cm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 60 cm, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'moquette', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9):60 × 120 cm, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'moquette', 'includi', 'A-EDILE', 'A.6', 'A.6.7', None, None), ('tipo_pavimento', 'moquette', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: essenza', None, None), ('tipo_pavimento', 'moquette', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: multistrato bianco', None, None), ('tipo_pavimento', 'moquette', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 75 × 10 mm: essenza', None, None), ('tipo_pavimento', 'moquette', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 75 × 10 mm: multistrato bianco', None, None), ('tipo_pavimento', 'moquette', 'includi', 'B-FINITURE', 'PAVIMENTI', 'Moquette in quadrotte autoposanti idonee alla posa senza collante, ad alta flessibilità, antistatiche, ignifughe di classe 1, dimensioni 50 × 50 cm: con supporto in composto termoplastico rinforzato con due strati di fibre di vetro e pretrattato con antibatterico:100% nylon, superficie velluto diseg', None, None), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 120 cm, naturale, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 60 cm, spessore 15 mm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A):30 × 60 cm, naturale o bocciardato, spessore 10', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, effetto marmetta grana media antiscivolo (R11), spessore 8,5 mm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, superficie bocciardata antiscivolo (R12 B), spessore 8,5 mm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:120 × 278 cm, spessore 6 mm:effetto marmo, superficie lucida', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:160 × 320 cm, spessore 6 mm:effetto marmo, superficie lucida', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):60 × 120 cm, naturale, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):dimensioni 60 × 60 cm, spessore 15 mm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto cemento:120 × 120 cm, rettificato, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 30 cm, disegno mosaico', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 60 cm, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 120 cm, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm: 90 × 90 cm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:30 × 60 cm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:60 × 120 cm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 60 cm, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'mosaico', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9):60 × 120 cm, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'mosaico', 'includi', 'A-EDILE', 'A.6', 'A.6.8', None, None), ('tipo_pavimento', 'mosaico', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino di gres porcellanato colorato in massa, superficie naturale o bocciardata:effetto cemento, 10 × 30 cm, spessore 8,5 mm con sguscia', None, None), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 120 cm, naturale, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 60 cm, spessore 15 mm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A):30 × 60 cm, naturale o bocciardato, spessore 10', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, effetto marmetta grana media antiscivolo (R11), spessore 8,5 mm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, superficie bocciardata antiscivolo (R12 B), spessore 8,5 mm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:120 × 278 cm, spessore 6 mm:effetto marmo, superficie lucida', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:160 × 320 cm, spessore 6 mm:effetto marmo, superficie lucida', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):60 × 120 cm, naturale, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):dimensioni 60 × 60 cm, spessore 15 mm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto cemento:120 × 120 cm, rettificato, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 30 cm, disegno mosaico', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 60 cm, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 120 cm, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm: 90 × 90 cm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:30 × 60 cm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:60 × 120 cm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 60 cm, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'parquet', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9):60 × 120 cm, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'parquet', 'includi', 'A-EDILE', 'A.6', 'A.6.10', None, None), ('tipo_pavimento', 'parquet', 'includi', 'A-EDILE', 'A.6', 'A.6.7', None, None), ('tipo_pavimento', 'vinilico_lvt', 'escludi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: essenza', None, None), ('tipo_pavimento', 'vinilico_lvt', 'escludi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: multistrato bianco', None, None), ('tipo_pavimento', 'vinilico_lvt', 'escludi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 75 × 10 mm: multistrato bianco', None, None), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'A-EDILE', 'A.6', 'A.6.1', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 120 cm, naturale, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 60 cm, spessore 15 mm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A):30 × 60 cm, naturale o bocciardato, spessore 10', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, effetto marmetta grana media antiscivolo (R11), spessore 8,5 mm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, superficie bocciardata antiscivolo (R12 B), spessore 8,5 mm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:120 × 278 cm, spessore 6 mm:effetto marmo, superficie lucida', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:160 × 320 cm, spessore 6 mm:effetto marmo, superficie lucida', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):60 × 120 cm, naturale, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):dimensioni 60 × 60 cm, spessore 15 mm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto cemento:120 × 120 cm, rettificato, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 30 cm, disegno mosaico', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 60 cm, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 120 cm, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm: 90 × 90 cm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:30 × 60 cm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:60 × 120 cm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 60 cm, spessore 10 mm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'fattore_quantita', 'B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9):60 × 120 cm, spessore 10,5 mm', None, 0.12), ('tipo_pavimento', 'vinilico_lvt', 'includi', 'A-EDILE', 'A.6', 'A.6.2', None, None), ('tipo_pavimento', 'vinilico_lvt', 'includi', 'A-EDILE', 'A.6', 'A.6.7', None, None), ('tipo_pavimento', 'vinilico_lvt', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: essenza', None, None), ('tipo_pavimento', 'vinilico_lvt', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: multistrato bianco', None, None), ('tipo_pavimento', 'vinilico_lvt', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 75 × 10 mm: essenza', None, None), ('tipo_pavimento', 'vinilico_lvt', 'includi', 'B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 75 × 10 mm: multistrato bianco', None, None), ('tipo_pavimento', 'vinilico_lvt', 'includi', 'B-FINITURE', 'PAVIMENTI', "Vinilico multistrato LVT in listoni delle dimensioni di 17 ÷ 20 × 100 ÷ 124 cm o piastre delle dimensioni di 36 × 69 cm con profili laterali ad incastro per posa senza collante, con uno strato d'usura in pvc puro trasparente che protegge uno strato a motivi stampatitrattato con fotoreticolazione UV ", None, None))

_EFFETTI_RIMOSSI: tuple[tuple, ...] = ()


def _tabelle():
    """Definizioni locali delle tabelle toccate (mai i modelli ORM, stesso
    principio della 0021/0022: una migrazione dati non deve dipendere da come
    saranno i modelli in futuro)."""
    domanda = sa.table(
        "domanda",
        sa.column("code"),
    )
    opzione = sa.table(
        "opzione_domanda",
        sa.column("id"),
        sa.column("domanda_code"),
        sa.column("code"),
        sa.column("etichetta"),
        sa.column("descrizione"),
        sa.column("is_default"),
        sa.column("ordine"),
        sa.column("attiva"),
        sa.column("updated_at"),
    )
    sottocategoria = sa.table(
        "sottocategoria",
        sa.column("id"),
        sa.column("listino_id"),
        sa.column("categoria_code"),
        sa.column("codice"),
        sa.column("nome"),
    )
    voce = sa.table(
        "voce",
        sa.column("id"),
        sa.column("sottocategoria_id"),
        sa.column("codice"),
        sa.column("descrizione"),
    )
    effetto = sa.table(
        "effetto_opzione",
        sa.column("id"),
        sa.column("opzione_id"),
        sa.column("tipo_effetto"),
        sa.column("target_categoria_code"),
        sa.column("target_sottocategoria_id"),
        sa.column("target_voce_id"),
        sa.column("tipo_code"),
        sa.column("valore"),
        sa.column("attivo"),
        sa.column("updated_at"),
    )
    return domanda, opzione, sottocategoria, voce, effetto


def _listino_default_id(bind):
    """id del listino predefinito, o None se manca (catalogo non seminato).

    `sottocategoria` e' per listino: il seed risolve i bersagli naturali solo
    sul listino predefinito (`scripts/seed.py::seed_domande`) e la migrazione
    fa lo stesso. Senza questo filtro, con un secondo listino con gli stessi
    codici, `.first()` senza ORDER BY su Postgres poteva agganciare le voci
    del listino sbagliato (WR-03 review 09)."""
    listino = sa.table("listino", sa.column("id"), sa.column("is_default"))
    riga = bind.execute(
        sa.select(listino.c.id).where(listino.c.is_default.is_(True)).order_by(listino.c.id).limit(1)
    ).first()
    return riga[0] if riga is not None else None


def _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key):
    """Chiave naturale -> voce.id (codice se esiste, altrimenti nome/descrizione
    esatta — stessa regola del seed/0022). `None` se non risolta."""
    listino_id = _listino_default_id(bind)
    if listino_id is None:
        return None
    riga_sotto = bind.execute(
        sa.select(sottocategoria.c.id)
        .where(
            sottocategoria.c.listino_id == listino_id,
            sottocategoria.c.categoria_code == categoria_code,
            sottocategoria.c.codice == sottocategoria_key,
        )
        .order_by(sottocategoria.c.id)
    ).first()
    if riga_sotto is None:
        riga_sotto = bind.execute(
            sa.select(sottocategoria.c.id)
            .where(
                sottocategoria.c.listino_id == listino_id,
                sottocategoria.c.categoria_code == categoria_code,
                sottocategoria.c.codice.is_(None),
                sottocategoria.c.nome == sottocategoria_key,
            )
            .order_by(sottocategoria.c.id)
        ).first()
    if riga_sotto is None:
        return None
    sotto_id = riga_sotto[0]
    riga_voce = bind.execute(
        sa.select(voce.c.id)
        .where(voce.c.sottocategoria_id == sotto_id, voce.c.codice == voce_key)
        .order_by(voce.c.id)
    ).first()
    if riga_voce is None:
        riga_voce = bind.execute(
            sa.select(voce.c.id)
            .where(
                voce.c.sottocategoria_id == sotto_id,
                voce.c.codice.is_(None),
                voce.c.descrizione == voce_key,
            )
            .order_by(voce.c.id)
        ).first()
    return riga_voce[0] if riga_voce is not None else None


def _opzione_id(bind, opzione, domanda_code, opzione_code):
    riga = bind.execute(
        sa.select(opzione.c.id).where(opzione.c.domanda_code == domanda_code, opzione.c.code == opzione_code)
    ).first()
    return riga[0] if riga is not None else None


def _vicino(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= 1e-6


def _effetto_esiste(bind, effetto, **chiave) -> bool:
    condizioni = [
        (effetto.c[colonna] == valore) if valore is not None else effetto.c[colonna].is_(None)
        for colonna, valore in chiave.items()
    ]
    riga = bind.execute(sa.select(effetto.c.id).where(*condizioni)).first()
    return riga is not None


def upgrade() -> None:
    bind = op.get_bind()
    adesso = datetime.now(timezone.utc).replace(tzinfo=None)
    domanda, opzione, sottocategoria, voce, effetto = _tabelle()

    riga_domanda = bind.execute(
        sa.select(domanda.c.code).where(domanda.c.code == DOMANDA_PAVIMENTO)
    ).first()
    if riga_domanda is None:
        # DB vergine o popolato di sole righe fittizie (nessun catalogo
        # ancora seminato): il seed create-if-missing crea tutto da zero al
        # boot (D-41), questa migrazione non ha nulla da fare.
        return

    opzioni_nuove_chiavi = {(dc, oc) for dc, oc, *_ in _OPZIONI_NUOVE}

    non_risolte: list[str] = []
    n_tot = 0
    n_ok = 0

    risolti_effetti_aggiunti: list[tuple] = []
    for (
        domanda_code,
        opzione_code,
        tipo_effetto,
        categoria_code,
        sottocategoria_key,
        voce_key,
        tipo_code,
        valore,
    ) in _EFFETTI_AGGIUNTI:
        n_tot += 1
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        opzione_pendente = opzione_id is None and (domanda_code, opzione_code) in opzioni_nuove_chiavi
        if voce_id is None or (opzione_id is None and not opzione_pendente):
            non_risolte.append(
                f"effetto_aggiunto {domanda_code}/{opzione_code}/{categoria_code}/{sottocategoria_key}/{voce_key}"
            )
            continue
        n_ok += 1
        risolti_effetti_aggiunti.append(
            (domanda_code, opzione_code, opzione_id, tipo_effetto, voce_id, tipo_code, valore)
        )

    risolti_effetti_rimossi: list[tuple] = []
    for (
        domanda_code,
        opzione_code,
        tipo_effetto,
        categoria_code,
        sottocategoria_key,
        voce_key,
        tipo_code,
        valore,
    ) in _EFFETTI_RIMOSSI:
        n_tot += 1
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        if voce_id is None or opzione_id is None:
            non_risolte.append(
                f"effetto_rimosso {domanda_code}/{opzione_code}/{categoria_code}/{sottocategoria_key}/{voce_key}"
            )
            continue
        n_ok += 1
        risolti_effetti_rimossi.append((opzione_id, tipo_effetto, voce_id, tipo_code, valore))

    if non_risolte:
        raise RuntimeError(
            f"0023: risolte {n_ok}/{n_tot} chiavi naturali; non risolte: {non_risolte}"
        )

    # --- scritture: solo dopo la guardia sopra, solo righe gia' risolte ----

    opzione_id_per_chiave: dict[tuple[str, str], int] = {}
    for domanda_code, opzione_code, etichetta, descrizione, ordine, is_default in _OPZIONI_NUOVE:
        esistente = _opzione_id(bind, opzione, domanda_code, opzione_code)
        if esistente is not None:
            opzione_id_per_chiave[(domanda_code, opzione_code)] = esistente
            continue
        bind.execute(
            sa.insert(opzione).values(
                domanda_code=domanda_code,
                code=opzione_code,
                etichetta=etichetta,
                descrizione=descrizione,
                is_default=is_default,
                ordine=ordine,
                attiva=True,
                updated_at=adesso,
            )
        )
        opzione_id_per_chiave[(domanda_code, opzione_code)] = _opzione_id(bind, opzione, domanda_code, opzione_code)

    for domanda_code, opzione_code, opzione_id, tipo_effetto, voce_id, tipo_code, valore in risolti_effetti_aggiunti:
        if opzione_id is None:
            opzione_id = opzione_id_per_chiave[(domanda_code, opzione_code)]
        if _effetto_esiste(
            bind,
            effetto,
            opzione_id=opzione_id,
            tipo_effetto=tipo_effetto,
            target_categoria_code=None,
            target_sottocategoria_id=None,
            target_voce_id=voce_id,
            tipo_code=tipo_code,
        ):
            continue
        bind.execute(
            sa.insert(effetto).values(
                opzione_id=opzione_id,
                tipo_effetto=tipo_effetto,
                target_categoria_code=None,
                target_sottocategoria_id=None,
                target_voce_id=voce_id,
                tipo_code=tipo_code,
                valore=valore,
                attivo=True,
                updated_at=adesso,
            )
        )

    for opzione_id, tipo_effetto, voce_id, tipo_code, valore in risolti_effetti_rimossi:
        cond_tipo_code = (
            effetto.c.tipo_code == tipo_code if tipo_code is not None else effetto.c.tipo_code.is_(None)
        )
        riga = bind.execute(
            sa.select(effetto.c.id, effetto.c.valore).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == tipo_effetto,
                effetto.c.target_voce_id == voce_id,
                cond_tipo_code,
            )
        ).first()
        if riga is None:
            continue
        if valore is not None and not _vicino(riga[1], valore):
            continue
        bind.execute(sa.delete(effetto).where(effetto.c.id == riga[0]))


def downgrade() -> None:
    """Rimuove esattamente gli effetti che questa migrazione avrebbe creato,
    ripristina quelli che avrebbe rimosso (nessuno, oggi) e cancella le tre
    opzioni nuove solo se restano senza alcun effetto residuo — tollerante
    (nessun raise): una curatela fatta a mano dopo l'upgrade non deve
    bloccare un downgrade, solo essere rispettata (le righe non toccate da
    questa migrazione restano)."""
    bind = op.get_bind()
    adesso = datetime.now(timezone.utc).replace(tzinfo=None)
    domanda, opzione, sottocategoria, voce, effetto = _tabelle()

    for (
        domanda_code,
        opzione_code,
        tipo_effetto,
        categoria_code,
        sottocategoria_key,
        voce_key,
        tipo_code,
        _valore,
    ) in _EFFETTI_AGGIUNTI:
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if opzione_id is None or voce_id is None:
            continue
        cond_tipo_code = (
            effetto.c.tipo_code == tipo_code if tipo_code is not None else effetto.c.tipo_code.is_(None)
        )
        bind.execute(
            sa.delete(effetto).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == tipo_effetto,
                effetto.c.target_voce_id == voce_id,
                cond_tipo_code,
            )
        )

    for (
        domanda_code,
        opzione_code,
        tipo_effetto,
        categoria_code,
        sottocategoria_key,
        voce_key,
        tipo_code,
        valore,
    ) in _EFFETTI_RIMOSSI:
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        voce_id = _risolvi_voce_id(bind, sottocategoria, voce, categoria_code, sottocategoria_key, voce_key)
        if opzione_id is None or voce_id is None:
            continue
        cond_tipo_code = (
            effetto.c.tipo_code == tipo_code if tipo_code is not None else effetto.c.tipo_code.is_(None)
        )
        gia_presente = bind.execute(
            sa.select(effetto.c.id).where(
                effetto.c.opzione_id == opzione_id,
                effetto.c.tipo_effetto == tipo_effetto,
                effetto.c.target_voce_id == voce_id,
                cond_tipo_code,
            )
        ).first()
        if gia_presente is not None:
            continue
        bind.execute(
            sa.insert(effetto).values(
                opzione_id=opzione_id,
                tipo_effetto=tipo_effetto,
                target_categoria_code=None,
                target_sottocategoria_id=None,
                target_voce_id=voce_id,
                tipo_code=tipo_code,
                valore=valore,
                attivo=True,
                updated_at=adesso,
            )
        )

    for domanda_code, opzione_code, *_ in _OPZIONI_NUOVE:
        opzione_id = _opzione_id(bind, opzione, domanda_code, opzione_code)
        if opzione_id is None:
            continue
        residui = bind.execute(
            sa.select(sa.func.count()).select_from(effetto).where(effetto.c.opzione_id == opzione_id)
        ).scalar_one()
        if residui == 0:
            bind.execute(sa.delete(opzione).where(opzione.c.id == opzione_id))
