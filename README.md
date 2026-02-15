# AI Commodity Predictor Monorepo

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

### 3) Run backend locally (without Docker)

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Backend API base URL: `http://127.0.0.1:8000/api`

Quick checks:

```bash
curl -i http://127.0.0.1:8000/api/health
curl -i http://127.0.0.1:8000/api/commodities
```

### 4) Run frontend locally (without Docker)

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Open: `http://127.0.0.1:5173`

Notes:

- Vite dev server proxies `/api/*` to `http://127.0.0.1:8000`.
- If running frontend from a different host/port setup, create `frontend/.env.local`:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

### 5) Run split dev mode via Make (optional)

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
