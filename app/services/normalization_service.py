from __future__ import annotations

import pandas as pd

from app.schemas.market_data import NormalizedHistoricalSeries, NormalizedLiveQuote
from app.schemas.responses import LivePriceResponse, RegionalHistoricalPoint, RegionalHistoricalResponse


class MarketDataNormalizationService:
    def __init__(self, *, to_regional_price, unit_for, region_currency: dict[str, str]) -> None:
        self._to_regional_price = to_regional_price
        self._unit_for = unit_for
        self._region_currency = region_currency

    def to_live_price_response(
        self,
        quote: NormalizedLiveQuote,
        region: str,
        fx_rates: dict[str, float],
    ) -> LivePriceResponse:
        return LivePriceResponse(
            commodity=quote.commodity,
            region=region,
            unit=self._unit_for(quote.commodity, region),
            currency=self._region_currency[region],
            live_price=round(self._to_regional_price(quote.price_usd_per_troy_oz, region, fx_rates), 4),
            daily_change=round(quote.daily_change or 0.0, 4),
            daily_change_pct=round(quote.daily_change_pct or 0.0, 4),
            source=quote.provenance.detail or quote.provenance.provider,
            timestamp=quote.observed_at,
        )

    def to_historical_response(
        self,
        series: NormalizedHistoricalSeries,
        fx_rates: dict[str, float],
        fx_history: pd.Series | None = None,
    ) -> RegionalHistoricalResponse:
        def _fx_for_date(date_value):
            if fx_history is None or fx_history.empty or series.region == "us":
                return fx_rates
            ts = pd.Timestamp(date_value).normalize()
            rate = fx_history.get(ts)
            if rate is None:
                history = fx_history.loc[:ts]
                rate = history.iloc[-1] if not history.empty else None
            if rate is None:
                return fx_rates
            regional_fx = dict(fx_rates)
            if series.region == "india":
                regional_fx["INR"] = float(rate)
            elif series.region == "europe":
                regional_fx["EUR"] = float(rate)
            return regional_fx

        points = [
            RegionalHistoricalPoint(
                date=bar.date,
                open=round(self._to_regional_price(bar.open_usd_per_troy_oz, series.region, _fx_for_date(bar.date)), 4),
                high=round(self._to_regional_price(bar.high_usd_per_troy_oz, series.region, _fx_for_date(bar.date)), 4),
                low=round(self._to_regional_price(bar.low_usd_per_troy_oz, series.region, _fx_for_date(bar.date)), 4),
                close=round(self._to_regional_price(bar.close_usd_per_troy_oz, series.region, _fx_for_date(bar.date)), 4),
                volume=bar.volume,
            )
            for bar in series.bars
        ]
        return RegionalHistoricalResponse(
            commodity=series.commodity,
            region=series.region,
            currency=self._region_currency[series.region],
            unit=self._unit_for(series.commodity, series.region),
            rows=len(points),
            data=points,
        )
