from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_percentage_error, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from xgboost import XGBRegressor


@dataclass
class ModelResult:
    name: str
    model: object
    rmse: float
    mape: float


def benchmark_models(x: pd.DataFrame, y: pd.Series) -> list[ModelResult]:
    x_train, x_test, y_train, y_test = train_test_split(x, y, shuffle=False, test_size=0.2)
    candidates: list[tuple[str, object]] = [
        ("xgboost", XGBRegressor(n_estimators=250, max_depth=6, learning_rate=0.04)),
        ("temporal_fusion_transformer", MLPRegressor(hidden_layer_sizes=(128, 64), max_iter=500)),
        ("nbeats", RandomForestRegressor(n_estimators=250, random_state=42)),
    ]

    results: list[ModelResult] = []
    for name, model in candidates:
        model.fit(x_train, y_train)
        pred = model.predict(x_test)
        results.append(
            ModelResult(
                name=name,
                model=model,
                rmse=float(root_mean_squared_error(y_test, pred)),
                mape=float(mean_absolute_percentage_error(y_test, pred)),
            )
        )

    try:
        from prophet import Prophet

        frame = pd.DataFrame({"ds": pd.date_range("2020-01-01", periods=len(y_train), freq="D"), "y": y_train.values})
        p = Prophet(yearly_seasonality=True)
        p.fit(frame)
        future = pd.DataFrame({"ds": pd.date_range("2020-01-01", periods=len(y_train) + len(y_test), freq="D")})
        fc = p.predict(future)["yhat"].tail(len(y_test)).to_numpy()
        results.append(
            ModelResult(
                name="prophet_long_range",
                model=p,
                rmse=float(root_mean_squared_error(y_test, fc)),
                mape=float(mean_absolute_percentage_error(y_test, fc)),
            )
        )
    except Exception:
        pass

    return sorted(results, key=lambda r: r.rmse)
