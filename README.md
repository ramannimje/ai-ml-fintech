# ai-commodity-predictor

Production-style commodity price forecasting service built with FastAPI, async SQLAlchemy, PostgreSQL, and multiple ML models (XGBoost, LSTM, Transformer, Prophet baseline).

## Features
- Async FastAPI backend with structured JSON APIs
- Supported commodities: Gold, Silver, Crude Oil
- Automatic historical download via Yahoo Finance (`yfinance`)
- Cached + incremental data refresh in `ml/cache/`
- Feature engineering: MA, RSI, volatility, lagged values, returns, rolling min/max
- Model training + comparison across multiple model families
- Automatic best-model selection by validation RMSE
- Model artifact persistence in `ml/artifacts/`
- Metadata tracking in PostgreSQL (`training_runs`)

## Repository structure

```text
app/
    api/
    core/
    services/
    models/
    schemas/
    db/
ml/
    data/
    features/
    training/
    inference/
    evaluation/
tests/
scripts/
docker/
```

## Quickstart (local)

1. Copy env file:
```bash
cp .env.example .env
```

2. Start services:
```bash
docker-compose up --build
```

3. API docs:
- http://localhost:8000/docs

## Make commands

```bash
make install
make run
make test
make train
make predict
```

## Core API endpoints
- `GET /health`
- `GET /commodities`
- `GET /historical/{commodity}`
- `POST /train/{commodity}?horizon=1|7|30`
- `GET /predict/{commodity}?horizon=1|7|30`
- `GET /metrics/{commodity}`
- `POST /retrain-all?horizon=1|7|30`

## Example train + predict

Train gold model:
```bash
curl -X POST "http://localhost:8000/train/gold?horizon=7"
```

Predict gold price:
```bash
curl "http://localhost:8000/predict/gold?horizon=7"
```

Example response:
```json
{
  "commodity": "gold",
  "prediction_date": "2026-02-20",
  "predicted_price": 74850.23,
  "confidence_interval": [74210.11, 75420.55],
  "model_used": "transformer_20260213010101",
  "model_accuracy_rmse": 412.4,
  "horizon_days": 7
}
```

## Scripts

Train commodity:
```bash
python scripts/train.py gold --horizon 1
```

Predict commodity:
```bash
python scripts/predict.py gold --horizon 30
```

