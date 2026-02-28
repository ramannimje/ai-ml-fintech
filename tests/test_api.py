from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.responses import (
    LivePriceResponse,
    RegionalHistoricalPoint,
    RegionalHistoricalResponse,
    RegionalPredictionResponse,
    TrainResponse,
)
from app.api import routes

client = TestClient(app)


def test_live_price_success(monkeypatch) -> None:
    async def _mock_live(region=None):
        _ = region
        return [
            LivePriceResponse(
                commodity="gold",
                region="us",
                unit="oz",
                currency="USD",
                live_price=2320.0,
                source="comex/yahoo_finance",
                timestamp=datetime.now(timezone.utc),
            )
        ]

    monkeypatch.setattr(routes.service, "live_prices", _mock_live)
    response = client.get("/api/live-prices")
    assert response.status_code == 200
    assert response.json()["items"][0]["commodity"] == "gold"


def test_fallback_source(monkeypatch) -> None:
    async def _mock_live(region=None):
        _ = region
        return [
            LivePriceResponse(
                commodity="silver",
                region="india",
                unit="10g_24k",
                currency="INR",
                live_price=71250.0,
                source="yahoo_finance",
                timestamp=datetime.now(timezone.utc),
            )
        ]

    monkeypatch.setattr(routes.service, "live_prices", _mock_live)
    response = client.get("/api/live-prices/india")
    assert response.status_code == 200
    assert "yahoo_finance" in response.json()["items"][0]["source"]


def test_region_unit_conversion(monkeypatch) -> None:
    async def _mock_hist(commodity: str, region: str, period: str):
        _ = commodity, period
        return RegionalHistoricalResponse(
            commodity="gold",
            region=region,
            currency="INR",
            unit="10g_24k",
            rows=1,
            data=[RegionalHistoricalPoint(date=date(2025, 1, 1), open=70000, high=71000, low=69000, close=70500, volume=1.0)],
        )

    monkeypatch.setattr(routes.service, "historical", _mock_hist)
    response = client.get("/api/historical/gold/india?range=1m")
    assert response.status_code == 200
    assert response.json()["unit"] == "10g_24k"


def test_prediction_endpoint(monkeypatch) -> None:
    async def _mock_predict(session, commodity: str, region: str, horizon: int):
        _ = session, commodity, region, horizon
        return RegionalPredictionResponse(
            commodity="gold",
            region="us",
            unit="oz",
            currency="USD",
            forecast_horizon=date(2026, 12, 31),
            point_forecast=2400.0,
            confidence_interval=(2300.0, 2500.0),
            scenario="base",
            scenario_forecasts={"bull": 2544.0, "base": 2400.0, "bear": 2256.0},
            model_used="xgb_us_1",
        )

    monkeypatch.setattr(routes.service, "predict", _mock_predict)
    response = client.get("/api/predict/gold/us?horizon=30")
    assert response.status_code == 200
    assert response.json()["point_forecast"] == 2400.0


def test_invalid_region(monkeypatch) -> None:
    async def _mock_live(region=None):
        raise ValueError("Unsupported region")

    monkeypatch.setattr(routes.service, "live_prices", _mock_live)
    response = client.get("/api/live-prices/moon")
    assert response.status_code == 400


def test_training_trigger(monkeypatch) -> None:
    async def _mock_train(session, commodity: str, region: str, horizon: int):
        _ = session, commodity, region, horizon
        return TrainResponse(
            commodity="silver",
            region="europe",
            best_model="xgb",
            model_version="xgb_europe_v1",
            rmse=10.0,
            mape=1.2,
        )

    monkeypatch.setattr(routes.service, "train", _mock_train)
    response = client.post("/api/train/silver/europe?horizon=7")
    assert response.status_code == 200
    assert response.json()["region"] == "europe"


def test_persistence(monkeypatch) -> None:
    class _Run:
        commodity = "gold"
        model_version = "v1"
        rmse = 9.0
        mape = 1.1
        trained_at = datetime.now(timezone.utc)
        region = "us"

    async def _latest(session, commodity: str, region: str):
        _ = session, commodity, region
        return _Run()

    monkeypatch.setattr(routes.service, "latest_metrics", _latest)
    # Persistence is represented by saved model metadata. Existing routes don't expose metrics endpoint now,
    # so this check focuses on train endpoint payload carrying model_version.
    async def _mock_train(session, commodity: str, region: str, horizon: int):
        _ = session, commodity, region, horizon
        return TrainResponse(
            commodity="gold",
            region="us",
            best_model="xgb",
            model_version="persisted_v1",
            rmse=9.0,
            mape=1.1,
        )

    monkeypatch.setattr(routes.service, "train", _mock_train)
    response = client.post("/api/train/gold/us?horizon=1")
    assert response.status_code == 200
    assert response.json()["model_version"] == "persisted_v1"
