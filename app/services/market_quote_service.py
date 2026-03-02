from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import yfinance as yf

from app.services.fx_cache import get_fx_rates
from app.services.price_conversion import REGION_CURRENCY, troy_oz_to_grams, convert_price

ALERT_COMMODITY_SYMBOLS = {
    "gold": "GC=F",
    "silver": "SI=F",
    "crude_oil": "CL=F",
    "natural_gas": "NG=F",
    "copper": "HG=F",
}

ALERT_COMMODITY_UNITS = {
    "gold": {"india": "10g_24k", "us": "oz", "europe": "exchange_standard"},
    "silver": {"india": "10g_24k", "us": "oz", "europe": "exchange_standard"},
    "crude_oil": {"india": "barrel", "us": "barrel", "europe": "barrel"},
    "natural_gas": {"india": "mmbtu", "us": "mmbtu", "europe": "mmbtu"},
    "copper": {"india": "lb", "us": "lb", "europe": "lb"},
}


@dataclass
class MarketQuote:
    commodity: str
    region: str
    currency: str
    unit: str
    price: float
    daily_change_pct: float
    timestamp: datetime
    source: str


class MarketQuoteService:
    @staticmethod
    def _normalize_download(df):
        if df.empty:
            return df
        if isinstance(df.columns, tuple):
            return df
        if getattr(df.columns, "nlevels", 1) > 1:
            df.columns = [str(col[0]) for col in df.columns]
        else:
            df.columns = [str(col) for col in df.columns]
        return df

    def fetch_quote(self, commodity: str, region: str) -> MarketQuote:
        if commodity not in ALERT_COMMODITY_SYMBOLS:
            raise ValueError(f"Unsupported commodity: {commodity}")

        symbol = ALERT_COMMODITY_SYMBOLS[commodity]
        df = yf.download(symbol, period="5d", auto_adjust=False, progress=False).reset_index()
        df = self._normalize_download(df)
        if df.empty or len(df.index) < 2:
            raise RuntimeError(f"Unable to fetch market data for {commodity}")
        if "Close" not in df.columns:
            raise RuntimeError(f"Market data for {commodity} does not include Close column")

        latest_close = float(df["Close"].iloc[-1])
        prev_close = float(df["Close"].iloc[-2])
        daily_change = ((latest_close - prev_close) / prev_close) * 100 if prev_close else 0.0

        fx = get_fx_rates()
        currency = REGION_CURRENCY[region]

        if commodity in {"gold", "silver"}:
            # yfinance metal quote is USD/troy-ounce; convert via canonical USD/gram.
            display_price = convert_price(troy_oz_to_grams(latest_close), region, fx)
        else:
            rate = fx.get(currency, 1.0)
            display_price = latest_close * rate

        return MarketQuote(
            commodity=commodity,
            region=region,
            currency=currency,
            unit=ALERT_COMMODITY_UNITS[commodity][region],
            price=round(display_price, 4),
            daily_change_pct=round(daily_change, 4),
            timestamp=datetime.now(timezone.utc),
            source="yahoo_finance",
        )
