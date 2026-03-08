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

## Production Deployment (Railway & Vercel)

We use **Railway** for the backend (due to better resource availability for ML training and no sleep phase) and **Vercel** for the frontend.

### 1. Backend (Railway)

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project** → **Deploy from GitHub repo** → select `ai-ml-fintech`.
3. Railway will automatically detect the `railway.json` file and use the `backend/Dockerfile`.
4. Once deployed, click on the service → **Variables** and add the following:

   | Variable | Value |
   |----------|-------|
   | `ENVIRONMENT` | `production` |
   | `DATABASE_URL` | *(your Supabase PostgreSQL URL)* |
   | `AUTH0_DOMAIN` | `dev-mrxlgcmm2f0itm0g.us.auth0.com` |
   | `AUTH0_CLIENT_ID` | `0aSmSDeSBI3UbUA4ls7MzJCEAsavmWg7` |
   | `INFISICAL_PROJECT_ID` | *(from Infisical)* |
   | `INFISICAL_ENV` | `prod` |
   | `INFISICAL_CLIENT_ID` | *(from Infisical)* |
   | `INFISICAL_CLIENT_SECRET` | *(from Infisical)* |

5. Go to the **Settings** tab → click **Generate Domain** under Public Networking to get your public URL (e.g., `ai-ml-fintech-production.up.railway.app`).

### 2. Frontend (Vercel)

1. Go to [vercel.com](https://vercel.com) and sign in.
2. If the project already exists, go to **Settings** → **Environment Variables**.
3. Set/Update `VITE_API_BASE_URL` to the new Railway URL from step 5 (e.g., `https://ai-ml-fintech-production.up.railway.app/api`).
4. Trigger a new deployment in Vercel.

### 3. Auth0 Configuration

1. Log in to your Auth0 Dashboard.
2. Go to **Applications** → select your application.
3. Update **Allowed Callback URLs** to include your new Railway URL: `https://<YOUR_RAILWAY_URL>/api/auth/callback`
4. Ensure **Allowed Web Origins** and **Allowed Logout URLs** include your Vercel URL.

## Environment Model

- `ENVIRONMENT=local`: app reads `.env.local` and environment variables.
- `ENVIRONMENT=production`: app prefers Infisical for supported secrets; if missing, it falls back to environment variables.

## Health Check

Railway health check path (automatically parsed from `railway.json`):

`GET /api/health`

Response:

```json
{
  "status": "ok"
}
```
