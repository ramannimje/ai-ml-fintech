from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from app.services.ai_chat_service import AIChatService
from app.services.commodity_service import CommodityService


class _FailingAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, _url):
        raise RuntimeError("tlsv1 unrecognized name")


def test_metals_live_failure_enters_cooldown(monkeypatch) -> None:
    service = CommodityService()
    service._metals_live_cooldown_until = None
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: _FailingAsyncClient())

    out = asyncio.run(service._fetch_metals_live_rates())
    assert out == {}
    assert service._metals_live_cooldown_until is not None
    assert service._metals_live_last_error is not None


def test_metals_live_cooldown_skips_remote_call(monkeypatch) -> None:
    service = CommodityService()
    service._metals_live_cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=5)
    called = {"value": False}

    class _ShouldNotBeCalled:
        async def __aenter__(self):
            called["value"] = True
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, _url):
            called["value"] = True
            return None

    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: _ShouldNotBeCalled())
    out = asyncio.run(service._fetch_metals_live_rates())
    assert out == {}
    assert called["value"] is False


def test_openrouter_retry_after_cooldown_parser() -> None:
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    response = httpx.Response(status_code=429, request=request, headers={"retry-after": "180"})
    assert AIChatService._cooldown_from_rate_limit(response, default_seconds=300) == 180


def test_extract_openrouter_text() -> None:
    payload = {"choices": [{"message": {"content": "hello"}}]}
    assert AIChatService._extract_openrouter_text(payload) == "hello"


def test_openrouter_refine_success(monkeypatch) -> None:
    service = AIChatService()
    monkeypatch.setattr(service, "_openrouter_api_key", lambda: "test-key")

    class _OpenRouterClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, _url, headers=None, json=None):
            _ = headers, json
            return httpx.Response(
                status_code=200,
                request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
                json={"choices": [{"message": {"content": "Gold is expected to stay firm."}}]},
            )

    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: _OpenRouterClient())

    out = asyncio.run(
        service._openrouter_refine(
            query_context={"message": "what is the gold price in 2026 end?"},
            data_context={},
            fallback_answer="fallback",
        )
    )
    assert "Gold is expected" in out


def test_openrouter_advisory_returns_engine_fallback_on_failure(monkeypatch) -> None:
    service = AIChatService()

    async def _fake_openrouter_generate_content(system_prompt, prompt, temperature, max_tokens):
        _ = system_prompt, prompt, temperature, max_tokens
        return ""

    monkeypatch.setattr(service, "_openrouter_generate_content", _fake_openrouter_generate_content)
    service._openrouter_last_error = "timeout"

    out = asyncio.run(
        service._openrouter_advisory_answer(
            session=None,  # type: ignore[arg-type]
            question="Should I invest in silver now?",
            query_context={"commodity": "silver"},
            data_context={
                "current_price": {"price": 100.0, "currency": "USD", "unit": "oz"},
                "historical_trend": {"signal_text": "bullish", "volatility_pct": 3.5, "change_pct": 8.2},
                "regional_market_signal": "Silver leads",
            },
            fallback_answer="fallback-outlook",
        )
    )
    assert out == "fallback-outlook"
