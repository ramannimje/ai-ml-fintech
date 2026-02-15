from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

COMMODITY_SYMBOLS = {
    "gold": "GC=F",
    "silver": "SI=F",
    "crude_oil": "CL=F",
}


class MarketDataFetcher:
    def __init__(self, cache_dir: str) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, commodity: str) -> Path:
        return self.cache_dir / f"{commodity}.csv"

    @staticmethod
    def _normalize_download(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        if isinstance(df.columns, pd.MultiIndex):
            # yfinance can return MultiIndex columns even for one symbol.
            df.columns = [str(col[0]) for col in df.columns]
        else:
            df.columns = [str(col) for col in df.columns]

        if "Date" not in df.columns and "Datetime" in df.columns:
            df = df.rename(columns={"Datetime": "Date"})

        required = ["Date", "Open", "High", "Low", "Close", "Volume"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Historical data missing columns: {missing}. Available: {list(df.columns)}")
        return df

    def get_historical(self, commodity: str, period: str = "5y") -> pd.DataFrame:
        symbol = COMMODITY_SYMBOLS[commodity]
        path = self._cache_path(commodity)
        cached = pd.read_csv(path, parse_dates=["Date"]) if path.exists() else pd.DataFrame()

        if cached.empty:
            fresh = yf.download(symbol, period=period, auto_adjust=False, progress=False).reset_index()
            fresh = self._normalize_download(fresh)
        else:
            last_dt = cached["Date"].max().to_pydatetime().replace(tzinfo=timezone.utc)
            start = (last_dt + timedelta(days=1)).date().isoformat()
            fresh = yf.download(symbol, start=start, auto_adjust=False, progress=False).reset_index()
            if not fresh.empty:
                fresh = self._normalize_download(fresh)
                fresh = pd.concat([cached, fresh], ignore_index=True)
            else:
                fresh = cached.copy()

        fresh = fresh[["Date", "Open", "High", "Low", "Close", "Volume"]].drop_duplicates("Date")
        fresh = fresh.sort_values("Date").ffill().dropna()
        fresh.to_csv(path, index=False)
        return fresh

    def latest_timestamp(self, commodity: str) -> datetime | None:
        path = self._cache_path(commodity)
        if not path.exists():
            return None
        data = pd.read_csv(path, parse_dates=["Date"])
        return data["Date"].max().to_pydatetime()
