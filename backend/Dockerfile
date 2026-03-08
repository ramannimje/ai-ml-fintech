FROM python:3.11-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -1sLf "https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh" | bash \
    && apt-get install -y --no-install-recommends infisical \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
COPY app ./app
COPY ml ./ml
COPY backend ./backend
COPY .env.production ./.env.production
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
