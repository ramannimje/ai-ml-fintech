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
                   '- AI chat service (Gemini/OpenAI/Ollama)
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
- `/api/train/{commodity}/{region}`
- `/api/news-summary/{commodity}`

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
3. Call Gemini directly
4. Return Gemini output

Template-based advisory answers are not returned for advisory queries.

On Gemini advisory failure, response text is fixed:

`We are unable to generate an advisory response at the moment. Please try again.`

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
