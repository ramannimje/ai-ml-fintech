from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Protocol

import httpx
import pandas as pd

from app.core.exceptions import TrainingError
from app.schemas.market_data import (
    MarketDataProvenanceRecord,
    NormalizedHistoricalBar,
    NormalizedHistoricalSeries,
    NormalizedLiveQuote,
)
from ml.data.data_fetcher import COMMODITY_SYMBOLS, MarketDataFetcher

logger = logging.getLogger(__name__)

PRIMARY_SOURCE_BY_COMMODITY = {
    "gold": "comex",
    "silver": "comex",
    "crude_oil": "comex",
}


class LiveQuoteProvider(Protocol):
    provider_name: str
    fallback_level: int

    async def fetch(self, commodities: list[str]) -> dict[str, NormalizedLiveQuote]:
        ...


class MetalsLiveQuoteProvider:
    provider_name = "metals.live"
    fallback_level = 0

    def __init__(self) -> None:
        self.cooldown_until: datetime | None = None
        self.last_error: str | None = None

    async def fetch(self, commodities: list[str]) -> dict[str, NormalizedLiveQuote]:
        now = datetime.now(timezone.utc)
        if self.cooldown_until and now < self.cooldown_until:
            return {}

        try:
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "tradesight/1.0"}) as client:
                response = await client.get("https://api.metals.live/v1/spot")
            response.raise_for_status()
            raw_data = response.json()
            rates: dict[str, float] = {}
            for entry in raw_data:
                if isinstance(entry, dict):
                    rates.update(entry)
            self.last_error = None
            return {
                commodity: NormalizedLiveQuote(
                    commodity=commodity,
                    price_usd_per_troy_oz=float(price),
                    observed_at=now,
                    provenance=MarketDataProvenanceRecord(
                        source_type="live",
                        provider=self.provider_name,
                        detail=commodity,
                        observed_at=now,
                        ingested_at=now,
                        fallback_level=self.fallback_level,
                    ),
                )
                for commodity, price in rates.items()
                if commodity in commodities
            }
        except Exception as exc:
            self.last_error = str(exc)
            self.cooldown_until = now + timedelta(minutes=10)
            logger.warning("Metals.live API fetch failed: %s (cooldown 10m)", exc)
            return {}


class YahooFinanceLiveQuoteProvider:
    provider_name = "yahoo_finance_api"
    fallback_level = 1

    async def fetch(self, commodities: list[str]) -> dict[str, NormalizedLiveQuote]:
        now = datetime.now(timezone.utc)
        quotes: dict[str, NormalizedLiveQuote] = {}
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            for commodity in commodities:
                symbol = COMMODITY_SYMBOLS.get(commodity)
                if not symbol:
                    continue
                try:
                    # Fetch 5 days to calculate daily change
                    response = await client.get(
                        f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
                    )
                    response.raise_for_status()
                    data = response.json()
                    result = data.get("chart", {}).get("result", [{}])[0]
                    price = result.get("meta", {}).get("regularMarketPrice")
                    if price is None:
                        continue
                    
                    # Calculate daily change from previous close
                    quotes_data = result.get("indicators", {}).get("quote", [{}])[0]
                    closes = quotes_data.get("close", [])
                    valid_closes = [c for c in closes if c is not None]
                    
                    daily_change = 0.0
                    daily_change_pct = 0.0
                    if len(valid_closes) >= 2:
                        latest_close = valid_closes[-1]
                        prev_close = valid_closes[-2]
                        daily_change = latest_close - prev_close
                        daily_change_pct = ((latest_close - prev_close) / prev_close) * 100 if prev_close else 0.0
                    
                    quotes[commodity] = NormalizedLiveQuote(
                        commodity=commodity,
                        price_usd_per_troy_oz=float(price),
                        daily_change=daily_change,
                        daily_change_pct=daily_change_pct,
                        observed_at=now,
                        provenance=MarketDataProvenanceRecord(
                            source_type="live",
                            provider=self.provider_name,
                            detail=f"{PRIMARY_SOURCE_BY_COMMODITY.get(commodity, 'yahoo_finance')}/yahoo_api",
                            observed_at=now,
                            ingested_at=now,
                            raw_symbol=symbol,
                            fallback_level=self.fallback_level,
                        ),
                    )
                except Exception as exc:
                    logger.warning("Direct YF API fetch failed for %s: %s", commodity, exc)
        return quotes


class CachedHistoryQuoteProvider:
    provider_name = "cached_history"
    fallback_level = 2

    def __init__(self, fetcher: MarketDataFetcher) -> None:
        self.fetcher = fetcher

    async def fetch(self, commodities: list[str]) -> dict[str, NormalizedLiveQuote]:
        now = datetime.now(timezone.utc)
        quotes: dict[str, NormalizedLiveQuote] = {}
        for commodity in commodities:
            try:
                raw = self.fetcher.get_historical(commodity, period="1y")
                if raw.empty:
                    raise TrainingError(f"No cached market data available for {commodity}")
                quotes[commodity] = NormalizedLiveQuote(
                    commodity=commodity,
                    price_usd_per_troy_oz=float(raw["Close"].iloc[-1]),
                    observed_at=now,
                    provenance=MarketDataProvenanceRecord(
                        source_type="live",
                        provider=self.provider_name,
                        detail=f"{PRIMARY_SOURCE_BY_COMMODITY.get(commodity, 'yahoo_finance')}/cached_history",
                        observed_at=now,
                        ingested_at=now,
                        raw_symbol=COMMODITY_SYMBOLS.get(commodity),
                        fallback_level=self.fallback_level,
                    ),
                )
            except Exception as exc:
                logger.error("pricing_failure deep fallback commodity=%s reason=%s", commodity, str(exc))
        return quotes


class PlaceholderQuoteProvider:
    provider_name = "placeholder"
    fallback_level = 3

    PLACEHOLDER_PRICES = {
        "gold": 1900.0,
        "silver": 24.0,
        "crude_oil": 80.0,
    }

    async def fetch(self, commodities: list[str]) -> dict[str, NormalizedLiveQuote]:
        now = datetime.now(timezone.utc)
        return {
            commodity: NormalizedLiveQuote(
                commodity=commodity,
                price_usd_per_troy_oz=float(self.PLACEHOLDER_PRICES[commodity]),
                observed_at=now,
                provenance=MarketDataProvenanceRecord(
                    source_type="live",
                    provider=self.provider_name,
                    detail="static safety fallback",
                    observed_at=now,
                    ingested_at=now,
                    fallback_level=self.fallback_level,
                ),
            )
            for commodity in commodities
            if commodity in self.PLACEHOLDER_PRICES
        }


class MarketIngestionService:
    def __init__(
        self,
        fetcher: MarketDataFetcher,
        live_quote_providers: list[LiveQuoteProvider] | None = None,
    ) -> None:
        self.fetcher = fetcher
        self.metals_live_provider = MetalsLiveQuoteProvider()
        self.yahoo_live_provider = YahooFinanceLiveQuoteProvider()
        self.cached_history_provider = CachedHistoryQuoteProvider(fetcher)
        self.placeholder_provider = PlaceholderQuoteProvider()
        self.live_quote_providers = live_quote_providers or [
            self.metals_live_provider,
            self.yahoo_live_provider,
            self.cached_history_provider,
            self.placeholder_provider,
        ]

    async def fetch_live_quotes(self, commodities: list[str]) -> dict[str, NormalizedLiveQuote]:
        remaining = list(commodities)
        quotes: dict[str, NormalizedLiveQuote] = {}
        for provider in self.live_quote_providers:
            if not remaining:
                break
            batch = await provider.fetch(remaining)
            for commodity, quote in batch.items():
                if commodity not in quotes:
                    quotes[commodity] = quote
            remaining = [commodity for commodity in remaining if commodity not in quotes]
        return quotes

    def load_historical_series(
        self,
        commodity: str,
        region: str,
        period: str = "1y",
    ) -> NormalizedHistoricalSeries:
        frame = self.fetcher.get_historical(commodity, period=period, region=region)
        bars = [
            NormalizedHistoricalBar(
                date=row.Date.date() if hasattr(row.Date, "date") else row.Date,
                open_usd_per_troy_oz=float(row.Open),
                high_usd_per_troy_oz=float(row.High),
                low_usd_per_troy_oz=float(row.Low),
                close_usd_per_troy_oz=float(row.Close),
                volume=float(row.Volume) if row.Volume is not None else None,
            )
            for row in frame.itertuples()
        ]
        latest_observed = frame["Date"].max().to_pydatetime().replace(tzinfo=timezone.utc) if not frame.empty else None
        return NormalizedHistoricalSeries(
            commodity=commodity,
            region=region,
            bars=bars,
            provenance=MarketDataProvenanceRecord(
                source_type="historical",
                provider="yahoo_finance/cache",
                detail=f"ml/cache/{commodity}_{region}.csv",
                observed_at=latest_observed,
                ingested_at=datetime.now(timezone.utc),
                raw_symbol=COMMODITY_SYMBOLS.get(commodity),
            ),
        )
