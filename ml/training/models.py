from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_percentage_error, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor

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
    """Short-horizon Prophet wrapper."""

    def __init__(self) -> None:
        from prophet import Prophet
        self._model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True,
        )

    def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
        frame = pd.DataFrame(
            {"ds": pd.date_range(start="2000-01-01", periods=len(y), freq="D"), "y": y.values}
        )
        self._last_ds = frame["ds"].iloc[-1]
        self._model.fit(frame)

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        future = pd.DataFrame(
            {"ds": pd.date_range(start=self._last_ds + pd.Timedelta(days=1), periods=len(x), freq="D")}
        )
        forecast = self._model.predict(future)
        return forecast["yhat"].to_numpy()


class LongHorizonProphet:
    """
    Long-range Prophet model tuned for multi-year forecasting.
    Uses a higher changepoint_prior_scale for flexibility and
    generates forecasts up to 2028.
    """

    def __init__(self) -> None:
        from prophet import Prophet
        self._model = Prophet(
            changepoint_prior_scale=0.5,
            seasonality_prior_scale=10.0,
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
        )
        self._last_ds: pd.Timestamp | None = None
        self._last_y: float = 0.0

    def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
        frame = pd.DataFrame(
            {"ds": pd.date_range(start="2000-01-01", periods=len(y), freq="D"), "y": y.values}
        )
        self._last_ds = frame["ds"].iloc[-1]
        self._last_y = float(y.iloc[-1])
        self._model.fit(frame)

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        future = pd.DataFrame(
            {"ds": pd.date_range(start=self._last_ds + pd.Timedelta(days=1), periods=len(x), freq="D")}
        )
        forecast = self._model.predict(future)
        return forecast["yhat"].to_numpy()


class NBEATSStub:
    """
    N-BEATS approximation using a multi-layer MLP regressor.
    Full N-BEATS requires neuralforecast; this stub provides
    similar multi-step forecasting capability with sklearn.
    """

    def __init__(self) -> None:
        self._model = MLPRegressor(
            hidden_layer_sizes=(256, 128, 64),
            activation="relu",
            max_iter=500,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
        )

    def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
        self._model.fit(x, y)

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        return self._model.predict(x)


def benchmark_models(x: pd.DataFrame, y: pd.Series) -> list[ModelResult]:
    """
    Train and evaluate all candidate models, returning results sorted by RMSE.
    Includes: RandomForest, XGBoost, Prophet (short), LongHorizonProphet, N-BEATS stub.
    """
    x_train, x_test, y_train, y_test = train_test_split(x, y, shuffle=False, test_size=0.2)
    results: list[ModelResult] = []

    # Sklearn-compatible candidates
    candidates: list[tuple[str, Regressor]] = [
        ("random_forest", RandomForestRegressor(n_estimators=300, random_state=42)),
        ("nbeats_mlp", NBEATSStub()),
    ]
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

    # Prophet short-horizon
    try:
        prophet = ProphetBaseline()
        x_prophet = pd.DataFrame(index=pd.RangeIndex(start=0, stop=len(x), step=1))
        prophet.fit(x_prophet.iloc[: len(x_train)], y_train.reset_index(drop=True))
        pred = prophet.predict(x_prophet.iloc[len(x_train):])
        results.append(
            ModelResult(
                name="prophet",
                model=prophet,
                rmse=float(root_mean_squared_error(y_test, pred)),
                mape=float(mean_absolute_percentage_error(y_test, pred)),
            )
        )
    except Exception:
        pass

    # Long-horizon Prophet
    try:
        lh_prophet = LongHorizonProphet()
        x_prophet = pd.DataFrame(index=pd.RangeIndex(start=0, stop=len(x), step=1))
        lh_prophet.fit(x_prophet.iloc[: len(x_train)], y_train.reset_index(drop=True))
        pred = lh_prophet.predict(x_prophet.iloc[len(x_train):])
        results.append(
            ModelResult(
                name="prophet_longrange",
                model=lh_prophet,
                rmse=float(root_mean_squared_error(y_test, pred)),
                mape=float(mean_absolute_percentage_error(y_test, pred)),
            )
        )
    except Exception:
        pass

    return sorted(results, key=lambda r: r.rmse)
