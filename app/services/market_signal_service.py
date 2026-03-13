from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.responses import (
    DataProvenance,
    MarketSignalResponse,
    MarketIntelligenceResponse,
)
from app.services.commodity_service import CommodityService
from app.services.feature_store_service import FeatureStoreService
from app.services.ingestion_service import MarketIngestionService
from app.services.market_quote_service import ALERT_COMMODITY_SYMBOLS
from app.services.news_service import CommodityNewsService
from app.services.news_persistence_service import NewsPersistenceService
from app.services.signal_service import SignalService


class MarketSignalService:
    def __init__(self) -> None:
        self.commodity_service = CommodityService()
        self.news_service = CommodityNewsService()
        self.news_persistence_service = NewsPersistenceService(self.news_service)
        self.ingestion_service = MarketIngestionService(fetcher=self.commodity_service.fetcher)
        self.feature_store_service = FeatureStoreService(fetcher=self.commodity_service.fetcher)
        self.signal_service = SignalService()

    async def build_market_intelligence(
        self,
        session: AsyncSession,
        commodity: str,
        region: str,
        horizon: int = 30,
        include_news: bool = True,
    ) -> MarketIntelligenceResponse:
        live_rows = await self.commodity_service.live_prices(region=region)
        live_row = next((item for item in live_rows if item.commodity == commodity), None)
        if live_row is None:
            raise ValueError(f"Live price unavailable for {commodity}/{region}")

        historical = await self.commodity_service.historical(commodity, region=region, period="1y")
        prediction = await self.commodity_service.predict(session, commodity, region=region, horizon=horizon)

        series = self.ingestion_service.load_historical_series(commodity=commodity, region=region, period="1y")
        enriched = await self.feature_store_service.materialize_online_features_for_session(
            session,
            commodity=commodity,
            series=series,
            region=region,
            period="1y",
        )
        closes = [float(point.close) for point in historical.data if point.close is not None]
        features = self.feature_store_service.build_feature_snapshot(closes=closes, enriched=enriched)
        signal = self.signal_service.summarize(
            current_price=float(live_row.live_price),
            point_forecast=float(prediction.point_forecast),
            forecast_range=prediction.confidence_interval,
            features=features,
        )

        news_sentiment = None
        news_summary = None
        provenance = [
            DataProvenance(
                data_type="live_price",
                provider=live_row.source,
                detail=f"{commodity}/{region}",
                observed_at=live_row.timestamp,
            ),
            DataProvenance(
                data_type="historical",
                provider=series.provenance.provider,
                detail=series.provenance.detail,
                observed_at=series.provenance.observed_at,
            ),
            DataProvenance(
                data_type="forecast",
                provider=prediction.model_used,
                detail=f"horizon={horizon}",
            ),
            DataProvenance(
                data_type="features",
                provider="feature_store_service_v1",
                detail="returns, momentum, volatility, FX proxy, inflation proxy, rate proxy",
            ),
            DataProvenance(
                data_type="signal",
                provider="market_signal_service_v1",
                detail="weighted rules over features and forecast outputs",
            ),
        ]

        if include_news and commodity in ALERT_COMMODITY_SYMBOLS:
            if session is None:
                news = await self.news_service.summarize(commodity)
            else:
                headlines = await self.news_persistence_service.get_or_ingest_recent_headlines(
                    session,
                    commodity=commodity,
                )
                news = await self.news_service.summarize(commodity, headlines=headlines)
            news_sentiment = news.sentiment
            news_summary = news.summary
            provenance.append(
                DataProvenance(
                    data_type="news",
                    provider="newsapi/claude_fallback",
                    detail=f"headlines={len(news.headlines)}",
                    observed_at=news.updated_at,
                )
            )

        return MarketIntelligenceResponse(
            commodity=commodity,
            region=region,
            currency=prediction.currency,
            unit=prediction.unit,
            horizon_days=horizon,
            as_of=datetime.now(timezone.utc),
            live_price=round(float(live_row.live_price), 4),
            forecast_point=round(float(prediction.point_forecast), 4),
            forecast_range=(
                round(float(prediction.confidence_interval[0]), 4),
                round(float(prediction.confidence_interval[1]), 4),
            ),
            scenario_forecasts=prediction.scenario_forecasts,
            signal=signal,
            features=features,
            news_sentiment=news_sentiment,
            news_summary=news_summary,
            provenance=provenance,
        )

    async def build_signal_response(
        self,
        session: AsyncSession,
        commodity: str,
        region: str,
        horizon: int = 30,
    ) -> MarketSignalResponse:
        live_rows = await self.commodity_service.live_prices(region=region)
        live_row = next((item for item in live_rows if item.commodity == commodity), None)
        if live_row is None:
            raise ValueError(f"Live price unavailable for {commodity}/{region}")

        prediction = await self.commodity_service.predict(session, commodity, region=region, horizon=horizon)
        series = self.ingestion_service.load_historical_series(commodity=commodity, region=region, period="1y")
        enriched = await self.feature_store_service.materialize_online_features_for_session(
            session,
            commodity=commodity,
            series=series,
            region=region,
            period="1y",
        )
        closes = [bar.close_usd_per_troy_oz for bar in series.bars]
        features = self.feature_store_service.build_feature_snapshot(closes=closes, enriched=enriched)
        provenance = [
            DataProvenance(
                data_type="live_price",
                provider=live_row.source,
                detail=f"{commodity}/{region}",
                observed_at=live_row.timestamp,
            ),
            DataProvenance(
                data_type="historical",
                provider=series.provenance.provider,
                detail=series.provenance.detail,
                observed_at=series.provenance.observed_at,
            ),
            DataProvenance(
                data_type="forecast",
                provider=prediction.model_used,
                detail=f"horizon={horizon}",
            ),
            DataProvenance(
                data_type="features",
                provider="feature_store_service_v1",
                detail="returns, momentum, volatility, FX proxy, inflation proxy, rate proxy",
            ),
            DataProvenance(
                data_type="signal",
                provider="signal_service_v1",
                detail="weighted rules over features and forecast outputs",
            ),
        ]
        return self.signal_service.build_response(
            commodity=commodity,
            region=region,
            horizon_days=horizon,
            current_price=float(live_row.live_price),
            point_forecast=float(prediction.point_forecast),
            forecast_range=prediction.confidence_interval,
            scenario_forecasts=prediction.scenario_forecasts,
            features=features,
            provenance=provenance,
        )
