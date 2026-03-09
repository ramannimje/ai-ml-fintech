# Platform Notes

## Runtime Architecture

```text
Browser
  |
  v
Nginx (:80)
  |- /        -> Frontend (Vite/React)
  '- /api/*   -> FastAPI (`app.main`)
                   |- SQLAlchemy (SQLite/Postgres)
                   |- Commodity/ML services
                   |- Alert services (email/whatsapp)
                   '- AI chat service (OpenRouter)
```

## Data + Forecasting Flow

1. Fetch market data (primary + fallback providers)
2. Normalize to region-specific units/currency
3. Build historical features and trend metrics
4. Run prediction model (`gold`, `silver`, `crude_oil`) with horizon `1..90`
5. Return point forecast + confidence interval + scenarios

## Supported Regions and Units

- `india` -> `INR`, `10g`
- `us` -> `USD`, `oz`
- `europe` -> `EUR`, `exchange_standard`

## API Groups

Market:

- `/api/health`
- `/api/regions`
- `/api/commodities`
- `/api/live-prices`
- `/api/live-prices/{region}`
- `/api/public/live-prices/{region}`
- `/api/historical/{commodity}/{region}`
- `/api/predict/{commodity}/{region}`
- `/api/train/{commodity}/{region}` (returns 202 Accepted)
- `/api/train/{commodity}/{region}/status` (polls in-memory progress cache)
- `/api/news-summary/{commodity}`

## Async ML Training Architecture

Due to the heavy resource requirements of training ML models (Prophet, XGBoost, N-BEATS, Random Forest), the `/api/train` endpoint executes asynchronously:

1. **Initiation**: FastAPI receives the POST request and immediately returns a `202 Accepted` response.
2. **Background Task**: The actual training loop (`CommodityService.train()`) is passed to FastAPI's `BackgroundTasks`, running outside the main event loop to prevent API blocking/timeouts.
3. **Optimized Scoring**: The system calculates metrics using an 80/20 train/test split via `benchmark_models` instead of redundant cross-validation walk-forward loops, reducing runtime from 4 minutes to under 30 seconds.
4. **Status Polling**: The React frontend actively polls the new `/status` endpoint every 5 seconds, which reads an in-memory `_training_status` cache to determine if the job is `processing`, `completed`, or `failed`.

AI:

- `/api/ai/chat`
- `/api/ai/chat/stream`
- `/api/ai/provider-status`

User/Alerts:

- `/api/profile` (GET/PUT)
- `/api/settings` (GET/POST)
- `/api/alerts` (CRUD)
- `/api/alerts/whatsapp`
- `/api/alerts/history`
- `/api/alerts/history/export`
- `/api/alerts/evaluate`

Auth:

- `/api/auth/login`
- `/api/auth/callback`
- `/api/auth/logout`
- `/api/auth/me`

## AI Advisory Behavior (Current)

Advisory-intent questions (buy/sell/invest/hold/entry/exit/forecast timing) follow this path:

1. Build user + market context
2. Build dynamic advisory prompt
3. Call OpenRouter (`qwen/qwen3-next-80b-a3b-instruct`)
4. Return model output

If the provider call fails, the service falls back to deterministic engine output.

## Secrets and Configuration

Secret resolution order:

1. Infisical via `VaultService`
2. Environment fallback
3. Default value (if provided)

Namespaces in `app/core/secrets.py`:

- `AI_SECRETS` -> `/ai`
- `DB_SECRETS` -> `/database`
- `EMAIL_SECRETS` -> `/email`
- `AUTH_SECRETS` -> `/auth`

Infisical runtime config keys:

- `INFISICAL_PROJECT_ID`, `INFISICAL_ENV`
- `INFISICAL_TOKEN` or `INFISICAL_CLIENT_ID` + `INFISICAL_CLIENT_SECRET`
- Optional tuning: cache/refresh/retry settings in `.env.example`

## Dev Commands

```bash
# backend
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend && npm run dev

# tests
pytest -q
```

## Operational Notes

- AI chat endpoints are rate-limited per user key.
- Background WhatsApp alert worker starts on app startup when enabled.
- Database schema guards run at startup for alerts/training tables.
