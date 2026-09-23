"""Round-trip export -> import del listino (D-12, 08-03-PLAN.md, CUR-01/CUR-02).

Il test esistente (`test_dettaglio_pro_livelli.py::test_upload_excel_non_azzera_livello`)
copre un solo campo e non direbbe niente se il round-trip perdesse `um`,
`ordine` o il prezzo. Questo file chiude quella lacuna CONTANDO (D-12): il
criterio d'uscita del round-trip a vuoto e' una coppia di conteggi a zero
(`len(nuove) == 0 and len(modificate) == 0`), mai un'ispezione qualitativa
del payload.
"""

from __future__ import annotations

import io
import re
from decimal import Decimal
from pathlib import Path
from typing import get_args, get_origin

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.dettaglio_pro import Sottocategoria, Voce
from app.schemas.admin_upload import UploadTargetEsistente, VoceRigaIn
from app.services.city_resolver import resolve_listino
from app.services.export_excel.listino import COLONNE_VOCI, build_workbook_listino
from app.services.export_excel.workbook import TOKEN_CANCELLA, nuovo_workbook, scrivi_foglio_dati, serializza
from app.services.listino_upload_service import (
    apply_diff_idempotent,
    compute_diff,
    parse_flat_listino,
)
from scripts.seed import load_seed_data, seed
from tests.session_factory import sessione_di_test

REGISTRAZIONE_URL = "/api/v1/auth/registrati"
LISTINI_URL = "/api/v1/admin/listini"
UPLOAD_URL = "/api/v1/admin/upload-listino"


@pytest.fixture()
def session():
    """Sessione a livello di servizio (sqlite in-memoria + seed reale) —
    la maggior parte di questi test lavora sotto HTTP, incatenando
    direttamente `parse_flat_listino` -> `compute_diff` -> `apply_diff_idempotent`."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)
    with testing_session_local() as s:
        seed(s, load_seed_data())
        s.commit()
        yield s


def _listino(session):
    listino, _ = resolve_listino(session, "Reggio Emilia")
    return listino


def _voci_con_sotto(session, listino) -> list[tuple[Voce, Sottocategoria]]:
    return (
        session.query(Voce, Sottocategoria)
        .join(Sottocategoria, Voce.sottocategoria_id == Sottocategoria.id)
        .filter(Sottocategoria.listino_id == listino.id)
        .order_by(Voce.id)
        .all()
    )


def _riga_completa(voce: Voce, sotto: Sottocategoria, **overrides: object) -> dict:
    base = {
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
    base.update(overrides)
    return base


def _xlsx_piatto(righe: list[dict], *, colonne: list[str] = COLONNE_VOCI) -> bytes:
    """Costruisce un workbook piatto riusando le stesse funzioni di
    scrittura dell'export reale (`export_excel/workbook.py`), cosi' i test
    esercitano esattamente il formato che l'endpoint produce davvero —
    mai un formato inventato ad hoc dal test."""
    wb = nuovo_workbook(con_margine=False)
    scrivi_foglio_dati(wb, nome="voci", colonne=colonne, righe=righe)
    return serializza(wb)


class TestRoundtripAVuoto:
    def test_roundtrip_a_vuoto_non_produce_modifiche(self, session):
        """D-12: il file appena scaricato, ricaricato senza modifiche,
        produce zero righe nuove e zero righe modificate — un conteggio,
        non un'ispezione."""
        listino = _listino(session)
        xlsx_bytes, _ = build_workbook_listino(session, listino.id)

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)

        assert len(nuove) == 0 and len(modificate) == 0
        assert scarti_diff == []


class TestPreservazioneCampi:
    def test_roundtrip_preserva_tutti_i_campi(self, session):
        """Un giro completo export -> parse -> apply -> commit non deve
        cambiare NULLA: la tupla (codice, descrizione, um, prezzo, ordine,
        livello) di ogni Voce e' identica prima e dopo, livello curato
        incluso — e' il test che direbbe qualcosa se si perdesse `um` o
        `ordine`, che il test precedente (un solo campo) non copriva."""
        listino = _listino(session)
        voci_con_sotto = _voci_con_sotto(session, listino)
        assert len(voci_con_sotto) >= 2, "seed atteso: almeno due voci su RE"

        # Curatela non banale: livello valorizzato, non solo NULL, cosi' il
        # round-trip prova qualcosa di piu' che "i NULL restano NULL".
        voci_con_sotto[0][0].livello = "alto"
        voci_con_sotto[1][0].livello = "medio"
        session.commit()

        def _stato() -> list[tuple]:
            return sorted(
                (
                    (v.id, v.codice, v.descrizione, v.um, v.prezzo_unitario_cliente, v.ordine, v.livello)
                    for v, _ in _voci_con_sotto(session, listino)
                ),
                key=lambda t: t[0],
            )

        prima = _stato()

        xlsx_bytes, _ = build_workbook_listino(session, listino.id)
        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert scarti_diff == []
        apply_diff_idempotent(
            session,
            UploadTargetEsistente(listino_id=listino.id),
            [r.riga for r in nuove],
            [r.riga for r in modificate],
        )
        session.commit()
        session.expire_all()

        dopo = _stato()
        assert dopo == prima


class TestColonnaAssenteNonAzzera:
    def test_colonna_assente_non_azzera_il_campo(self, session):
        """CUR-02 esteso oltre un solo campo: un file piatto SENZA la
        colonna `livello` e SENZA la colonna `um` non tocca quei due campi
        a database, mentre il prezzo (presente e modificato nel file) si
        aggiorna regolarmente."""
        listino = _listino(session)
        voce, sotto = _voci_con_sotto(session, listino)[0]
        voce.livello = "alto"
        session.commit()

        livello_prima = voce.livello
        um_prima = voce.um
        nuovo_prezzo = voce.prezzo_unitario_cliente + Decimal("5.00")

        colonne_senza_livello_um = [c for c in COLONNE_VOCI if c not in ("um", "livello")]
        xlsx_bytes = _xlsx_piatto(
            [_riga_completa(voce, sotto, prezzo_unitario_cliente=nuovo_prezzo)],
            colonne=colonne_senza_livello_um,
        )

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []
        assert righe[0].campi_presenti is not None
        assert "livello" not in righe[0].campi_presenti
        assert "um" not in righe[0].campi_presenti

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert scarti_diff == []
        assert len(nuove) == 0
        assert len(modificate) == 1
        assert modificate[0].campi_modificati == ["prezzo_unitario_cliente"]

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [], [r.riga for r in modificate]
        )
        session.commit()
        session.expire_all()

        voce_dopo = session.get(Voce, voce.id)
        assert voce_dopo.livello == livello_prima
        assert voce_dopo.um == um_prima
        assert voce_dopo.prezzo_unitario_cliente == nuovo_prezzo


class TestTokenCancella:
    def test_token_cancella_azzera_solo_quel_campo(self, session):
        """Il token #CANCELLA# su `livello` porta il campo a `None`, senza
        toccare nessun altro campo della stessa riga."""
        listino = _listino(session)
        voce, sotto = _voci_con_sotto(session, listino)[0]
        voce.livello = "alto"
        session.commit()

        prezzo_prima = voce.prezzo_unitario_cliente
        um_prima = voce.um
        descrizione_prima = voce.descrizione
        ordine_prima = voce.ordine

        xlsx_bytes = _xlsx_piatto([_riga_completa(voce, sotto, livello=TOKEN_CANCELLA)])

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []
        assert righe[0].livello is None
        assert "livello" in righe[0].campi_presenti

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert scarti_diff == []
        assert len(modificate) == 1
        assert modificate[0].campi_modificati == ["livello"]

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [], [r.riga for r in modificate]
        )
        session.commit()
        session.expire_all()

        voce_dopo = session.get(Voce, voce.id)
        assert voce_dopo.livello is None
        assert voce_dopo.prezzo_unitario_cliente == prezzo_prima
        assert voce_dopo.um == um_prima
        assert voce_dopo.descrizione == descrizione_prima
        assert voce_dopo.ordine == ordine_prima


class TestNessunaEliminazione:
    def test_import_non_elimina_mai_righe(self, session):
        """D-10: un file che contiene solo 3 delle N voci del listino non
        fa sparire le altre — l'import e' solo additivo/aggiornante."""
        listino = _listino(session)
        voci_con_sotto = _voci_con_sotto(session, listino)
        assert len(voci_con_sotto) >= 3, "seed atteso: almeno tre voci su RE"

        count_prima = session.query(Voce).count()

        sottoinsieme = voci_con_sotto[:3]
        righe_file = [
            _riga_completa(v, s, prezzo_unitario_cliente=v.prezzo_unitario_cliente + Decimal("1.00"))
            for v, s in sottoinsieme
        ]
        xlsx_bytes = _xlsx_piatto(righe_file)

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert scarti_diff == []
        assert len(modificate) == 3

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [], [r.riga for r in modificate]
        )
        session.commit()

        count_dopo = session.query(Voce).count()
        assert count_dopo == count_prima


class TestRigaSenzaId:
    def test_riga_senza_id_crea_una_voce_nuova(self, session):
        """D-04: una riga con `id` vuoto e chiave naturale nuova produce un
        insert, mai un aggiornamento a caso."""
        listino = _listino(session)
        voce0, sotto0 = _voci_con_sotto(session, listino)[0]
        count_prima = session.query(Voce).count()

        xlsx_bytes = _xlsx_piatto(
            [
                _riga_completa(
                    voce0,
                    sotto0,
                    id=None,
                    codice=None,
                    descrizione="Voce round-trip creata da test",
                    prezzo_unitario_cliente=Decimal("12.34"),
                )
            ]
        )

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []
        assert righe[0].id is None

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert scarti_diff == []
        assert len(nuove) == 1
        assert len(modificate) == 0

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [r.riga for r in nuove], []
        )
        session.commit()

        count_dopo = session.query(Voce).count()
        assert count_dopo == count_prima + 1
        nuova = session.query(Voce).filter_by(descrizione="Voce round-trip creata da test").one()
        assert nuova.prezzo_unitario_cliente == Decimal("12.34")


class TestRigaSenzaIdNonAzzeraCampiAssenti:
    """CR-01: anche il percorso per CHIAVE NATURALE deve rispettare
    `campi_presenti`.

    Le classi qui sopra (`TestPreservazioneCampi`, `TestColonnaAssenteNonAzzera`,
    `TestTokenCancella`) lavorano tutte su righe con un `id` vero, cioe' sul
    percorso `_resolve_per_id` + `_applica_voce`, che la disciplina "campo
    assente = campo non toccato" la rispettava gia'. `TestRigaSenzaId` copre
    il percorso per chiave naturale, ma solo creando una sottocategoria e una
    voce entrambe nuove: li' non c'e' niente da sovrascrivere e il difetto non
    si vede. Restava scoperto — e rotto — il caso normale: aggiungere una voce
    a una sottocategoria che esiste gia'.
    """

    def test_voce_nuova_non_riscrive_l_ordine_della_sottocategoria_esistente(self, session):
        """Il modo documentato di aggiungere una voce dal file piatto e'
        lasciare vuota la cella `id`. `sottocategoria_ordine` non e' fra i
        campi richiesti per una riga nuova, quindi la cella puo' restare
        vuota: in quel caso l'ordine della sottocategoria ESISTENTE deve
        restare quello che era, non lo `0` di placeholder."""
        listino = _listino(session)
        voce0, sotto0 = _voci_con_sotto(session, listino)[0]
        sotto0.ordine = 42
        session.commit()

        xlsx_bytes = _xlsx_piatto(
            [
                _riga_completa(
                    voce0,
                    sotto0,
                    id=None,
                    codice=None,
                    descrizione="Voce nuova sotto una sottocategoria esistente",
                    prezzo_unitario_cliente=Decimal("77.00"),
                    # celle lasciate vuote dall'admin: non devono toccare nulla
                    sottocategoria_ordine=None,
                    ordine=None,
                )
            ]
        )

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []
        assert righe[0].id is None
        assert righe[0].campi_presenti is not None
        assert "sottocategoria_ordine" not in righe[0].campi_presenti

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert scarti_diff == []
        assert len(nuove) == 1

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [r.riga for r in nuove], []
        )
        session.commit()
        session.expire_all()

        sotto_dopo = session.get(Sottocategoria, sotto0.id)
        assert sotto_dopo.ordine == 42, "l'ordine della sottocategoria esistente e' stato azzerato"
        # la voce nuova e' stata comunque creata, agganciata alla stessa sottocategoria
        nuova = (
            session.query(Voce)
            .filter_by(descrizione="Voce nuova sotto una sottocategoria esistente")
            .one()
        )
        assert nuova.sottocategoria_id == sotto0.id

    def test_voce_esistente_risolta_per_chiave_naturale_non_perde_l_ordine(self, session):
        """Se l'admin cancella per sbaglio la cella `id` di una riga che sta
        modificando, la riga ricade sul percorso per chiave naturale. Deve
        aggiornare il campo che ha toccato (il prezzo) e lasciare stare
        quello che ha lasciato vuoto (`ordine`)."""
        listino = _listino(session)
        voce0, sotto0 = _voci_con_sotto(session, listino)[0]
        voce0.ordine = 7
        sotto0.ordine = 42
        session.commit()
        nuovo_prezzo = voce0.prezzo_unitario_cliente + Decimal("3.00")

        xlsx_bytes = _xlsx_piatto(
            [
                _riga_completa(
                    voce0,
                    sotto0,
                    id=None,
                    prezzo_unitario_cliente=nuovo_prezzo,
                    sottocategoria_ordine=None,
                    ordine=None,
                )
            ]
        )

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []
        assert righe[0].id is None
        assert "ordine" not in righe[0].campi_presenti

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert scarti_diff == []
        assert len(nuove) == 0
        assert len(modificate) == 1

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [], [r.riga for r in modificate]
        )
        session.commit()
        session.expire_all()

        voce_dopo = session.get(Voce, voce0.id)
        assert voce_dopo.prezzo_unitario_cliente == nuovo_prezzo
        assert voce_dopo.ordine == 7, "l'ordine della voce esistente e' stato azzerato"
        assert session.get(Sottocategoria, sotto0.id).ordine == 42

    def test_i_campi_presenti_vengono_comunque_scritti(self, session):
        """Contro-prova: la guardia non deve diventare "non scrivere mai
        niente". Quando le celle ci sono, il percorso per chiave naturale
        aggiorna sia la voce sia la sottocategoria."""
        listino = _listino(session)
        voce0, sotto0 = _voci_con_sotto(session, listino)[0]
        voce0.ordine = 7
        sotto0.ordine = 42
        session.commit()

        xlsx_bytes = _xlsx_piatto(
            [_riga_completa(voce0, sotto0, id=None, sottocategoria_ordine=99, ordine=11)]
        )

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []
        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert scarti_diff == []
        assert len(modificate) == 1

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [], [r.riga for r in modificate]
        )
        session.commit()
        session.expire_all()

        assert session.get(Voce, voce0.id).ordine == 11
        assert session.get(Sottocategoria, sotto0.id).ordine == 99


class TestDiffDichiaraICampiDiSottocategoria:
    """WR-01: sul percorso per CHIAVE NATURALE il diff deve confrontare
    anche i campi di sottocategoria, perche' la conferma li scrive.

    `compute_diff` valorizzava `sotto` solo sul ramo per id; sul ramo per
    chiave naturale restava None e il confronto su
    `_CAMPI_DIFF_SOTTOCATEGORIA` non veniva mai eseguito. Intanto
    `apply_diff_idempotent` chiama `_upsert_sottocategoria`, che quei campi
    li scrive eccome. Il risultato erano due difetti speculari: una modifica
    di sola sottocategoria spariva dal diff (e dall'import), e una modifica
    mista faceva confermare all'admin una scrittura che non gli era stata
    mostrata.
    """

    def test_modifica_di_sola_sottocategoria_non_sparisce_dal_diff(self, session):
        """Nessun campo di voce cambia: prima la riga non compariva affatto
        nel diff e la modifica era persa in silenzio — nessuno scarto,
        nessun avviso."""
        listino = _listino(session)
        voce0, sotto0 = _voci_con_sotto(session, listino)[0]
        sotto0.ordine = 42
        session.commit()

        xlsx_bytes = _xlsx_piatto([_riga_completa(voce0, sotto0, id=None, sottocategoria_ordine=99)])

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []
        assert righe[0].id is None

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert scarti_diff == []
        assert len(nuove) == 0
        assert len(modificate) == 1, "la modifica alla sottocategoria non compare nel diff"
        assert modificate[0].campi_modificati == ["sottocategoria_ordine"]

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [], [r.riga for r in modificate]
        )
        session.commit()
        session.expire_all()

        assert session.get(Sottocategoria, sotto0.id).ordine == 99

    def test_il_diff_dichiara_ogni_campo_di_sottocategoria_che_la_conferma_scrivera(self, session):
        """Il caso che conta: cambiano insieme un campo di voce e due di
        sottocategoria. La riga finiva in `modificate` per il solo campo di
        voce, e la conferma scriveva anche gli altri due — mai mostrati."""
        listino = _listino(session)
        voce0, sotto0 = _voci_con_sotto(session, listino)[0]
        sotto0.ordine = 42
        sotto0.famiglia = "fam-prima"
        session.commit()
        nuovo_prezzo = voce0.prezzo_unitario_cliente + Decimal("5.00")

        xlsx_bytes = _xlsx_piatto(
            [
                _riga_completa(
                    voce0,
                    sotto0,
                    id=None,
                    prezzo_unitario_cliente=nuovo_prezzo,
                    sottocategoria_ordine=99,
                    sottocategoria_famiglia="fam-curata",
                )
            ]
        )

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []
        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert scarti_diff == []
        assert len(modificate) == 1

        annunciati = set(modificate[0].campi_modificati)
        assert annunciati == {
            "prezzo_unitario_cliente",
            "sottocategoria_ordine",
            "sottocategoria_famiglia",
        }

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [], [r.riga for r in modificate]
        )
        session.commit()
        session.expire_all()

        # Cio' che e' stato scritto e' esattamente cio' che era stato annunciato.
        sotto_dopo = session.get(Sottocategoria, sotto0.id)
        assert session.get(Voce, voce0.id).prezzo_unitario_cliente == nuovo_prezzo
        assert sotto_dopo.ordine == 99
        assert sotto_dopo.famiglia == "fam-curata"


class TestLivelloSulPercorsoPerChiaveNaturale:
    """WR-02: l'anteprima annunciava una modifica a `livello` che la
    conferma non applicava mai.

    `livello` e' fra i campi diffati (`_CAMPI_DIFF_VOCE`) ma `_upsert_voce`
    lo escludeva dal ciclo di scrittura, per la ragione — corretta — che le
    righe di `parse_computo` si dichiarano complete e scriverebbero `None`
    su ogni voce. La condizione giusta non e' pero' "ramo per id si, per
    chiave naturale no", ma "il file dichiara esplicitamente il campo":
    `campi_presenti is None` (computo) non vale come dichiarazione,
    `campi_presenti` valorizzato (file piatto) si'.

    L'admin che cura i livelli a mano dal file piatto vedeva il diff giusto,
    confermava, e non trovava la modifica applicata — senza nessun
    messaggio, e con la riga contata comunque fra le `righe_importate`.
    """

    def test_il_livello_annunciato_nel_diff_viene_davvero_scritto(self, session):
        listino = _listino(session)
        voce0, sotto0 = _voci_con_sotto(session, listino)[0]
        voce0.livello = "alto"
        session.commit()

        xlsx_bytes = _xlsx_piatto([_riga_completa(voce0, sotto0, id=None, livello="medio")])

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []
        assert righe[0].id is None
        assert "livello" in righe[0].campi_presenti

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert scarti_diff == []
        assert len(modificate) == 1
        assert modificate[0].campi_modificati == ["livello"]

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [], [r.riga for r in modificate]
        )
        session.commit()
        session.expire_all()

        assert session.get(Voce, voce0.id).livello == "medio", (
            "l'anteprima aveva annunciato la modifica a livello, la conferma non l'ha applicata"
        )

    def test_il_computo_continua_a_non_azzerare_il_livello(self, session):
        """Contro-prova, e la ragione per cui `livello` era escluso: una
        riga che si dichiara completa ma viene da `parse_computo`
        (`campi_presenti is None`) non deve scrivere il `None` che porta
        addosso. Senza questa distinzione il fix azzererebbe la curatela a
        ogni ri-caricamento del computo."""
        listino = _listino(session)
        voce0, sotto0 = _voci_con_sotto(session, listino)[0]
        voce0.livello = "alto"
        session.commit()

        riga_da_computo = VoceRigaIn(
            id=None,
            categoria_code=sotto0.categoria_code,
            sottocategoria_codice=sotto0.codice,
            sottocategoria_nome=sotto0.nome,
            sottocategoria_famiglia=sotto0.famiglia,
            sottocategoria_ordine=sotto0.ordine,
            codice=voce0.codice,
            descrizione=voce0.descrizione,
            um=voce0.um,
            prezzo_unitario_cliente=voce0.prezzo_unitario_cliente,
            ordine=voce0.ordine,
            livello=None,
            campi_presenti=None,
        )

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [], [riga_da_computo]
        )
        session.commit()
        session.expire_all()

        assert session.get(Voce, voce0.id).livello == "alto"

    def test_una_voce_nuova_dal_file_piatto_conserva_il_livello_dichiarato(self, session):
        """Stesso principio sul ramo "voce nuova": il livello dichiarato nel
        file non deve perdersi fra la riga letta e la riga creata."""
        listino = _listino(session)
        voce0, sotto0 = _voci_con_sotto(session, listino)[0]

        xlsx_bytes = _xlsx_piatto(
            [
                _riga_completa(
                    voce0,
                    sotto0,
                    id=None,
                    codice=None,
                    descrizione="Voce nuova con livello curato",
                    livello="medio",
                )
            ]
        )

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []
        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert scarti_diff == []
        assert len(nuove) == 1

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [r.riga for r in nuove], []
        )
        session.commit()
        session.expire_all()

        creata = session.query(Voce).filter_by(descrizione="Voce nuova con livello curato").one()
        assert creata.livello == "medio"

    def test_il_token_cancella_azzera_il_livello_anche_senza_id(self, session):
        """`livello` e' fra le colonne nullable, quindi `#CANCELLA#` e' una
        dichiarazione esplicita a tutti gli effetti: il campo compare in
        `campi_presenti` con valore `None` e la scrittura deve avvenire."""
        listino = _listino(session)
        voce0, sotto0 = _voci_con_sotto(session, listino)[0]
        voce0.livello = "alto"
        session.commit()

        xlsx_bytes = _xlsx_piatto([_riga_completa(voce0, sotto0, id=None, livello=TOKEN_CANCELLA)])

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []
        assert righe[0].livello is None
        assert "livello" in righe[0].campi_presenti

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert len(modificate) == 1

        apply_diff_idempotent(
            session, UploadTargetEsistente(listino_id=listino.id), [], [r.riga for r in modificate]
        )
        session.commit()
        session.expire_all()

        assert session.get(Voce, voce0.id).livello is None


class TestIdInesistente:
    def test_id_inesistente_finisce_negli_scarti(self, session):
        """T-08-23: un id che non esiste nel listino di destinazione
        diventa uno scarto con un motivo leggibile, mai un update silenzioso
        e mai un insert con id diverso."""
        listino = _listino(session)
        voce0, sotto0 = _voci_con_sotto(session, listino)[0]
        id_inesistente = max(v.id for v, _ in _voci_con_sotto(session, listino)) + 100000
        count_prima = session.query(Voce).count()

        xlsx_bytes = _xlsx_piatto([_riga_completa(voce0, sotto0, id=id_inesistente)])

        righe, scarti = parse_flat_listino(xlsx_bytes)
        assert scarti == []
        assert righe[0].id == id_inesistente

        nuove, modificate, scarti_diff = compute_diff(session, righe, listino)
        assert nuove == []
        assert modificate == []
        assert len(scarti_diff) == 1
        assert str(id_inesistente) in scarti_diff[0].motivo

        count_dopo = session.query(Voce).count()
        assert count_dopo == count_prima


_TOTALE_ALLESTIMENTO_ROW = (None, "TOTALE ALLESTIMENTO DI CANTIERE", None, None, None)


def _xlsx_computo_minimo() -> bytes:
    """Un .xlsx minimo nel formato del computo originale (nessun foglio
    ISTRUZIONI): stessa forma di `test_upload_listino.py::_build_xlsx`,
    duplicata qui in miniatura per non accoppiare i due file di test. La
    riga di confine "TOTALE ALLESTIMENTO DI CANTIERE" precede sempre le
    righe vere, altrimenti `extract_a_edile` le classifica nel blocco
    sintetico A.0 invece che nella gerarchia A.n/A.n.m."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "A-EDILE"
    ws.append((None, *_TOTALE_ALLESTIMENTO_ROW))
    ws.append((None, "A.1", "DEMOLIZIONI - RIMOZIONI", None, None, None))
    ws.append((None, "A.1.1", "Demolizione muratura", "mq", 0, 25.50))

    wb.create_sheet("B-FINITURE")
    wb.create_sheet("C- SERRAMENTI PORTE  ")
    wb.create_sheet("D- PRODOTTI")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture()
def client(monkeypatch, tmp_path):
    limiter.reset()
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "admin.roundtrip@example.com")

    db_path = tmp_path / "test_export_import_roundtrip.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessione_di_test(engine)

    with testing_session_local() as s:
        seed(s, load_seed_data())

    monkeypatch.setattr(db_module, "SessionLocal", testing_session_local)

    import app.dependencies.auth as deps_auth_module
    import app.routers.auth as auth_router_module

    monkeypatch.setattr(deps_auth_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(auth_router_module, "SessionLocal", testing_session_local)

    return TestClient(app)


class TestComputoOriginaleAccettato:
    def test_computo_originale_ancora_accettato(self, client):
        """D-01: il file del computo originale continua a caricarsi da
        `/preview` esattamente come prima — instradato a `parse_computo`,
        non al lettore del formato piatto (che richiede ISTRUZIONI)."""
        client.post(
            REGISTRAZIONE_URL,
            json={"email": "admin.roundtrip@example.com", "password": "Password123", "nome": "Admin Roundtrip"},
        )
        listino_id = next(
            r["id"] for r in client.get(LISTINI_URL).json() if r["citta_riferimento"] == "Reggio Emilia"
        )

        response = client.post(
            f"{UPLOAD_URL}/preview",
            files={
                "file": (
                    "computo.xlsx",
                    _xlsx_computo_minimo(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={"target": f'{{"kind": "esistente", "listino_id": {listino_id}}}'},
        )

        assert response.status_code == 200
        body = response.json()
        assert any(r["riga"]["descrizione"] == "Demolizione muratura" for r in body["nuove"])


class TestContrattoDiffRowSulFilo:
    """WR-03: `id` e `campi_presenti` devono essere SUL FILO in ogni riga di
    `/preview`.

    Il tipo TypeScript `VoceRiga` (`frontend/src/api/admin/uploadListino.ts`)
    li dichiara, e la correttezza del percorso per id dipende dal fatto che
    sopravvivano al giro preview -> confirm: senza `id` la riga cade
    sull'upsert per chiave naturale, senza `campi_presenti` i placeholder
    delle colonne assenti verrebbero scritti a database come se fossero
    dati veri (CR-01).

    Questo test e' il presidio lato server di quel contratto: se un domani
    la risposta smettesse di portarli, il tipo TS tornerebbe a mentire e
    qui si vedrebbe subito.
    """

    CAMPI_ATTESI = {
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
        "campi_presenti",
    }

    def test_preview_del_formato_piatto_porta_id_e_campi_presenti(self, client, session):
        client.post(
            REGISTRAZIONE_URL,
            json={"email": "admin.roundtrip@example.com", "password": "Password123", "nome": "Admin Roundtrip"},
        )
        listino_id = next(
            r["id"] for r in client.get(LISTINI_URL).json() if r["citta_riferimento"] == "Reggio Emilia"
        )

        # export reale del listino, con una voce ritoccata perche' il diff
        # non sia vuoto e ci sia almeno una riga da ispezionare
        with db_module.SessionLocal() as db:
            xlsx_bytes, _ = build_workbook_listino(db, listino_id)
            voce = (
                db.query(Voce)
                .join(Sottocategoria, Voce.sottocategoria_id == Sottocategoria.id)
                .filter(Sottocategoria.listino_id == listino_id)
                .order_by(Voce.id)
                .first()
            )
            voce_id = voce.id
            nuovo_prezzo = float(voce.prezzo_unitario_cliente) + 9

        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
        ws = wb["voci"]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        for row in ws.iter_rows(min_row=2):
            if str(row[header.index("id")].value) == str(voce_id):
                row[header.index("prezzo_unitario_cliente")].value = nuovo_prezzo
                break
        buf = io.BytesIO()
        wb.save(buf)

        response = client.post(
            f"{UPLOAD_URL}/preview",
            files={
                "file": (
                    "listino.xlsx",
                    buf.getvalue(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={"target": f'{{"kind": "esistente", "listino_id": {listino_id}}}'},
        )

        assert response.status_code == 200
        body = response.json()
        righe = [*body["nuove"], *body["modificate"]]
        assert righe, "il file ritoccato deve produrre almeno una riga nel diff"

        for r in righe:
            assert set(r["riga"].keys()) == self.CAMPI_ATTESI, (
                "il contratto di VoceRigaIn sul filo e' cambiato: aggiornare "
                "anche l'interfaccia VoceRiga in frontend/src/api/admin/uploadListino.ts"
            )
            assert r["riga"]["campi_presenti"] is not None
            assert "prezzo_unitario_cliente" in r["riga"]["campi_presenti"]
            # WR-03: Decimal-as-string al confine API. Il valore arriva al
            # client come STRINGA JSON, non come number — `"12.50"`, non
            # `12.5`. Vale per il prezzo dentro `riga` e per
            # `valore_precedente`, che sono entrambi `Decimal` pydantic.
            assert isinstance(r["riga"]["prezzo_unitario_cliente"], str), (
                "prezzo_unitario_cliente non e' piu' una stringa sul filo: "
                "aggiornare il tipo in frontend/src/api/admin/uploadListino.ts"
            )
            if r["valore_precedente"] is not None:
                assert isinstance(r["valore_precedente"], str)

        modificata = next(r for r in body["modificate"] if r["riga"]["id"] == voce_id)
        assert modificata["riga"]["id"] == voce_id


def _forma_json(annotazione: object) -> str:
    """Riduce un'annotazione pydantic alla forma che il campo assume in
    JSON. `Decimal -> "string"` non e' un'approssimazione: e' la convenzione
    Decimal-as-string del progetto, ed e' esattamente il punto che il
    confronto sui soli nomi non vedeva."""
    args = [a for a in get_args(annotazione) if a is not type(None)]
    if args:
        annotazione = args[0]
    if get_origin(annotazione) in (list, set, tuple, frozenset):
        return "array"
    if annotazione is bool:  # prima di int: bool e' sottoclasse di int
        return "boolean"
    if annotazione is Decimal or annotazione is str:
        return "string"
    if annotazione in (int, float):
        return "number"
    return str(annotazione)


def _forma_ts(tipo: str) -> str:
    """Stessa riduzione, dal lato TypeScript: `string[] | null` -> "array",
    `number | null` -> "number"."""
    tipo = tipo.strip()
    if "[]" in tipo:
        return "array"
    for primitivo in ("string", "number", "boolean"):
        if re.search(rf"\b{primitivo}\b", tipo):
            return primitivo
    return tipo


class TestContrattoVoceRigaTypeScript:
    """WR-03: l'interfaccia TS `VoceRiga` deve elencare gli STESSI campi di
    `VoceRigaIn`.

    Il tipo TypeScript e' l'unica descrizione del contratto dal lato client,
    e finche' taceva `id` e `campi_presenti` funzionava solo per caso:
    `normalizeDiffRow` passa `raw.riga` cosi' com'e' e `ExcelUploadDialog`
    rispedisce lo stesso oggetto, quindi i campi sopravvivevano pur non
    essendo dichiarati. Il primo pezzo di codice che ricostruisse una
    `VoceRiga` campo per campo li perderebbe in silenzio, e ogni riga
    cadrebbe sull'upsert per chiave naturale con i placeholder addosso
    (CR-01).

    Il frontend non ha un test runner: questo confronto e' il solo modo di
    tenere le due dichiarazioni allineate automaticamente.

    Confronta i NOMI e la FORMA JSON dei tipi. La sola verifica dei nomi
    dava una sicurezza che non aveva: `prezzo_unitario_cliente` era
    dichiarato `number` mentre sul filo e' una stringa (pydantic serializza
    `Decimal` come stringa JSON), e il test passava lo stesso — mentre a
    schermo la colonna "nuovo" della tabella di anteprima mostrava `12.50`
    grezzo invece di `12,50 €`, perche'
    `String.prototype.toLocaleString` ignora gli argomenti.
    """

    PERCORSO_TS = "frontend/src/api/admin/uploadListino.ts"

    def _corpo_interfaccia(self) -> str:
        radice = Path(__file__).resolve().parents[2]
        if not (radice / "frontend").is_dir():
            # Checkout del solo backend (es. immagine Docker): non c'e'
            # niente da confrontare. Lo skip vale SOLO per l'assenza
            # dell'intera cartella — se c'e' ma il file manca, e' un errore.
            pytest.skip("cartella frontend assente: checkout di solo backend")

        percorso = radice / self.PERCORSO_TS
        assert percorso.exists(), f"atteso {self.PERCORSO_TS} (il file e' stato spostato?)"

        sorgente = percorso.read_text(encoding="utf-8")
        corpo = re.search(r"export interface VoceRiga \{(.*?)\n\}", sorgente, re.DOTALL)
        assert corpo is not None, "interfaccia VoceRiga non trovata in uploadListino.ts"
        return corpo.group(1)

    def test_voce_riga_ts_elenca_gli_stessi_campi_di_voce_riga_in(self):
        campi_ts = set(re.findall(r"^\s{2}(\w+)\??:", self._corpo_interfaccia(), re.MULTILINE))
        campi_py = set(VoceRigaIn.model_fields)

        assert campi_ts == campi_py, (
            "VoceRiga (TypeScript) e VoceRigaIn (pydantic) sono disallineati.\n"
            f"  solo in TS:     {sorted(campi_ts - campi_py)}\n"
            f"  solo in Python: {sorted(campi_py - campi_ts)}"
        )

    def test_voce_riga_ts_dichiara_la_forma_json_giusta_per_ogni_campo(self):
        """WR-03: il confronto sui soli nomi non basta.

        Riduce entrambe le dichiarazioni alla forma JSON che il campo ha
        davvero sul filo (`string`/`number`/`boolean`/`array`) e le mette a
        confronto. La riduzione e' volutamente grossolana — non prova a
        confrontare la nullabilita' — ma intercetta l'errore che conta: un
        `Decimal` dichiarato `number` in TypeScript.
        """
        attesi = {nome: _forma_json(campo.annotation) for nome, campo in VoceRigaIn.model_fields.items()}
        dichiarati = {
            nome: _forma_ts(tipo)
            for nome, tipo in re.findall(r"^\s{2}(\w+)\??:\s*([^;]+);", self._corpo_interfaccia(), re.MULTILINE)
        }

        disallineati = {
            nome: (attesi[nome], dichiarati.get(nome))
            for nome in attesi
            if dichiarati.get(nome) != attesi[nome]
        }
        assert not disallineati, (
            "VoceRiga (TypeScript) dichiara tipi che non corrispondono alla forma "
            "JSON di VoceRigaIn. Nota che pydantic serializza `Decimal` come "
            "STRINGA, non come number (convenzione Decimal-as-string del "
            "progetto).\n"
            + "\n".join(
                f"  {nome}: atteso {atteso!r}, dichiarato {dichiarato!r}"
                for nome, (atteso, dichiarato) in sorted(disallineati.items())
            )
        )
