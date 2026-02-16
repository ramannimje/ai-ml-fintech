from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_commodities() -> None:
    response = client.get("/api/commodities")
    assert response.status_code == 200
    assert set(response.json()["commodities"]) == {"gold", "silver", "crude_oil"}


def test_historical_region_validation() -> None:
    response = client.get("/api/historical/gold?region=moon")
    assert response.status_code == 404
