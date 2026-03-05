from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.services.ai_chat_service import AIChatService, AIProviderUnavailableError
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


def test_openai_retry_after_cooldown_parser() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code=429, request=request, headers={"retry-after": "180"})
    assert AIChatService._cooldown_from_rate_limit(response, default_seconds=300) == 180


def test_gemini_model_not_found_detection() -> None:
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent")
    response = httpx.Response(
        status_code=404,
        request=request,
        json={"error": {"message": "models/gemini-1.5-flash is not found for API version v1beta"}},
    )
    assert AIChatService._is_gemini_model_not_found(response) is True


def test_select_gemini_candidates_filters_unavailable_models() -> None:
    service = AIChatService()
    service.settings.gemini_model = "gemini-1.5-pro"
    service.settings.gemini_fallback_models = "gemini-1.5-flash"
    available = ["gemini-2.0-flash", "gemini-2.5-flash"]
    out = service._select_gemini_candidates(available)
    assert out[0] in {"gemini-2.5-flash", "gemini-2.0-flash"}
    assert "gemini-1.5-pro" not in out
    assert "gemini-1.5-flash" not in out


def test_gemini_refine_success_with_api_question(monkeypatch) -> None:
    service = AIChatService()
    service.settings.gemini_model = "gemini-1.5-pro"
    service.settings.gemini_fallback_models = "gemini-1.5-flash"
    monkeypatch.setattr(service, "_gemini_api_key", lambda: "test-key")

    async def _available_models(use_cache=True):
        _ = use_cache
        return ["gemini-2.0-flash"]

    class _GeminiClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, _url, headers=None, json=None):
            _ = headers, json
            return httpx.Response(
                status_code=200,
                request=httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"),
                json={"candidates": [{"content": {"parts": [{"text": "Gold is expected to trade near 171000 INR by end-2026."}]}}]},
            )

    monkeypatch.setattr(service, "_get_gemini_available_models", _available_models)
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: _GeminiClient())

    out = asyncio.run(
        service._gemini_refine(
            query_context={"message": "what is the gold price in 2026 end?"},
            data_context={},
            fallback_answer="fallback",
        )
    )
    assert "Gold is expected" in out


def test_gemini_provider_is_strict_no_fallback(monkeypatch) -> None:
    service = AIChatService()
    service.settings.ai_chat_provider = "gemini"

    async def _fake_gemini_refine(query_context, data_context, fallback_answer):
        _ = query_context, data_context
        return fallback_answer

    monkeypatch.setattr(service, "_gemini_refine", _fake_gemini_refine)

    with pytest.raises(AIProviderUnavailableError):
        asyncio.run(
            service._maybe_llm_refine(
                query_context={"message": "predict the gold price in 2026 end"},
                data_context={},
                fallback_answer="fallback",
            )
        )


def test_gemini_trading_outlook_does_not_append_template_sections(monkeypatch) -> None:
    service = AIChatService()
    service.settings.ai_chat_provider = "gemini"

    async def _fake_gemini_refine(query_context, data_context, fallback_answer):
        _ = query_context, data_context, fallback_answer
        return "Current Market\nSilver is strong.\n\nTrend Analysis\nBullish momentum."

    monkeypatch.setattr(service, "_gemini_refine", _fake_gemini_refine)

    out = asyncio.run(
        service._maybe_llm_refine(
            query_context={"intent": "trading_outlook", "message": "shall I invest in silver now?"},
            data_context={},
            fallback_answer=(
                "Current Market\nSilver snapshot.\n\nTrend Analysis\nTrend text.\n\n"
                "Investment View\nBias: Buy-on-dips. Confidence: medium.\n\nMarket Signal\nBullish."
            ),
        )
    )
    assert out == "Current Market\nSilver is strong.\n\nTrend Analysis\nBullish momentum."


def test_gemini_advisory_returns_fixed_message_on_failure(monkeypatch) -> None:
    service = AIChatService()

    async def _fake_gemini_generate_content(system_prompt, prompt, use_model_cache):
        _ = system_prompt, prompt, use_model_cache
        return ""

    monkeypatch.setattr(service, "_gemini_generate_content", _fake_gemini_generate_content)
    service._gemini_last_error = "timeout"

    out = asyncio.run(
        service._gemini_advisory_answer(
            question="Should I invest in silver now?",
            query_context={"commodity": "silver"},
            data_context={
                "current_price": {"price": 100.0, "currency": "USD", "unit": "oz"},
                "historical_trend": {"signal_text": "bullish", "volatility_pct": 3.5, "change_pct": 8.2},
                "regional_market_signal": "Silver leads",
            },
        )
    )
    assert out == "We are unable to generate an advisory response at the moment. Please try again."
