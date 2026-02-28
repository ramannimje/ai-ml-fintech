# AI Commodity Predictor Platform Notes

## Architecture Diagram

```text
React + TS + Tailwind (frontend)
            |
            v
        Nginx :80
     /api/*      / 
      |          |
      v          v
  FastAPI + ML   Vite build
      |
      v
SQLite/Postgres metadata + local model/data artifacts
```

## Data Flow Diagram

```text
Primary bullion feed intent: LBMA/MCX/COMEX
Operational fallback: Yahoo Finance
            |
            v
    Canonical USD/oz prices
            |
            v
     FX conversion layer
     (ECB -> fallback FX API -> stale cache)
            |
            v
 Region-adjusted outputs (INR 10g_24k / USD oz / EUR exchange_standard)
```

## Model Flow

1. Fetch region-tagged historical OHLC.
2. Build features including `fx_volatility`, `inflation_proxy`, `interest_rates_fred_ecb_rbi`.
3. Train region-specific model.
4. Validate with walk-forward split.
5. Persist artifact + training metadata.
6. Predict to fixed horizon `2026-12-31` with bull/base/bear scenarios.

## Live Price Source Explanation

- Live endpoint uses market close from commodity symbols and reports source metadata (`comex/yahoo_finance` or fallback path).
- Pricing values are never hardcoded.
- FX conversion is real-time with 60s TTL cache.

## Region Unit Logic

- `india`: `INR`, `10g_24k`
- `us`: `USD`, `oz`
- `europe`: `EUR`, `exchange_standard`

## Prediction Methodology

- Point forecast from latest trained region model.
- Confidence interval from model RMSE envelope.
- Scenario output:
  - Bull: `+6%`
  - Base: `point_forecast`
  - Bear: `-6%`

## Environment Config

- `DATABASE_URL`
- `DATA_CACHE_DIR`
- `ARTIFACT_DIR`
- `FX_API_URL` (optional fallback override)

## API Keys Required

- None mandatory for fallback mode (`yfinance`, public ECB feed, public fallback FX API).

## Retrain Steps

1. `POST /api/train/{commodity}/{region}?horizon=30`
2. Verify `model_version` in response.
3. Query prediction endpoint for updated outputs.

## Swagger Validation

1. Start backend.
2. Open `/docs`.
3. Validate all five target routes return schema-compliant payloads.

## Test Instructions

- Backend: `pytest -q tests`
- Frontend: `cd frontend && npm test`

## Troubleshooting

- FX failures: service falls back ECB -> fallback API -> stale cache.
- Empty live data: verify outbound internet access for market feeds.
- Missing artifacts: ensure `ARTIFACT_DIR` writable and retrain endpoint succeeds.
