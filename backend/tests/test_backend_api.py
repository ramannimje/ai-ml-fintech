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
    ids = {item["id"] for item in response.json()}
    assert ids == {"gold", "silver", "crude_oil"}
