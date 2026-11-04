"""Walking Skeleton verification: GET /api/v1/health/db proves Browser -> API
-> DB -> Browser with a real query (not a hardcoded number)."""

from fastapi.testclient import TestClient

from app.main import app


def _db_temporaneo(tmp_path, monkeypatch):
    from sqlalchemy import create_engine

    import app.routers.health as health
    from app.db import Base
    from tests.session_factory import sessione_di_test

    engine = create_engine(f"sqlite:///{tmp_path / 'health.db'}")
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(health, "SessionLocal", sessione_di_test(engine))
    return health


def test_health_db_returns_live_count(tmp_path, monkeypatch):
    health = _db_temporaneo(tmp_path, monkeypatch)
    monkeypatch.setattr(health, "_e_admin", lambda session, session_id: True)
    client = TestClient(app)

    response = client.get("/api/v1/health/db")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["listini"], int)
    assert body["listini"] >= 0


def test_health_db_pubblico_solo_status_e_aggiornato(tmp_path, monkeypatch):
    """Senza sessione admin niente dettagli d'infrastruttura."""
    _db_temporaneo(tmp_path, monkeypatch)
    body = TestClient(app).get("/api/v1/health/db").json()
    assert set(body) == {"status", "aggiornato"}


def test_health_db_dice_la_migrazione_e_la_head(tmp_path, monkeypatch):
    """Su un database creato senza alembic la versione manca: `aggiornato` e'
    falso, ed e' proprio il segnale da guardare in produzione."""
    from pathlib import Path

    from sqlalchemy import create_engine

    import app.routers.health as health
    from app.db import Base
    from tests.session_factory import sessione_di_test

    versioni = sorted(
        p.name.split("_")[0] for p in (Path(__file__).parents[1] / "alembic" / "versions").glob("0*.py")
    )
    assert health._migrazione_head() == versioni[-1]

    engine = create_engine(f"sqlite:///{tmp_path / 'health.db'}")
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(health, "SessionLocal", sessione_di_test(engine))
    monkeypatch.setattr(health, "_e_admin", lambda session, session_id: True)

    body = TestClient(app).get("/api/v1/health/db").json()
    assert body["migrazione"] is None
    assert body["migrazione_head"] == versioni[-1]
    assert body["aggiornato"] is False


def test_health_db_dettagli_con_sessione_admin_vera(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.models.user import User, UserSession

    health = _db_temporaneo(tmp_path, monkeypatch)
    with health.SessionLocal() as s:
        admin = User(email="admin@example.com", nome="Admin", role="admin")
        utente = User(email="utente@example.com", nome="Utente", role="user")
        s.add_all([admin, utente])
        s.flush()
        scadenza = datetime.now(timezone.utc) + timedelta(days=1)
        s.add_all(
            [
                UserSession(id="sess-admin", user_id=admin.id, expires_at=scadenza),
                UserSession(id="sess-utente", user_id=utente.id, expires_at=scadenza),
            ]
        )
        s.commit()

    client = TestClient(app)
    client.cookies.set("session_id", "sess-utente")
    assert set(client.get("/api/v1/health/db").json()) == {"status", "aggiornato"}
    client.cookies.set("session_id", "sess-admin")
    assert "listini" in client.get("/api/v1/health/db").json()
