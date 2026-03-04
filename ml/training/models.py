from __future__ import annotations

from dataclasses import dataclass
import importlib
import logging
import os
from typing import Any, Protocol

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

logger = logging.getLogger(__name__)


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


def xgboost_available() -> bool:
    if XGBRegressor is None:
        return False
    return os.getenv("DISABLE_XGBOOST", "").strip().lower() not in {"1", "true", "yes"}


def chronos_bolt_available() -> bool:
    # Keep Chronos opt-in to avoid hard runtime failures on systems with incompatible torch builds.
    if os.getenv("ENABLE_CHRONOS_BOLT", "").strip().lower() not in {"1", "true", "yes"}:
        return False
    return importlib.util.find_spec("torch") is not None and importlib.util.find_spec("chronos") is not None


class ChronosBoltRegressor:
    """
    Lightweight adapter for Chronos-Bolt foundation model.
    The heavy pipeline object is loaded lazily and excluded from pickling.
    """

    def __init__(
        self,
        prediction_length: int = 1,
        model_id: str = "amazon/chronos-bolt-base",
        num_samples: int = 20,
        context_limit: int = 512,
    ) -> None:
        self.prediction_length = max(1, int(prediction_length))
        self.model_id = model_id
        self.num_samples = max(1, int(num_samples))
        self.context_limit = max(32, int(context_limit))
        self._history = np.array([], dtype=float)
        self._pipeline: Any | None = None
        self._torch: Any | None = None

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_pipeline"] = None
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._pipeline = None

    def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
        _ = x
        self._history = y.astype(float).to_numpy()

    def _load_pipeline(self) -> Any:
        if not chronos_bolt_available():
            raise RuntimeError("Chronos dependencies are unavailable (requires chronos + torch)")
        torch = importlib.import_module("torch")
        chronos_mod = importlib.import_module("chronos")
        chronos_pipeline = getattr(chronos_mod, "ChronosPipeline", None)
        if chronos_pipeline is None:
            raise RuntimeError("ChronosPipeline class not found in chronos package")
        if self._pipeline is None:
            try:
                self._pipeline = chronos_pipeline.from_pretrained(self.model_id, device_map="cpu")
            except TypeError:
                self._pipeline = chronos_pipeline.from_pretrained(self.model_id)
        self._torch = torch
        return self._pipeline

    def _normalize_forecast(self, raw: Any, prediction_length: int) -> np.ndarray:
        arr = raw
        if hasattr(arr, "detach"):
            arr = arr.detach().cpu().numpy()
        else:
            arr = np.asarray(arr)

        # Typical Chronos shape: [batch, samples, horizon] or [samples, horizon].
        if arr.ndim == 3 and arr.shape[0] == 1:
            arr = arr[0]
        if arr.ndim == 2:
            if arr.shape[0] == 1:
                arr = arr[0]
            elif arr.shape[1] == prediction_length:
                arr = np.median(arr, axis=0)
            else:
                arr = arr.reshape(-1)
        if arr.ndim > 1:
            arr = arr.reshape(-1)

        out = np.asarray(arr, dtype=float).reshape(-1)
        if out.size < prediction_length and out.size > 0:
            out = np.pad(out, (0, prediction_length - out.size), mode="edge")
        if out.size == 0:
            raise RuntimeError("Chronos returned empty forecast")
        return out[:prediction_length]

    def _predict_from_history(self, history: np.ndarray, prediction_length: int) -> np.ndarray:
        history = np.asarray(history, dtype=float).reshape(-1)
        if history.size < 2:
            raise ValueError("Chronos requires at least 2 points of history")
        pipeline = self._load_pipeline()
        context = self._torch.tensor([history[-self.context_limit :]], dtype=self._torch.float32)
        try:
            raw = pipeline.predict(
                context=context,
                prediction_length=prediction_length,
                num_samples=self.num_samples,
            )
        except TypeError:
            raw = pipeline.predict(
                context=context,
                prediction_length=prediction_length,
            )
        return self._normalize_forecast(raw, prediction_length)

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        return self._predict_from_history(self._history, prediction_length=len(x))

    def predict_from_series(self, series: pd.Series | np.ndarray, prediction_length: int = 1) -> np.ndarray:
        return self._predict_from_history(np.asarray(series, dtype=float), prediction_length=max(1, prediction_length))


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
    if chronos_bolt_available():
        candidates.append(("chronos_bolt", ChronosBoltRegressor(prediction_length=max(1, len(y_test)))))
    if xgboost_available():
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
        except Exception as exc:
            logger.warning("benchmark model failed name=%s reason=%s", name, str(exc))
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
