# Deployment Guide

## Local Setup

1. Configure backend env:

```bash
cp .env.example .env.local
```

2. Configure frontend env:

```bash
cp frontend/.env.example frontend/.env.local
```

3. Start local stack (Postgres, Redis, Backend, Nginx):

```bash
docker compose up --build
```

Local URLs:
- Nginx: `http://localhost`
- Backend health: `http://localhost/api/health`

## Backend Local (without Docker)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --reload
```

## Frontend Local

```bash
cd frontend
npm install
npm run dev
```

## Production Deployment

1. Deploy backend to Render using `render.yaml`.
2. Deploy frontend to Vercel and set `VITE_API_BASE_URL` to Render backend URL.
3. Create Supabase Postgres and set `DATABASE_URL`.
4. Create Upstash Redis and set `REDIS_URL` (TLS URL supported).
5. Configure Infisical project/environments and load production secrets.
6. Configure Auth0 app:
   - Allowed Callback URLs: backend callback URL
   - Allowed Web Origins: Vercel app URL

## Environment Model

- `ENVIRONMENT=local`: app reads `.env.local` and environment variables.
- `ENVIRONMENT=production`: app prefers Infisical for supported secrets; if missing, it falls back to environment variables.

## Health Check

Render health check path:

`GET /api/health`

Response:

```json
{
  "status": "ok"
}
```
