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
from decimal import Decimal

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as db_module
from app.config import settings
from app.db import Base
from app.limiter import limiter
from app.main import app
from app.models.dettaglio_pro import Sottocategoria, Voce
from app.schemas.admin_upload import UploadTargetEsistente
from app.services.city_resolver import resolve_listino
from app.services.export_excel.listino import COLONNE_VOCI, build_workbook_listino
from app.services.export_excel.workbook import TOKEN_CANCELLA, nuovo_workbook, scrivi_foglio_dati, serializza
from app.services.listino_upload_service import (
    apply_diff_idempotent,
    compute_diff,
    parse_flat_listino,
)
from scripts.seed import load_seed_data, seed

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
    testing_session_local = sessionmaker(bind=engine)
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
    testing_session_local = sessionmaker(bind=engine)

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
