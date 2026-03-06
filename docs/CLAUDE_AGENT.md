# Agent Guide

This document is the practical context for coding agents working in this repository.

## Project Summary

AI-enabled commodity platform with:

- FastAPI backend (`app/`)
- React + Vite frontend (`frontend/`)
- ML forecasting pipeline (`ml/`)
- Alerting (email + WhatsApp)
- Auth0 auth + profile/settings persistence
- Gemini/OpenAI/Ollama provider support for AI chat

## Current Backend Architecture

- Entry: `app/main.py`
- Core routes: `app/api/routes.py`
- AI chat routes: `app/api/routes_ai_chat.py`
- Settings routes: `app/api/routes_settings.py`
- Optional auth routes: `app/api/auth_routes.py`

Main services:

- `CommodityService` for market/historical/predict/train
- `AIChatService` for LLM calls and advisory logic
- `AlertService` for alert CRUD/evaluation/history/export
- `ProfileService` and `SettingsService` for user preferences
- `VaultService` for Infisical runtime secret retrieval

## AI Chat (Important)

Advisory-intent questions are handled through a Gemini-first path:

1. Detect advisory intent (`isAdvisoryQuestion`)
2. Fetch market context
3. Build dynamic advisory prompt
4. Generate response with Gemini

Behavior constraints:

- No template advisory response for advisory questions
- If Gemini advisory generation fails, return:
  - `We are unable to generate an advisory response at the moment. Please try again.`

## Data and Model Notes

- Regions: `india`, `us`, `europe`
- Forecast-supported commodities: `gold`, `silver`, `crude_oil`
- Additional tracked commodities for market data include `natural_gas`, `copper`
- Prediction horizon constrained to `1..90` days

## Secrets

Secrets are loaded with namespace mapping in `app/core/secrets.py`:

- `/ai`, `/database`, `/email`, `/auth`

`VaultService` uses Infisical CLI when available and credentials are configured; otherwise values fall back to environment variables.

## Local Development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

## Test Targets

Run all backend tests:

```bash
pytest -q
```

Useful targeted suite for AI chat changes:

```bash
pytest -q tests/test_ai_chat_api.py tests/test_resilience_sources.py
```

## Agent Checklist for Changes

1. Keep docs and behavior aligned when touching AI, auth, or secrets.
2. Do not commit real secrets to `.env.example`.
3. Prefer targeted tests for changed subsystems before broad test runs.
4. If changing AI chat behavior, update both route-level and service-level tests.
