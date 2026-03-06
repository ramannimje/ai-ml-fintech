# Codex Agent Implementation Prompt

## Purpose

This repository is **TradeSight** — an AI-powered multi-region commodity market intelligence platform. When implementing changes, align with current production behavior instead of legacy assumptions.

## Current Technical Reality

- Backend: FastAPI app rooted at `app/main.py`
- Frontend: React + TypeScript + Vite
- Auth: Auth0 (optional auth routes if authlib is available)
- Secrets: runtime retrieval via `VaultService` + `get_secret_value`
- AI chat: provider abstraction with Gemini/OpenAI/Ollama
- Advisory questions: Gemini-first dynamic generation path

## Non-Negotiable AI Chat Behavior

For advisory intent (buy/sell/invest/hold/entry/exit/forecast timing):

1. Build market context
2. Build dynamic prompt from context + user question
3. Call Gemini
4. Return generated answer

Do not return canned or template advisory responses.

If advisory Gemini generation fails, return exactly:

`We are unable to generate an advisory response at the moment. Please try again.`

## API Surfaces to Preserve

- Market: `/api/live-prices`, `/api/historical`, `/api/predict`, `/api/train`
- Alerts: CRUD + evaluate + history + CSV export
- AI: `/api/ai/chat`, `/api/ai/chat/stream`, `/api/ai/provider-status`
- Profile/settings: `/api/profile`, `/api/settings`

## Secret Management Rules

- Never commit real secrets in `.env.example`.
- `.env.example` should contain placeholders only.
- Real secrets belong in local `.env` or secret manager.

## Testing Guidance

At minimum run:

```bash
pytest -q tests/test_ai_chat_api.py tests/test_resilience_sources.py
```

For broader confidence:

```bash
pytest -q
```

## Change Checklist

1. Keep route contracts unchanged unless intentionally versioned.
2. Update docs when API/behavior changes.
3. Add or update tests for behavior-critical paths.
4. Validate no secret leakage into tracked files.
