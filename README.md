# AI Commodity Predictor

End-to-end commodity forecasting platform with a FastAPI backend and premium React frontend, served as one application through Nginx.

## Monorepo Structure

```text
ai-commodity-predictor/
├── backend/
│   ├── app/
│   ├── ml/
│   ├── tests/
│   ├── docker/
│   ├── requirements.txt
│   └── main.py
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── infra/
│   ├── nginx/
│   └── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

## Architecture

```text
Browser
  │
  ▼
Nginx (single entrypoint :80)
  ├── /      -> Frontend (React + Vite)
  └── /api/* -> Backend (FastAPI + ML services)
                    ├── PostgreSQL metadata (training_runs)
                    └── Model/data artifacts on filesystem
```

## Frontend Stack

- React 18 + TypeScript + Vite
- TailwindCSS + utility-first dark UI
- TanStack Query (cache + fetch orchestration)
- Zustand (theme persistence)
- Recharts (market and prediction visuals)
- React Router v6
- Axios + Zod API client validation
- Framer Motion animations
- Vitest + ESLint + Typecheck

## Backend API (proxied by Nginx)

- `GET /api/health`
- `GET /api/commodities`
- `GET /api/historical/{commodity}`
- `POST /api/train/{commodity}?horizon=1|7|30`
- `GET /api/predict/{commodity}?horizon=1|7|30`
- `GET /api/metrics/{commodity}`
- `POST /api/retrain-all?horizon=1|7|30`

## Local Setup

### 1) Environment

```bash
cp .env.example .env
```

### 2) Run full stack (recommended)

```bash
docker compose up --build
```

Open: `http://localhost/`

### 3) Run in split dev mode

Terminal A:

```bash
make backend-dev
```

Terminal B:

```bash
make frontend-dev
```

## Developer Commands

```bash
make dev      # full stack via Docker
make build    # frontend build + docker build
make test     # backend pytest + frontend vitest
make lint     # frontend eslint + typecheck
```

## How frontend talks to backend

- All UI calls use `frontend/src/api/client.ts` with base URL `/api`.
- Nginx routes `/api/*` to backend service.
- React Query policies:
  - Historical: stale 10 minutes
  - Metrics: stale 5 minutes
  - Predictions: no cache (stale 0)

## Screenshots

- Dashboard (placeholder): `docs/screenshots/dashboard.png`
- Commodity detail (placeholder): `docs/screenshots/commodity.png`
- Train models (placeholder): `docs/screenshots/train.png`
- Metrics table (placeholder): `docs/screenshots/metrics.png`
