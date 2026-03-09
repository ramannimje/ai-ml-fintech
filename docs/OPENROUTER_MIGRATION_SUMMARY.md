# OpenRouter Migration Summary

## Overview
This repository was migrated from mixed AI providers (Gemini/OpenAI/Ollama abstraction) to an OpenRouter-first LLM integration using:

- Endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Model: `qwen/qwen3-next-80b-a3b-instruct`
- Auth env var: `OPENROUTER_API_KEY`

The migration preserved existing prompt-construction logic while replacing transport/auth/model wiring and updating config, API status schema, tests, and docs.

## Core Backend Changes

### 1. AI Chat Service Refactor
**File:** `app/services/ai_chat_service.py`

- Removed Gemini/OpenAI request paths and unified LLM execution under OpenRouter.
- Added OpenRouter auth retrieval via `OPENROUTER_API_KEY`.
- Implemented OpenRouter request payload in OpenAI-compatible schema:
  - `model`
  - `messages`
  - `temperature`
  - `max_tokens`
- Preserved advisory and refinement prompt builders.
- Added robust error handling:
  - Missing API key handling
  - HTTP error handling
  - 429 rate-limit cooldown handling (`retry-after`)
  - request exception handling
- Updated provider status reporting to OpenRouter fields only.

### 2. Configuration Updates
**File:** `app/core/config.py`

- Removed Gemini/OpenAI settings and added OpenRouter settings:
  - `openrouter_api_key`
  - `openrouter_chat_model` (default: `qwen/qwen3-next-80b-a3b-instruct`)
  - `openrouter_base_url` (default OpenRouter chat completions URL)
- Set default provider to `openrouter`.
- Updated Infisical secret hydration to use `OPENROUTER_API_KEY`.

### 3. Provider Status Schema Update
**File:** `app/schemas/responses.py`

- Replaced old multi-provider status model fields with OpenRouter-only fields:
  - `provider: Literal["openrouter", "disabled"]`
  - `openrouter_model`
  - `openrouter_api_key_present`
  - `openrouter_cooldown_seconds_remaining`
  - `last_openrouter_error`

### 4. API Error Message Generalization
**File:** `app/api/routes_ai_chat.py`

- Updated 503 detail from provider-specific wording to generic:
  - `AI provider unavailable: ...`

### 5. Vault Secret Namespace Mapping
**File:** `app/services/vault_service.py`

- Updated AI path key mapping to include `OPENROUTER_API_KEY` and remove Gemini/OpenAI API key entries.

## Vector/RAG Support Adjustments

### 6. Removed Gemini Embedding SDK Dependency in Vector Service
**File:** `app/services/vector_service.py`

- Removed Google GenAI SDK usage.
- Implemented deterministic local text embeddings for retrieval support (hashing-based fallback embedding).
- Retained pgvector-based similarity query usage when pgvector is available.

### 7. Dependency Cleanup
**File:** `backend/requirements.txt`

- Removed `google-genai` dependency.
- Kept relevant existing dependencies used by tests/runtime.

## Environment and Docs Updates

### 8. Environment Template Update
**File:** `.env.example`

- Added/updated:
  - `OPENROUTER_API_KEY=`
  - `AI_CHAT_PROVIDER=openrouter`
  - `OPENROUTER_CHAT_MODEL=qwen/qwen3-next-80b-a3b-instruct`
  - `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1/chat/completions`
- Removed Gemini/OpenAI AI-chat env variables from template.

### 9. README Update
**File:** `README.md`

- Updated AI chat documentation to OpenRouter + Qwen model.
- Updated secret namespace description to include `OPENROUTER_API_KEY`.

### 10. Platform Notes Update
**File:** `docs/PLATFORM.md`

- Updated architecture and AI advisory behavior to OpenRouter model path.
- Removed Gemini-specific behavior notes.

## Test Suite Updates

### 11. API Tests
**File:** `tests/test_ai_chat_api.py`

- Updated provider-status expectations to OpenRouter fields.
- Updated unavailable-provider error assertions.
- Added end-to-end test:
  - `test_ai_chat_end_to_end_uses_openrouter_model`
  - Verifies outbound request uses:
    - URL `https://openrouter.ai/api/v1/chat/completions`
    - model `qwen/qwen3-next-80b-a3b-instruct`
    - `messages`, `temperature`, `max_tokens`

### 12. Resilience Tests
**File:** `tests/test_resilience_sources.py`

- Replaced Gemini/OpenAI-specific tests with OpenRouter-focused tests:
  - cooldown parser
  - response extraction
  - refine path success
  - advisory fallback behavior on provider failure

### 13. Vault Tests
**File:** `tests/test_vault_service.py`

- Updated expected key from `OPENAI_API_KEY` to `OPENROUTER_API_KEY`.

### 14. Vector Engine Tests
**File:** `tests/test_vector_engine.py`

- Updated fixture assumptions to align with refactored vector service behavior.

## Validation Results

### Targeted End-to-End AI Route Check
Executed:

```bash
pytest -q tests/test_ai_chat_api.py::test_ai_chat_end_to_end_uses_openrouter_model
```

Result:
- `1 passed`
- Validates route-level OpenRouter integration and payload schema.

### Full Updated Relevant Suite
Executed:

```bash
pytest -q tests/test_ai_chat_api.py tests/test_resilience_sources.py tests/test_vault_service.py tests/test_vector_engine.py tests/test_ai_chat_service.py
```

Result:
- `24 passed, 2 skipped`

## Notes

- Prompt construction logic for advisory/refinement was preserved; only provider transport/auth/model integration was changed.
- Provider status API response shape changed; consumers expecting old Gemini/OpenAI fields must use new OpenRouter fields.
