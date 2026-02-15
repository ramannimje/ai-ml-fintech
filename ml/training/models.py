from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_percentage_error, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


class Regressor(Protocol):
    def fit(self, x: pd.DataFrame, y: pd.Series) -> None: ...
    def predict(self, x: pd.DataFrame) -> np.ndarray: ...


@dataclass
class ModelResult:
    name: str
    model: object
    rmse: float
    mape: float


class LSTMRegressor:
    def __init__(self, input_dim: int, epochs: int = 15) -> None:
        self.scaler = StandardScaler()
        self.epochs = epochs
        self.model = nn.LSTM(input_size=input_dim, hidden_size=32, num_layers=1, batch_first=True)
        self.head = nn.Linear(32, 1)

    def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
        x_scaled = self.scaler.fit_transform(x)
        x_tensor = torch.tensor(x_scaled, dtype=torch.float32).unsqueeze(1)
        y_tensor = torch.tensor(y.values, dtype=torch.float32).unsqueeze(1)
        loader = DataLoader(TensorDataset(x_tensor, y_tensor), batch_size=32, shuffle=True)
        optimizer = torch.optim.Adam(list(self.model.parameters()) + list(self.head.parameters()), lr=1e-3)
        loss_fn = nn.MSELoss()
        self.model.train()
        for _ in range(self.epochs):
            for xb, yb in loader:
                optimizer.zero_grad()
                out, _ = self.model(xb)
                pred = self.head(out[:, -1, :])
                loss = loss_fn(pred, yb)
                loss.backward()
                optimizer.step()

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        self.model.eval()
        x_scaled = self.scaler.transform(x)
        with torch.no_grad():
            out, _ = self.model(torch.tensor(x_scaled, dtype=torch.float32).unsqueeze(1))
            pred = self.head(out[:, -1, :]).squeeze(1).numpy()
        return pred


class TinyTransformerRegressor:
    def __init__(self, input_dim: int, epochs: int = 12) -> None:
        self.scaler = StandardScaler()
        self.epochs = epochs
        encoder = nn.TransformerEncoderLayer(d_model=input_dim, nhead=2, batch_first=True)
        self.model = nn.TransformerEncoder(encoder, num_layers=2)
        self.head = nn.Linear(input_dim, 1)

    def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
        x_scaled = self.scaler.fit_transform(x)
        x_tensor = torch.tensor(x_scaled, dtype=torch.float32).unsqueeze(1)
        y_tensor = torch.tensor(y.values, dtype=torch.float32).unsqueeze(1)
        loader = DataLoader(TensorDataset(x_tensor, y_tensor), batch_size=32, shuffle=True)
        optimizer = torch.optim.Adam(list(self.model.parameters()) + list(self.head.parameters()), lr=5e-4)
        loss_fn = nn.MSELoss()
        self.model.train()
        for _ in range(self.epochs):
            for xb, yb in loader:
                optimizer.zero_grad()
                out = self.model(xb)
                pred = self.head(out[:, -1, :])
                loss = loss_fn(pred, yb)
                loss.backward()
                optimizer.step()

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        self.model.eval()
        x_scaled = self.scaler.transform(x)
        with torch.no_grad():
            out = self.model(torch.tensor(x_scaled, dtype=torch.float32).unsqueeze(1))
            pred = self.head(out[:, -1, :]).squeeze(1).numpy()
        return pred


class ProphetBaseline:
    def __init__(self) -> None:
        from prophet import Prophet

        self._model = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=True)

    def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
        frame = pd.DataFrame({"ds": x.index, "y": y.values})
        self._model.fit(frame)

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        future = pd.DataFrame({"ds": x.index})
        forecast = self._model.predict(future)
        return forecast["yhat"].to_numpy()


def benchmark_models(x: pd.DataFrame, y: pd.Series) -> list[ModelResult]:
    x_train, x_test, y_train, y_test = train_test_split(x, y, shuffle=False, test_size=0.2)
    results: list[ModelResult] = []

    candidates: list[tuple[str, Regressor]] = [
        ("xgboost", XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.05)),
        ("lstm", LSTMRegressor(input_dim=x.shape[1])),
        ("transformer", TinyTransformerRegressor(input_dim=x.shape[1])),
    ]

    for name, model in candidates:
        model.fit(x_train, y_train)
        pred = model.predict(x_test)
        results.append(ModelResult(name=name, model=model, rmse=float(root_mean_squared_error(y_test, pred)), mape=float(mean_absolute_percentage_error(y_test, pred))))

    try:
        prophet = ProphetBaseline()
        x_prophet = pd.DataFrame(index=pd.RangeIndex(start=0, stop=len(x), step=1))
        prophet.fit(x_prophet.iloc[: len(x_train)], y_train.reset_index(drop=True))
        pred = prophet.predict(x_prophet.iloc[len(x_train):])
        results.append(ModelResult(name="prophet", model=prophet, rmse=float(root_mean_squared_error(y_test, pred)), mape=float(mean_absolute_percentage_error(y_test, pred))))
    except Exception:
        pass

    return sorted(results, key=lambda r: r.rmse)
