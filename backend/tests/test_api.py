from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_commodities() -> None:
    response = client.get("/api/commodities")
    assert response.status_code == 200
    assert set(response.json()["commodities"]) == {"gold", "silver", "crude_oil"}
