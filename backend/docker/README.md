# Backend Docker Notes

The backend container image is built from `backend/Dockerfile`.

## What it includes

- Python 3.11 slim base
- Infisical CLI installation
- Backend requirements from `backend/requirements.txt`
- App source under `/app/backend`

## Entrypoint

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

(`backend.main` re-exports `app.main`.)

## Usage

Normally run through root `docker-compose.yml`:

```bash
docker compose up --build backend
```
