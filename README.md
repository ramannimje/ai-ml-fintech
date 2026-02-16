# AI Commodity Predictor Monorepo

FastAPI + React market intelligence platform for commodity pricing and forecasting across India, US, and Europe.

## Multi-Region Pricing & Forecasting

The platform now supports regional pricing standards with canonical storage in **grams**:

| Region | Currency | Display Unit |
|---|---|---|
| India | INR | per 10 grams |
| United States | USD | per troy ounce |
| Europe | EUR | per gram |

How it works:
- Backend stores canonical `price_in_grams` and converts per region at response time.
- FX conversion uses exchangerate.host with 1-hour cache + fallback values.
- Historical data is region-tagged (`commodity`, `timestamp`, `region`, `price_in_grams`, `currency`, `source`).
- Forecasts provide short + long horizon points (including yearly milestones up to 2028).

### Forecast interpretation and limitations
- Long-horizon (to 2028) projections are model-based scenarios, not guaranteed outcomes.
- Accuracy decreases as horizon extends.
- Macro-exogenous features are included as extensible placeholders (inflation, USD index, rates).

## Monorepo Structure

```text
backend/    # FastAPI, ML pipeline, tests
frontend/   # React + Vite UI
infra/      # Nginx and infra compose assets
```

## API

All endpoints are served under `/api` and accept optional `region=india|us|europe`:
- `GET /api/commodities`
- `GET /api/historical/{commodity}?region=india&range=5y`
- `POST /api/train/{commodity}?region=us&horizon=30`
- `GET /api/predict/{commodity}?region=europe&horizon=30`
- `GET /api/metrics/{commodity}?region=us`
- `POST /api/retrain-all?region=india&horizon=7`

## Run locally (end-to-end)

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost`.

Nginx routing:
- `/` -> frontend
- `/api/*` -> backend

## Dev commands

```bash
make backend-dev
make frontend-dev
make test
make lint
make build
```

## Migration

A migration script for adding `region` column exists:
- `backend/alembic/versions/20260215_01_add_region_to_training_runs.py`


## Resolving PR conflicts against main

If your PR shows conflicts with `main` and you want to keep everything from your current branch, run:

```bash
bash backend/scripts/resolve_main_conflicts.sh origin/main
```

What it does:
- fetches latest refs
- merges `origin/main` into your current branch with `-X ours`
- if any unresolved paths remain, it force-keeps current branch versions and commits

Then push:

```bash
git push
```
