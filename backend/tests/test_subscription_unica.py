"""Una tessera per utente: migrazione 0036 e corsa fra webhook e conferma."""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.db import Base
from app.models.subscription import Subscription
from app.models.user import User
from app.services.pagamenti import tessera_di
from tests.session_factory import sessione_di_test


def _migrazione():
    percorso = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0036_subscription_unica.py"
    spec = importlib.util.spec_from_file_location("migrazione_0036", percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture()
def engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    with sessione_di_test(engine)() as s:
        s.add_all([User(id=1, email="a@x.it", nome="A"), User(id=2, email="b@x.it", nome="B")])
        s.commit()
    return engine


def _come_prima_della_0036(conn):
    conn.execute(text("DROP INDEX ix_subscription_user_id"))
    conn.execute(text("CREATE INDEX ix_subscription_user_id ON subscription (user_id)"))


def test_0036_unisce_i_doppioni_senza_perdere_nulla(engine, monkeypatch):
    m = _migrazione()
    with engine.begin() as conn:
        _come_prima_della_0036(conn)
        ins = text(
            "INSERT INTO subscription (id, user_id, stato, scaduta_il, stripe_customer_id,"
            " stripe_subscription_id, cancella_a_fine_periodo, acquistato_il, receduto_il)"
            " VALUES (:id, :u, :stato, :scad, :cus, :sub, 0, :acq, :rec)"
        )
        righe = [
            # utente 1: la riga col abbonamento Stripe vince; cliente e recesso
            # arrivano dalle altre.
            dict(id=1, u=1, stato="inattivo", scad=None, cus="cus_1", sub=None, acq=None,
                 rec=datetime(2026, 5, 1)),
            dict(id=2, u=1, stato="attivo", scad=datetime(2026, 12, 1), cus=None, sub="sub_1",
                 acq=datetime(2026, 4, 1), rec=None),
            dict(id=3, u=1, stato="attivo", scad=datetime(2027, 1, 1), cus=None, sub=None, acq=None,
                 rec=datetime(2026, 6, 1)),
            # utente 2: una sola riga, non si tocca.
            dict(id=4, u=2, stato="attivo", scad=None, cus=None, sub=None, acq=None, rec=None),
        ]
        for r in righe:
            conn.execute(ins, r)

        monkeypatch.setattr(m, "op", Operations(MigrationContext.configure(conn)))
        m.upgrade()

        rimaste = conn.execute(
            text(
                "SELECT id, user_id, stripe_customer_id, stripe_subscription_id, receduto_il"
                " FROM subscription ORDER BY id"
            )
        ).all()
        assert [(r.id, r.user_id) for r in rimaste] == [(2, 1), (4, 2)]
        tenuta = rimaste[0]
        assert tenuta.stripe_customer_id == "cus_1"
        assert tenuta.stripe_subscription_id == "sub_1"
        assert str(tenuta.receduto_il).startswith("2026-05-01")

        with pytest.raises(IntegrityError):
            conn.execute(text("INSERT INTO subscription (user_id, stato, cancella_a_fine_periodo) VALUES (1, 'x', 0)"))


def test_tessera_di_non_duplica(engine):
    factory = sessione_di_test(engine)
    with factory() as s:
        prima = tessera_di(s, 1)
        s.commit()
        seconda = tessera_di(s, 1)
        assert prima.id == seconda.id
        assert s.query(Subscription).filter_by(user_id=1).count() == 1


def test_tessera_di_perde_la_corsa_e_rilegge(engine, monkeypatch):
    """Un'altra richiesta crea la tessera fra la lettura e l'inserimento:
    l'inserimento collide e si rilegge la riga esistente, senza errore."""
    factory = sessione_di_test(engine)
    with factory() as altra:
        altra.add(Subscription(user_id=2, stato="attivo"))
        altra.commit()

    with factory() as s:
        originale = s.query

        chiamate = {"n": 0}

        def query_che_non_vede_la_prima_volta(*args, **kwargs):
            q = originale(*args, **kwargs)
            chiamate["n"] += 1
            if chiamate["n"] == 1:
                return q.filter(text("1 = 0"))
            return q

        monkeypatch.setattr(s, "query", query_che_non_vede_la_prima_volta)
        tessera = tessera_di(s, 2)
        assert tessera.stato == "attivo"
        s.commit()
        assert originale(Subscription).filter_by(user_id=2).count() == 1
