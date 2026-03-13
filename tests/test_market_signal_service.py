from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

import pandas as pd
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.schemas.market_data import (
    MarketDataProvenanceRecord,
    NormalizedHistoricalBar,
    NormalizedHistoricalSeries,
    NormalizedLiveQuote,
)
from app.schemas.responses import (
    CommodityNewsSummaryResponse,
    EngineeredFeatureSnapshot,
    LivePriceResponse,
    MarketIntelligenceResponse,
    MarketSignalResponse,
    NewsHeadline,
    RegionalHistoricalPoint,
    RegionalHistoricalResponse,
    RegionalPredictionResponse,
)
from app.services.market_signal_service import MarketSignalService


def test_market_signal_service_builds_structured_bundle(monkeypatch) -> None:
    service = MarketSignalService()

    async def _live_prices(region: str | None = None):
        _ = region
        return [
            LivePriceResponse(
                commodity="gold",
                region="us",
                unit="oz",
                currency="USD",
                live_price=2350.0,
                source="metals.live",
                timestamp=datetime.now(timezone.utc),
            )
        ]

    async def _historical(commodity: str, region: str, period: str = "1y"):
        _ = commodity, region, period
        return RegionalHistoricalResponse(
            commodity="gold",
            region="us",
            currency="USD",
            unit="oz",
            rows=40,
            data=[
                RegionalHistoricalPoint(
                    date=date(2026, 1, min(day, 28)),
                    open=2200.0 + day,
                    high=2205.0 + day,
                    low=2195.0 + day,
                    close=2200.0 + day,
                    volume=1000.0 + day,
                )
                for day in range(1, 41)
            ],
        )

    async def _predict(session, commodity: str, region: str, horizon: int):
        _ = session, commodity, region, horizon
        return RegionalPredictionResponse(
            commodity="gold",
            region="us",
            unit="oz",
            currency="USD",
            forecast_horizon=date(2026, 4, 10),
            point_forecast=2390.0,
            confidence_interval=(2340.0, 2440.0),
            scenario="base",
            scenario_forecasts={"bull": 2460.0, "base": 2390.0, "bear": 2320.0},
            model_used="xgboost_us_20260310",
        )

    async def _news(commodity: str, headlines=None):
        _ = commodity
        return CommodityNewsSummaryResponse(
            commodity="gold",
            sentiment="bullish",
            summary="Macro uncertainty and a softer dollar are supporting gold.",
            headlines=[
                NewsHeadline(
                    title="Gold supported by softer dollar",
                    source="Test Feed",
                    url="",
                    published_at=datetime.now(timezone.utc),
                )
            ],
            updated_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(service.commodity_service, "live_prices", _live_prices)
    monkeypatch.setattr(service.commodity_service, "historical", _historical)
    monkeypatch.setattr(service.commodity_service, "predict", _predict)
    monkeypatch.setattr(
        service.commodity_service.fetcher,
        "get_historical",
        lambda commodity, period="1y", region="us": pd.DataFrame(
            {
                "Date": pd.date_range("2026-01-01", periods=80, freq="D"),
                "Open": [2200.0 + i for i in range(80)],
                "High": [2205.0 + i for i in range(80)],
                "Low": [2195.0 + i for i in range(80)],
                "Close": [2200.0 + i for i in range(80)],
                "Volume": [1000.0 + i for i in range(80)],
            }
        ),
    )
    monkeypatch.setattr(service.news_service, "summarize", _news)
    async def _recent_headlines(session, *, commodity: str, limit: int = 6):
        _ = session, commodity, limit
        return [
            NewsHeadline(
                title="Gold supported by softer dollar",
                source="Test Feed",
                url="",
                published_at=datetime.now(timezone.utc),
            )
        ]
    monkeypatch.setattr(service.news_persistence_service, "get_or_ingest_recent_headlines", _recent_headlines)

    response = asyncio.run(service.build_market_intelligence(session=None, commodity="gold", region="us", horizon=30))
    assert response.signal.label in {"bullish", "neutral", "cautious", "bearish"}
    assert response.features.calendar_month == 3
    assert response.news_sentiment == "bullish"
    assert {item.data_type for item in response.provenance} >= {"live_price", "historical", "forecast", "signal"}


def test_market_intelligence_endpoint(monkeypatch) -> None:
    client = TestClient(app)

    async def _bundle(session, commodity: str, region: str, horizon: int):
        _ = session, commodity, region, horizon
        return MarketIntelligenceResponse(
            commodity="gold",
            region="us",
            currency="USD",
            unit="oz",
            horizon_days=30,
            as_of=datetime.now(timezone.utc),
            live_price=2350.0,
            forecast_point=2390.0,
            forecast_range=(2340.0, 2440.0),
            scenario_forecasts={"bull": 2460.0, "base": 2390.0, "bear": 2320.0},
            signal={
                "label": "bullish",
                "score": 0.42,
                "confidence": 0.71,
                "scenario": "bull",
                "rationale": "forecast spread positive, momentum positive, volatility contained",
                "thresholds_applied": ["forecast_upside>=1.5%"],
            },
            features={
                "returns_1d": 0.003,
                "returns_5d": 0.012,
                "returns_20d": 0.028,
                "realized_volatility_20d": 0.011,
                "momentum_20d": 0.028,
                "price_vs_ma20_pct": 0.015,
                "drawdown_20d_pct": -0.004,
                "fx_rate": 1.0,
                "fx_volatility": 0.0,
                "inflation_proxy": 0.002,
                "rate_proxy": 0.01,
                "calendar_month": 3,
            },
            news_sentiment="bullish",
            news_summary="Bullish macro backdrop.",
            provenance=[],
        )

    monkeypatch.setattr(routes.market_signal_service, "build_market_intelligence", _bundle)
    response = client.get("/api/intelligence/gold/us?horizon=30")
    assert response.status_code == 200
    payload = response.json()
    assert payload["signal"]["label"] == "bullish"
    assert payload["features"]["calendar_month"] == 3


def test_market_signal_endpoint(monkeypatch) -> None:
    client = TestClient(app)

    async def _bundle(session, commodity: str, region: str, horizon: int):
        _ = session, commodity, region, horizon
        return MarketSignalResponse(
            commodity="gold",
            region="us",
            horizon_days=30,
            live_price=2350.0,
            forecast_point=2390.0,
            forecast_range=(2340.0, 2440.0),
            scenario_forecasts={"bull": 2460.0, "base": 2390.0, "bear": 2320.0},
            signal={
                "label": "bullish",
                "score": 0.42,
                "confidence": 0.71,
                "scenario": "bull",
                "rationale": "forecast spread positive, momentum positive, volatility contained",
                "thresholds_applied": ["forecast_upside>=1.5%"],
            },
            features={
                "returns_1d": 0.003,
                "returns_5d": 0.012,
                "returns_20d": 0.028,
                "realized_volatility_20d": 0.011,
                "momentum_20d": 0.028,
                "price_vs_ma20_pct": 0.015,
                "drawdown_20d_pct": -0.004,
                "fx_rate": 1.0,
                "fx_volatility": 0.0,
                "inflation_proxy": 0.002,
                "rate_proxy": 0.01,
                "calendar_month": 3,
            },
            provenance=[],
        )

    monkeypatch.setattr(routes.market_signal_service, "build_signal_response", _bundle)
    response = client.get("/api/signals/gold/us?horizon=30")
    assert response.status_code == 200
    payload = response.json()
    assert payload["signal"]["label"] == "bullish"
    assert payload["horizon_days"] == 30


def test_normalized_feature_and_forecast_endpoints(monkeypatch) -> None:
    client = TestClient(app)

    async def _fetch_live_quotes(commodities):
        _ = commodities
        return {
            "gold": NormalizedLiveQuote(
                commodity="gold",
                price_usd_per_troy_oz=2350.0,
                observed_at=datetime.now(timezone.utc),
                provenance=MarketDataProvenanceRecord(
                    source_type="live",
                    provider="metals.live",
                    detail="gold/us",
                    observed_at=datetime.now(timezone.utc),
                ),
            )
        }

    def _load_historical_series(commodity: str, region: str, period: str = "1y"):
        _ = commodity, region, period
        return NormalizedHistoricalSeries(
            commodity="gold",
            region="us",
            provenance=MarketDataProvenanceRecord(
                source_type="historical",
                provider="cache",
                detail="gold/us",
                observed_at=datetime.now(timezone.utc),
            ),
            bars=[
                NormalizedHistoricalBar(
                    date=date(2026, 3, 1),
                    open_usd_per_troy_oz=2200.0,
                    high_usd_per_troy_oz=2210.0,
                    low_usd_per_troy_oz=2190.0,
                    close_usd_per_troy_oz=2205.0,
                    volume=1000.0,
                )
            ],
        )

    async def _materialize_online_features_for_session(session, *, commodity: str, series, region: str, period: str = "1y", fx=None):
        _ = session, commodity, series, region, period, fx
        return pd.DataFrame([{"Date": pd.Timestamp("2026-03-01"), "fx_rate": 1.0, "fx_volatility": 0.0, "inflation_proxy": 0.002, "interest_rates_fred_ecb_rbi": 0.01}])

    def _build_feature_snapshot(closes, enriched):
        _ = closes, enriched
        return EngineeredFeatureSnapshot(
            returns_1d=0.003,
            returns_5d=0.012,
            returns_20d=0.028,
            realized_volatility_20d=0.011,
            momentum_20d=0.028,
            price_vs_ma20_pct=0.015,
            drawdown_20d_pct=-0.004,
            fx_rate=1.0,
            fx_volatility=0.0,
            inflation_proxy=0.002,
            rate_proxy=0.01,
            calendar_month=3,
        )

    async def _predict(session, commodity: str, region: str, horizon: int):
        _ = session, commodity, region, horizon
        return RegionalPredictionResponse(
            commodity="gold",
            region="us",
            unit="oz",
            currency="USD",
            forecast_horizon=date(2026, 4, 10),
            point_forecast=2390.0,
            confidence_interval=(2340.0, 2440.0),
            scenario="base",
            scenario_forecasts={"bull": 2460.0, "base": 2390.0, "bear": 2320.0},
            model_used="xgboost_us_20260310",
        )

    async def _persist_live(session, *, quotes, region: str, job_id=None):
        _ = session, quotes, region, job_id

    async def _persist_historical(session, *, series, period: str, job_id=None):
        _ = session, series, period, job_id

    monkeypatch.setattr(routes.service.ingestion_service, "fetch_live_quotes", _fetch_live_quotes)
    monkeypatch.setattr(routes.service.ingestion_service, "load_historical_series", _load_historical_series)
    monkeypatch.setattr(routes.service.feature_store_service, "materialize_online_features_for_session", _materialize_online_features_for_session)
    monkeypatch.setattr(routes.service.feature_store_service, "build_feature_snapshot", _build_feature_snapshot)
    monkeypatch.setattr(routes.service.ingestion_persistence_service, "persist_live_quotes", _persist_live)
    monkeypatch.setattr(routes.service.ingestion_persistence_service, "persist_historical_series", _persist_historical)
    monkeypatch.setattr(routes.service, "predict", _predict)

    live_response = client.get("/api/normalized/live/gold/us")
    assert live_response.status_code == 200
    assert live_response.json()["price_usd_per_troy_oz"] == 2350.0

    historical_response = client.get("/api/normalized/historical/gold/us?range=1y")
    assert historical_response.status_code == 200
    assert historical_response.json()["rows"] == 1

    features_response = client.get("/api/features/gold/us?range=1y")
    assert features_response.status_code == 200
    assert features_response.json()["features"]["calendar_month"] == 3

    forecast_response = client.get("/api/forecasts/gold/us?horizon=30")
    assert forecast_response.status_code == 200
    assert forecast_response.json()["point_forecast"] == 2390.0
