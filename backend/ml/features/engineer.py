from __future__ import annotations

import numpy as np
import pandas as pd


def add_features(df: pd.DataFrame) -> pd.DataFrame:
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

    return out.dropna().reset_index(drop=True)


def make_supervised(df: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, pd.Series]:
    features = [
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
    work = df.copy()
    work["target"] = work["Close"].shift(-horizon)
    work = work.dropna().reset_index(drop=True)
    return work[features], work["target"]
