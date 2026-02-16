from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

from backend.app.services.price_conversion import PriceConverter

COMMODITY_SYMBOLS = {
    "gold": "GC=F",
    "silver": "SI=F",
    "crude_oil": "CL=F",
}

REGION_SOURCE = {
    "us": "comex_yfinance",
    "india": "mcx_derived",
    "europe": "lbma_ecb_derived",
}


class MarketDataFetcher:
    def __init__(self, cache_dir: str) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.converter = PriceConverter()

    def _cache_path(self, commodity: str, region: str) -> Path:
        return self.cache_dir / f"{commodity}_{region}.csv"

    async def get_historical(self, commodity: str, region: str, period: str = "5y") -> pd.DataFrame:
        path = self._cache_path(commodity, region)
        if path.exists():
            data = pd.read_csv(path, parse_dates=["timestamp"])
            return data.sort_values("timestamp")

        symbol = COMMODITY_SYMBOLS[commodity]
        base = yf.download(symbol, period=period, auto_adjust=False, progress=False).reset_index()
        if base.empty:
            return pd.DataFrame(columns=["commodity", "timestamp", "region", "price_in_grams", "currency", "unit", "source", "open", "high", "low", "close", "volume"])

        records = []
        for row in base.itertuples(index=False):
            usd_per_gram = float(row.Close) / 31.1034768
            regional_price = await self.converter.usd_per_gram_to_region(usd_per_gram, region)
            open_v = await self.converter.usd_per_gram_to_region(float(row.Open) / 31.1034768, region)
            high_v = await self.converter.usd_per_gram_to_region(float(row.High) / 31.1034768, region)
            low_v = await self.converter.usd_per_gram_to_region(float(row.Low) / 31.1034768, region)
            records.append(
                {
                    "commodity": commodity,
                    "timestamp": pd.to_datetime(row.Date),
                    "region": region,
                    "price_in_grams": float(usd_per_gram),
                    "currency": {"india": "INR", "us": "USD", "europe": "EUR"}[region],
                    "unit": {"india": "10g", "us": "oz", "europe": "g"}[region],
                    "source": REGION_SOURCE[region],
                    "open": open_v,
                    "high": high_v,
                    "low": low_v,
                    "close": regional_price,
                    "volume": float(row.Volume),
                }
            )
        data = pd.DataFrame(records).sort_values("timestamp")
        data.to_csv(path, index=False)
        return data
