# TradeSight

AI-powered multi-region commodity market intelligence platform with a FastAPI backend, React frontend, model-driven forecasting, alerts, and Gemini-based advisory chat.

## Stack

- Backend: FastAPI, SQLAlchemy (async), Pydantic, Redis, Auth0
- Frontend: React + TypeScript + Vite + TanStack Query
- ML/Data: pandas, yfinance, model artifacts in `ml/`
- Secrets: Infisical via runtime `VaultService` (`app/services/vault_service.py`)
- Deployment: Docker Compose + Nginx + Postgres

## Repository Layout

```text
app/                 FastAPI app (APIs, services, models)
frontend/            React app
ml/                  ML pipelines, artifacts, cached datasets
infra/nginx/         Nginx config
backend/             Docker/backend wrapper (`backend.main` -> `app.main`)
tests/               Pytest suites
```

## Key Functionality

- Live commodity pricing by region (`india`, `us`, `europe`)
- Historical data and forecasting (`gold`, `silver`, `crude_oil`)
- User profile + settings (preferred region, prediction horizon)
- Alerts: email + WhatsApp, history, CSV export
- News summaries per commodity
- AI chat endpoints with provider abstraction (Gemini/OpenAI/Ollama)
- Advisory query handling: advisory questions are generated directly by Gemini with dynamic market context

## AI Chat Behavior (Latest)

For advisory-style questions (for example, buy/sell/invest/hold timing):

1. Build market data context
2. Construct a dynamic advisory prompt
3. Call Gemini directly
4. Return Gemini output

No template response is used for advisory questions. If Gemini cannot respond, API returns:

`We are unable to generate an advisory response at the moment. Please try again.`

## API Surface (high level)

Core:

- `GET /api/health`
- `GET /api/regions`
- `GET /api/commodities`
- `GET /api/live-prices`
- `GET /api/live-prices/{region}`
- `GET /api/public/live-prices/{region}`
- `GET /api/historical/{commodity}/{region}`
- `GET /api/predict/{commodity}/{region}`
- `POST /api/train/{commodity}/{region}`

Alerts/Profile:

- `POST /api/alerts`
- `POST /api/alerts/whatsapp`
- `GET /api/alerts`
- `PATCH /api/alerts/{alert_id}`
- `DELETE /api/alerts/{alert_id}`
- `GET /api/alerts/history`
- `GET /api/alerts/history/export`
- `POST /api/alerts/evaluate`
- `GET /api/profile`
- `PUT /api/profile`
- `GET /api/settings`
- `POST /api/settings`

AI:

- `POST /api/ai/chat`
- `POST /api/ai/chat/stream`
- `GET /api/ai/provider-status`

Auth (if authlib installed):

- `GET /api/auth/login`
- `GET /api/auth/callback`
- `POST /api/auth/logout`
- `GET /api/auth/me`

## Environment and Secrets

1. Copy sample env:

```bash
cp .env.example .env
```

2. Keep real secrets in local `.env` (never commit).

3. For Infisical-backed secret loading, configure:

- `INFISICAL_PROJECT_ID`
- `INFISICAL_ENV`
- Either `INFISICAL_TOKEN` or (`INFISICAL_CLIENT_ID` + `INFISICAL_CLIENT_SECRET`)

4. Secrets are read by namespace paths:

- `/ai`: `OPENAI_API_KEY`, `GEMINI_API_KEY`, ...
- `/database`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_DB`
- `/email`: `SENDGRID_API_KEY`, `RESEND_API_KEY`
- `/auth`: `AUTH0_SECRET`, `JWT_SECRET`, messaging auth tokens

## Run Locally

Backend:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Run with Docker Compose

```bash
docker compose up --build
```

Nginx entrypoint: `http://localhost`

## Tests

```bash
source .venv/bin/activate
pytest -q
```

Targeted AI smoke tests:

```bash
pytest -q tests/test_ai_chat_api.py tests/test_resilience_sources.py
```

## Notes

- `/api/ai/chat` and `/api/ai/chat/stream` are rate-limited (`40 req / 60s` per user key).
- Provider status endpoint helps debug model availability/cooldowns.
- `VaultService` gracefully falls back to env vars if Infisical is unavailable.
