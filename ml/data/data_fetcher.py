from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path

import httpx
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

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

    @staticmethod
    def _apply_period_filter(df: pd.DataFrame, period: str) -> pd.DataFrame:
        if df.empty:
            return df
        if period == "max":
            return df
        out = df.copy()
        out["Date"] = pd.to_datetime(out["Date"])
        end = out["Date"].max()
        if period.endswith("d"):
            days = int(period[:-1] or "1")
            start = end - pd.Timedelta(days=days)
            return out[out["Date"] >= start]
        if period.endswith("m"):
            months = int(period[:-1] or "1")
            start = end - pd.DateOffset(months=months)
            return out[out["Date"] >= start]
        if period.endswith("y"):
            years = int(period[:-1] or "1")
            start = end - pd.DateOffset(years=years)
            return out[out["Date"] >= start]
        return out

    # ------------------------------------------------------------------
    # Direct Yahoo Finance HTTP fallback (bypasses yfinance rate limits)
    # ------------------------------------------------------------------
    _YAHOO_CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
    _YAHOO_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    @staticmethod
    def _yfinance_period_to_http(period: str) -> tuple[str, str]:
        """Convert yfinance period string to Yahoo Chart API range/interval."""
        mapping = {
            "1d": ("1d", "5m"),
            "5d": ("5d", "15m"),
            "1m": ("1mo", "1d"),
            "1mo": ("1mo", "1d"),
            "3m": ("3mo", "1d"),
            "3mo": ("3mo", "1d"),
            "6m": ("6mo", "1d"),
            "6mo": ("6mo", "1d"),
            "1y": ("1y", "1d"),
            "2y": ("2y", "1d"),
            "5y": ("5y", "1d"),
            "max": ("max", "1d"),
        }
        return mapping.get(period, ("5y", "1d"))

    def _fetch_via_http(self, symbol: str, period: str = "5y") -> pd.DataFrame:
        """Fetch historical OHLCV data directly from Yahoo Finance Chart API."""
        yf_range, interval = self._yfinance_period_to_http(period)
        url = self._YAHOO_CHART_URL.format(symbol=symbol)
        params = {"interval": interval, "range": yf_range}
        try:
            with httpx.Client(timeout=30, headers=self._YAHOO_HEADERS) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            result = data.get("chart", {}).get("result")
            if not result:
                logger.warning("yahoo_http_no_results symbol=%s range=%s", symbol, yf_range)
                return pd.DataFrame()

            chart = result[0]
            timestamps = chart.get("timestamp", [])
            quote = chart.get("indicators", {}).get("quote", [{}])[0]

            if not timestamps:
                return pd.DataFrame()

            rows = []
            for i, ts in enumerate(timestamps):
                o = quote.get("open", [None] * len(timestamps))[i]
                h = quote.get("high", [None] * len(timestamps))[i]
                l_ = quote.get("low", [None] * len(timestamps))[i]
                c = quote.get("close", [None] * len(timestamps))[i]
                v = quote.get("volume", [None] * len(timestamps))[i]
                if c is not None:
                    rows.append({
                        "Date": datetime.fromtimestamp(ts, tz=timezone.utc),
                        "Open": o or c,
                        "High": h or c,
                        "Low": l_ or c,
                        "Close": c,
                        "Volume": v or 0,
                    })

            df = pd.DataFrame(rows)
            logger.info("yahoo_http_fetched symbol=%s rows=%d range=%s", symbol, len(df), yf_range)
            return df
        except Exception as exc:
            logger.warning("yahoo_http_failed symbol=%s error=%s", symbol, exc)
            return pd.DataFrame()

    @staticmethod
    def _period_to_min_days(period: str) -> int:
        """Minimum days the cache must span for a given period to be adequate."""
        mapping = {
            "1d": 0, "5d": 3, "1m": 15, "1mo": 15, "3m": 60, "3mo": 60,
            "6m": 120, "6mo": 120, "1y": 300, "2y": 600, "5y": 1200, "max": 1200,
        }
        return mapping.get(period, 0)

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

        refresh_on_request = os.getenv("DATA_REFRESH_ON_REQUEST", "").strip().lower() in {"1", "true", "yes"}

        # Check if cache is adequate for the requested period
        cache_adequate = False
        if not cached.empty and not refresh_on_request:
            cached_days = (cached["Date"].max() - cached["Date"].min()).days
            needed_days = self._period_to_min_days(period)
            if cached_days >= needed_days:
                cache_adequate = True
                filtered = self._apply_period_filter(cached, period)
                return filtered[["Date", "Open", "High", "Low", "Close", "Volume"]].drop_duplicates("Date").sort_values("Date")
            else:
                logger.info(
                    "cache_inadequate commodity=%s cached_days=%d needed_days=%d period=%s — re-fetching",
                    commodity, cached_days, needed_days, period,
                )
                # Treat inadequate cache as empty so we do a full fresh fetch
                cached = pd.DataFrame()

        if cached.empty:
            # Try yfinance first, then fall back to direct HTTP
            try:
                fresh = yf.download(symbol, period=period, auto_adjust=False, progress=False, threads=False).reset_index()
                fresh = self._normalize_download(fresh)
            except Exception as exc:
                logger.warning("yfinance_download_failed symbol=%s error=%s", symbol, exc)
                fresh = pd.DataFrame()

            if fresh.empty:
                logger.info("yfinance_empty_fallback_http symbol=%s period=%s", symbol, period)
                fresh = self._fetch_via_http(symbol, period)
        else:
            last_dt = cached["Date"].max().to_pydatetime().replace(tzinfo=timezone.utc)
            start_date = (last_dt + timedelta(days=1)).date()
            if start_date > datetime.now(timezone.utc).date():
                fresh = cached.copy()
            else:
                try:
                    fresh = yf.download(
                        symbol,
                        start=start_date.isoformat(),
                        auto_adjust=False,
                        progress=False,
                        threads=False,
                    ).reset_index()
                    if not fresh.empty:
                        fresh = self._normalize_download(fresh)
                        fresh = pd.concat([cached, fresh], ignore_index=True)
                    else:
                        fresh = cached.copy()
                except Exception as exc:
                    logger.warning("yfinance_incremental_failed symbol=%s error=%s", symbol, exc)
                    fresh = cached.copy()

        if fresh.empty:
            logger.error("no_historical_data symbol=%s period=%s", symbol, period)
            return fresh

        fresh = fresh[["Date", "Open", "High", "Low", "Close", "Volume"]].drop_duplicates("Date")
        fresh = fresh.sort_values("Date").ffill().dropna()
        fresh.to_csv(path, index=False)
        return self._apply_period_filter(fresh, period)

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
