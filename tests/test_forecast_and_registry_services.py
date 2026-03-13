from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

from app.schemas.market_data import (
    MarketDataProvenanceRecord,
    NormalizedHistoricalBar,
    NormalizedHistoricalSeries,
)
from app.services.feature_store_service import FeatureStoreService
from app.services.forecast_service import ForecastService
from app.services import model_registry_service as model_registry_service_module
from app.services.model_registry_service import ModelRegistryService


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
            unit="exchange_standard",
            currency="EUR",
            to_regional_price=lambda price, _region, _fx: price,
            latest_metrics_loader=_latest_metrics_loader,
        )
    )

    assert response.model_used == "naive_fallback_v1"
    assert response.point_forecast == 2260.0
    assert response.confidence_interval[0] < response.point_forecast < response.confidence_interval[1]
    assert response.forecast_horizon >= datetime.now(timezone.utc).date()
