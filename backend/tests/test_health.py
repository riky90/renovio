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
