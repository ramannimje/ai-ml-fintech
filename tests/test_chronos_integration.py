from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.services import commodity_service as commodity_service_module
from app.services.commodity_service import CommodityService
from app.schemas.responses import TrainResponse
from ml.training import models as training_models


def test_benchmark_models_continues_when_chronos_candidate_fails(monkeypatch) -> None:
    class _FailingChronos:
        def __init__(self, prediction_length: int) -> None:
            _ = prediction_length

        def fit(self, x, y) -> None:
            _ = x, y
            raise RuntimeError("boom")

        def predict(self, x):
            return np.zeros(len(x))

    monkeypatch.setattr(training_models, "chronos_bolt_available", lambda: True)
    monkeypatch.setattr(training_models, "ChronosBoltRegressor", _FailingChronos)

    rows = 120
    x = pd.DataFrame(
        {
            "Close": np.linspace(100.0, 130.0, rows),
            "Open": np.linspace(99.0, 129.0, rows),
            "High": np.linspace(101.0, 131.0, rows),
            "Low": np.linspace(98.0, 128.0, rows),
            "Volume": np.linspace(1000.0, 1200.0, rows),
            "returns": np.linspace(0.001, 0.002, rows),
            "ma_5": np.linspace(100.0, 130.0, rows),
            "ma_20": np.linspace(100.0, 130.0, rows),
            "volatility_20": np.linspace(0.01, 0.02, rows),
            "lag_1": np.linspace(100.0, 130.0, rows),
            "lag_7": np.linspace(100.0, 130.0, rows),
            "rolling_min_14": np.linspace(99.0, 129.0, rows),
            "rolling_max_14": np.linspace(101.0, 131.0, rows),
            "rsi": np.linspace(40.0, 60.0, rows),
        }
    )
    y = pd.Series(np.linspace(101.0, 131.0, rows))

    ranked = training_models.benchmark_models(x, y)
    assert ranked, "benchmark should still return non-Chronos candidates"
    assert all(item.name != "chronos_bolt" for item in ranked)


def test_predict_uses_chronos_series_path(monkeypatch) -> None:
    service = CommodityService()

    class _Run:
        commodity = "gold"
        region = "us"
        model_version = "chronos_bolt_us_20260304101010"
        artifact_path = "ml/artifacts/gold/us/chronos_bolt_us_20260304101010.joblib"
        rmse = 15.0
        mape = 1.0
        trained_at = datetime.now(timezone.utc)

    class _ChronosModel:
        def predict(self, x):
            raise AssertionError("feature-based predict path should not be used for chronos_bolt")

        def predict_from_series(self, series, prediction_length: int = 1):
            assert len(series) > 10
            assert prediction_length == 30
            return np.linspace(2000.0, 2100.0, prediction_length)

    async def _latest_metrics(session, commodity: str, region: str):
        _ = session
        assert commodity == "gold"
        assert region == "us"
        return _Run()

    monkeypatch.setattr(service, "latest_metrics", _latest_metrics)
    monkeypatch.setattr(
        commodity_service_module,
        "load_model",
        lambda _path: (_ChronosModel(), {"model_name": "chronos_bolt", "horizon": 30}),
    )
    monkeypatch.setattr(commodity_service_module, "get_fx_rates", lambda: {"USD": 1.0, "INR": 83.5, "EUR": 0.92})
    monkeypatch.setattr(
        service.fetcher,
        "get_historical",
        lambda commodity, region: pd.DataFrame(
            {
                "Date": pd.date_range("2025-01-01", periods=120, freq="D"),
                "Open": np.linspace(1950.0, 2050.0, 120),
                "High": np.linspace(1960.0, 2060.0, 120),
                "Low": np.linspace(1940.0, 2040.0, 120),
                "Close": np.linspace(1955.0, 2055.0, 120),
                "Volume": np.linspace(1000.0, 1200.0, 120),
            }
        ),
    )

    response = asyncio.run(service.predict(session=None, commodity="gold", region="us", horizon=30))
    assert response.model_used == _Run.model_version
    assert response.currency == "USD"
    assert response.unit == "oz"
    assert response.point_forecast == 2100.0
    assert response.confidence_interval[0] < response.point_forecast < response.confidence_interval[1]


def test_predict_does_not_retrain_when_horizon_mismatch(monkeypatch) -> None:
    service = CommodityService()
    state = {"train_called": False}

    class _RunV1:
        commodity = "gold"
        region = "us"
        model_version = "xgb_us_h30"
        artifact_path = "ml/artifacts/gold/us/xgb_us_h30.joblib"
        rmse = 12.0
        mape = 1.0
        trained_at = datetime.now(timezone.utc)

    class _RunV2:
        commodity = "gold"
        region = "us"
        model_version = "xgb_us_h7"
        artifact_path = "ml/artifacts/gold/us/xgb_us_h7.joblib"
        rmse = 11.0
        mape = 0.9
        trained_at = datetime.now(timezone.utc)

    class _Model:
        def predict(self, x):
            _ = x
            return np.array([2050.0])

    async def _latest_metrics(session, commodity: str, region: str):
        _ = session, commodity, region
        return _RunV1()

    async def _train(session, commodity: str, region: str, horizon: int):
        _ = session, commodity, region
        state["train_called"] = True
        return TrainResponse(
            commodity="gold",
            region="us",
            best_model="xgboost",
            model_version="xgb_us_h7",
            rmse=11.0,
            mape=0.9,
        )

    monkeypatch.setattr(service, "latest_metrics", _latest_metrics)
    monkeypatch.setattr(service, "train", _train)
    monkeypatch.setattr(
        commodity_service_module,
        "load_model",
        lambda path: (_Model(), {"model_name": "xgboost", "horizon": 7 if "h7" in str(path) else 30}),
    )
    monkeypatch.setattr(commodity_service_module, "get_fx_rates", lambda: {"USD": 1.0, "INR": 83.5, "EUR": 0.92})
    monkeypatch.setattr(
        service.fetcher,
        "get_historical",
        lambda commodity, region: pd.DataFrame(
            {
                "Date": pd.date_range("2025-01-01", periods=220, freq="D"),
                "Open": np.linspace(1900.0, 2100.0, 220),
                "High": np.linspace(1910.0, 2110.0, 220),
                "Low": np.linspace(1890.0, 2090.0, 220),
                "Close": np.linspace(1905.0, 2105.0, 220),
                "Volume": np.linspace(1000.0, 1400.0, 220),
            }
        ),
    )

    response = asyncio.run(service.predict(session=None, commodity="gold", region="us", horizon=7))
    assert state["train_called"] is False
    assert "@h30->h7" in response.model_used
