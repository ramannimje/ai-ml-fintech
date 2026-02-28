from __future__ import annotations

import numpy as np
import pandas as pd


def add_features(df: pd.DataFrame, macro_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Add technical and macro features to OHLCV data.

    Args:
        df: OHLCV DataFrame with Date, Open, High, Low, Close, Volume columns.
        macro_df: Optional macro features DataFrame (DXY, treasury_10y) indexed by Date.

    Returns:
        Feature-enriched DataFrame with NaN rows dropped.
    """
    out = df.copy()
    out["returns"] = out["Close"].pct_change()
    out["ma_5"] = out["Close"].rolling(5).mean()
    out["ma_20"] = out["Close"].rolling(20).mean()
    out["volatility_20"] = out["returns"].rolling(20).std()
    out["lag_1"] = out["Close"].shift(1)
    out["lag_7"] = out["Close"].shift(7)
    out["rolling_min_14"] = out["Close"].rolling(14).min()
    out["rolling_max_14"] = out["Close"].rolling(14).max()

    delta = out["Close"].diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = pd.Series(gain).rolling(14).mean()
    avg_loss = pd.Series(loss).rolling(14).mean().replace(0, 1e-9)
    rs = avg_gain / avg_loss
    out["rsi"] = 100 - (100 / (1 + rs))

    # Cyclical time features for long-horizon forecasting
    if "Date" in out.columns:
        dates = pd.to_datetime(out["Date"])
        out["month_sin"] = np.sin(2 * np.pi * dates.dt.month / 12)
        out["month_cos"] = np.cos(2 * np.pi * dates.dt.month / 12)
        out["year_norm"] = (dates.dt.year - 2000) / 30.0  # normalized year

    # Merge macro features if provided
    if macro_df is not None and not macro_df.empty:
        if "Date" in out.columns:
            out = out.set_index("Date")
            out = out.join(macro_df, how="left")
            out = out.reset_index()
            out = out.rename(columns={"index": "Date"})
        out["dxy"] = out.get("dxy", pd.Series(np.nan, index=out.index)).ffill().bfill()
        out["treasury_10y"] = out.get("treasury_10y", pd.Series(np.nan, index=out.index)).ffill().bfill()

    return out.dropna().reset_index(drop=True)


def make_supervised(df: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, pd.Series]:
    """
    Create supervised learning features and target.
    Target is Close price shifted by horizon days.
    """
    base_features = [
        "Close",
        "Open",
        "High",
        "Low",
        "Volume",
        "returns",
        "ma_5",
        "ma_20",
        "volatility_20",
        "lag_1",
        "lag_7",
        "rolling_min_14",
        "rolling_max_14",
        "rsi",
    ]

    # Add optional features if present
    optional_features = ["month_sin", "month_cos", "year_norm", "dxy", "treasury_10y"]
    features = base_features + [f for f in optional_features if f in df.columns]

    work = df.copy()
    work["target"] = work["Close"].shift(-horizon)
    work = work.dropna().reset_index(drop=True)
    return work[features], work["target"]
