# Docker Notes

Container assets are defined at repository root and under `backend/` and `frontend/`:

- `docker-compose.yml`
- `Dockerfile` (root app image)
- `backend/Dockerfile` (compose backend image)
- `frontend/Dockerfile`

## Compose Topology

- `backend`: FastAPI (`backend.main:app`) + Infisical CLI installed
- `frontend`: Vite dev server container
- `postgres`: PostgreSQL 15
- `nginx`: reverse proxy/public entrypoint

## Run

```bash
docker compose up --build
```

App is served at `http://localhost`.

## Environment

Compose forwards these Infisical vars to backend:

- `INFISICAL_PROJECT_ID`
- `INFISICAL_ENV`
- `INFISICAL_TOKEN`
- `INFISICAL_CLIENT_ID`
- `INFISICAL_CLIENT_SECRET`
- `INFISICAL_API_URL`

Keep real secret values in `.env` (local only). Do not place real values in `.env.example`.
