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

# Macro feature symbols
MACRO_SYMBOLS = {
    "dxy": "DX-Y.NYB",       # USD Index
    "treasury_10y": "^TNX",  # 10-Year Treasury Yield (inflation proxy)
}


class MarketDataFetcher:
    def __init__(self, cache_dir: str) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, commodity: str, region: str = "us") -> Path:
        return self.cache_dir / f"{commodity}_{region}.csv"

    def _macro_cache_path(self, symbol_key: str) -> Path:
        return self.cache_dir / f"macro_{symbol_key}.csv"

    @staticmethod
    def _normalize_download(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        if isinstance(df.columns, pd.MultiIndex):
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

    def get_historical(self, commodity: str, period: str = "5y", region: str = "us") -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a commodity.
        Data is stored in USD/troy oz (raw from yfinance).
        Region-specific conversion is handled in the service layer.
        Cache is keyed by commodity+region for future extensibility.
        """
        symbol = COMMODITY_SYMBOLS[commodity]
        # Use region-aware cache path but same data source (COMEX)
        # Region-specific pricing is done at service layer via FX conversion
        path = self._cache_path(commodity, region)
        # Also check legacy path (commodity only) for backwards compat
        legacy_path = self.cache_dir / f"{commodity}.csv"

        cached = pd.DataFrame()
        if path.exists():
            cached = pd.read_csv(path, parse_dates=["Date"])
        elif legacy_path.exists():
            cached = pd.read_csv(legacy_path, parse_dates=["Date"])

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

    def get_macro_features(self, period: str = "5y") -> pd.DataFrame:
        """
        Fetch macro features: DXY (USD index) and 10Y Treasury yield.
        Returns a DataFrame indexed by Date with columns: dxy, treasury_10y.
        """
        frames: dict[str, pd.Series] = {}
        for key, symbol in MACRO_SYMBOLS.items():
            path = self._macro_cache_path(key)
            try:
                cached = pd.read_csv(path, parse_dates=["Date"]) if path.exists() else pd.DataFrame()
                if cached.empty:
                    raw = yf.download(symbol, period=period, auto_adjust=False, progress=False).reset_index()
                else:
                    last_dt = cached["Date"].max().to_pydatetime().replace(tzinfo=timezone.utc)
                    start = (last_dt + timedelta(days=1)).date().isoformat()
                    raw = yf.download(symbol, start=start, auto_adjust=False, progress=False).reset_index()
                    if not raw.empty:
                        raw = pd.concat([cached, raw], ignore_index=True)
                    else:
                        raw = cached.copy()

                if not raw.empty:
                    if isinstance(raw.columns, pd.MultiIndex):
                        raw.columns = [str(col[0]) for col in raw.columns]
                    if "Date" not in raw.columns and "Datetime" in raw.columns:
                        raw = raw.rename(columns={"Datetime": "Date"})
                    raw = raw[["Date", "Close"]].drop_duplicates("Date").sort_values("Date")
                    raw.to_csv(path, index=False)
                    frames[key] = raw.set_index("Date")["Close"].rename(key)
            except Exception:
                pass  # Macro features are optional; skip on error

        if not frames:
            return pd.DataFrame()

        macro = pd.concat(frames.values(), axis=1).ffill().bfill()
        macro.index = pd.to_datetime(macro.index)
        return macro

    def latest_timestamp(self, commodity: str) -> datetime | None:
        path = self._cache_path(commodity)
        if not path.exists():
            # Try legacy path
            legacy = self.cache_dir / f"{commodity}.csv"
            if not legacy.exists():
                return None
            path = legacy
        data = pd.read_csv(path, parse_dates=["Date"])
        return data["Date"].max().to_pydatetime()
