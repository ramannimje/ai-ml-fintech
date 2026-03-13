from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

import pandas as pd
from app.schemas.market_data import (
    MarketDataProvenanceRecord,
    NormalizedHistoricalBar,
    NormalizedHistoricalSeries,
)
from app.services.feature_store_service import FeatureStoreService
from app.services.forecast_service import ForecastService
from app.services import model_registry_service as model_registry_service_module
from app.services.model_registry_service import ModelRegistryService
from types import SimpleNamespace


def test_model_registry_load_model_bundle_uses_cache(monkeypatch) -> None:
    service = ModelRegistryService()
    calls = {"count": 0}

    class _Run:
        commodity = "gold"
        region = "us"
        model_version = "xgb_us_20260312"
        artifact_path = "ml/artifacts/gold/us/xgb_us_20260312.joblib"

    def _load_model(_path):
        calls["count"] += 1
        return object(), {"version": "xgb_us_20260312"}

    monkeypatch.setattr(model_registry_service_module, "load_model", _load_model)

    first = service.load_model_bundle(_Run())
    second = service.load_model_bundle(_Run())

    assert calls["count"] == 1
    assert first == second


def test_forecast_service_falls_back_to_naive_response() -> None:
    registry = ModelRegistryService()
    forecast = ForecastService(model_registry_service=registry)
    features = FeatureStoreService()
    series = NormalizedHistoricalSeries(
        commodity="gold",
        region="europe",
        provenance=MarketDataProvenanceRecord(source_type="historical", provider="cache"),
        bars=[
            NormalizedHistoricalBar(
                date=date(2026, 1, min(day, 28)),
                open_usd_per_troy_oz=2200.0 + day,
                high_usd_per_troy_oz=2205.0 + day,
                low_usd_per_troy_oz=2195.0 + day,
                close_usd_per_troy_oz=2200.0 + day,
                volume=1000.0 + day,
            )
            for day in range(1, 61)
        ],
    )

    async def _latest_metrics_loader(session, commodity: str, region: str):
        _ = session, commodity, region
        return None

    response = asyncio.run(
        forecast.generate_prediction(
            session=None,
            commodity="gold",
            region="europe",
            horizon=17,
            series=series,
            feature_store_service=features,
            fx_rates={"USD": 1.0, "INR": 83.0, "EUR": 0.92},
            unit="g",
            currency="EUR",
            to_regional_price=lambda price, _region, _fx: price,
            current_spot_usd_oz=2260.0,
            spot_timestamp=datetime.now(timezone.utc),
            latest_metrics_loader=_latest_metrics_loader,
        )
    )

    assert response.model_used == "naive_fallback_v1"
    assert response.point_forecast == 2260.0
    assert response.confidence_interval[0] < response.point_forecast < response.confidence_interval[1]
    assert response.forecast_horizon >= datetime.now(timezone.utc).date()


def test_forecast_service_caps_base_move_and_keeps_spot_inside_ci(monkeypatch) -> None:
    registry = ModelRegistryService()
    forecast = ForecastService(model_registry_service=registry)
    features = FeatureStoreService()
    series = NormalizedHistoricalSeries(
        commodity="gold",
        region="us",
        provenance=MarketDataProvenanceRecord(source_type="historical", provider="cache"),
        bars=[
            NormalizedHistoricalBar(
                date=date(2026, 2, min(day, 28)),
                open_usd_per_troy_oz=2400.0 + (day * 0.5),
                high_usd_per_troy_oz=2405.0 + (day * 0.5),
                low_usd_per_troy_oz=2395.0 + (day * 0.5),
                close_usd_per_troy_oz=2400.0 + (day * 0.5),
                volume=1000.0 + day,
            )
            for day in range(1, 61)
        ],
    )

    class _Model:
        def predict(self, _features):
            return [1600.0]

    monkeypatch.setattr(
        registry,
        "load_model_bundle",
        lambda _metrics: (_Model(), {"model_name": "xgboost", "horizon": 30}),
    )

    async def _latest_metrics_loader(session, commodity: str, region: str):
        _ = session, commodity, region
        return SimpleNamespace(
            rmse=25.0,
            trained_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
            model_version="xgb_us_20260312",
        )

    response = asyncio.run(
        forecast.generate_prediction(
            session=None,
            commodity="gold",
            region="us",
            horizon=30,
            series=series,
            feature_store_service=features,
            fx_rates={"USD": 1.0, "INR": 83.0, "EUR": 0.92},
            unit="oz",
            currency="USD",
            to_regional_price=lambda price, _region, _fx: price,
            current_spot_usd_oz=2430.0,
            spot_timestamp=datetime.now(timezone.utc),
            latest_metrics_loader=_latest_metrics_loader,
        )
    )

    assert abs(response.forecast_vs_spot_pct) <= 15.0
    assert response.confidence_interval[0] < response.current_spot_price < response.confidence_interval[1]
    assert response.confidence_method == "spot_anchored_volatility_90"


def test_base_ci_bounds_clamp_extreme_silver_ranges() -> None:
    low, high = ForecastService._apply_base_ci_bounds(
        spot_usd_oz=82.49,
        low_usd_oz=1.84,
        high_usd_oz=163.01,
        horizon_days=30,
    )

    assert low == 82.49 * 0.70
    assert high == 82.49 * 1.30


def test_silver_macro_bias_limits_bearish_base_case() -> None:
    registry = ModelRegistryService()
    forecast = ForecastService(model_registry_service=registry)
    raw = pd.DataFrame(
        {
            "Close": [80.0, 80.5, 81.0, 81.4, 81.7, 82.0, 82.2, 82.49] * 8,
            "High": [81.0, 81.2, 81.4, 81.8, 82.0, 82.3, 82.5, 82.8] * 8,
            "Low": [79.0, 79.8, 80.3, 80.8, 81.1, 81.5, 81.8, 82.1] * 8,
        }
    )
    feat = pd.DataFrame(
        {
            "Close": [70 + i * 0.2 for i in range(25)],
            "dxy": [105.0] * 24 + [102.0],
            "treasury_10y": [4.5] * 24 + [4.1],
        }
    )

    capped_return, _ = forecast._calibrate_base_return(
        commodity="silver",
        raw=raw,
        feat=feat,
        spot_usd_oz=82.49,
        raw_model_usd_oz=74.07,
        horizon_days=30,
        trained_horizon=30,
    )

    assert capped_return >= -0.04
