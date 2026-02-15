from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_percentage_error, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
try:
    from xgboost import XGBRegressor
except Exception:
    XGBRegressor = None


class Regressor(Protocol):
    def fit(self, x: pd.DataFrame, y: pd.Series) -> None: ...
    def predict(self, x: pd.DataFrame) -> np.ndarray: ...


@dataclass
class ModelResult:
    name: str
    model: object
    rmse: float
    mape: float


class ProphetBaseline:
    def __init__(self) -> None:
        from prophet import Prophet

        self._model = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=True)

    def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
        frame = pd.DataFrame({"ds": pd.date_range(start="2000-01-01", periods=len(y), freq="D"), "y": y.values})
        self._last_ds = frame["ds"].iloc[-1]
        self._model.fit(frame)

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        future = pd.DataFrame({"ds": pd.date_range(start=self._last_ds + pd.Timedelta(days=1), periods=len(x), freq="D")})
        forecast = self._model.predict(future)
        return forecast["yhat"].to_numpy()


def benchmark_models(x: pd.DataFrame, y: pd.Series) -> list[ModelResult]:
    x_train, x_test, y_train, y_test = train_test_split(x, y, shuffle=False, test_size=0.2)
    results: list[ModelResult] = []

    candidates: list[tuple[str, Regressor]] = [("random_forest", RandomForestRegressor(n_estimators=300, random_state=42))]
    if XGBRegressor is not None:
        candidates.append(("xgboost", XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.05)))

    for name, model in candidates:
        try:
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
        except Exception:
            continue

    try:
        prophet = ProphetBaseline()
        x_prophet = pd.DataFrame(index=pd.RangeIndex(start=0, stop=len(x), step=1))
        prophet.fit(x_prophet.iloc[: len(x_train)], y_train.reset_index(drop=True))
        pred = prophet.predict(x_prophet.iloc[len(x_train):])
        results.append(ModelResult(name="prophet", model=prophet, rmse=float(root_mean_squared_error(y_test, pred)), mape=float(mean_absolute_percentage_error(y_test, pred))))
    except Exception:
        pass

    return sorted(results, key=lambda r: r.rmse)
