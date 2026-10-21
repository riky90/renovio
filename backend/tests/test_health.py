"""Walking Skeleton verification: GET /api/v1/health/db proves Browser -> API
-> DB -> Browser with a real query (not a hardcoded number)."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_db_returns_live_count():
    client = TestClient(app)

    response = client.get("/api/v1/health/db")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["listini"], int)
    assert body["listini"] >= 0



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

    body = TestClient(app).get("/api/v1/health/db").json()
    assert body["migrazione"] is None
    assert body["migrazione_head"] == versioni[-1]
    assert body["aggiornato"] is False
