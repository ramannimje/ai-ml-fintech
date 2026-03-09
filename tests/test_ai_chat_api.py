from datetime import datetime, timezone

from fastapi.testclient import TestClient
import httpx

from app.main import app
from app.schemas.responses import AIChatResponse, UserProfileResponse
from app.api import routes_ai_chat
from app.services.ai_chat_service import AIProviderUnavailableError
from app.services.ai_reasoning_engine import QueryContext

client = TestClient(app)


def test_ai_chat_response(monkeypatch) -> None:
    async def _mock_profile(
        session,
        user_sub: str,
        user_email: str | None,
        user_name: str | None,
        picture_url: str | None,
        user_context=None,
    ):
        _ = session, user_email, user_name, picture_url, user_context
        return UserProfileResponse(
            user_sub=user_sub,
            email="test@example.com",
            name="Test User",
            picture_url=None,
            preferred_region="us",
            email_notifications_enabled=True,
            alert_cooldown_minutes=30,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _mock_allow(key: str, limit: int, window_seconds: int) -> bool:
        _ = key, limit, window_seconds
        return True

    async def _mock_ask(session, user_id: str, message: str, preferred_region: str):
        _ = session, user_id, message, preferred_region
        return AIChatResponse(
            answer="Gold is trending higher based on recent data.",
            intent="market_summary",
            region="us",
            commodity="gold",
            horizon_days=30,
            generated_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(routes_ai_chat.profile_service, "get_or_create", _mock_profile)
    monkeypatch.setattr(routes_ai_chat.limiter, "allow", _mock_allow)
    monkeypatch.setattr(routes_ai_chat.chat_service, "ask", _mock_ask)

    response = client.post("/api/ai/chat", json={"message": "Why is gold up today?"})
    assert response.status_code == 200
    payload = response.json()
    assert "Gold is trending higher" in payload["answer"]
    assert payload["commodity"] == "gold"


def test_ai_chat_rate_limited(monkeypatch) -> None:
    async def _mock_allow(key: str, limit: int, window_seconds: int) -> bool:
        _ = key, limit, window_seconds
        return False

    monkeypatch.setattr(routes_ai_chat.limiter, "allow", _mock_allow)

    response = client.post("/api/ai/chat", json={"message": "forecast silver"})
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()


def test_ai_chat_stream(monkeypatch) -> None:
    async def _mock_profile(
        session,
        user_sub: str,
        user_email: str | None,
        user_name: str | None,
        picture_url: str | None,
        user_context=None,
    ):
        _ = session, user_email, user_name, picture_url, user_context
        return UserProfileResponse(
            user_sub=user_sub,
            email="test@example.com",
            name="Test User",
            picture_url=None,
            preferred_region="us",
            email_notifications_enabled=True,
            alert_cooldown_minutes=30,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _mock_allow(key: str, limit: int, window_seconds: int) -> bool:
        _ = key, limit, window_seconds
        return True

    async def _mock_ask(session, user_id: str, message: str, preferred_region: str):
        _ = session, user_id, message, preferred_region
        return AIChatResponse(
            answer="Silver outlook is moderately bullish.",
            intent="market_summary",
            region="us",
            commodity="silver",
            horizon_days=30,
            generated_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(routes_ai_chat.profile_service, "get_or_create", _mock_profile)
    monkeypatch.setattr(routes_ai_chat.limiter, "allow", _mock_allow)
    monkeypatch.setattr(routes_ai_chat.chat_service, "ask", _mock_ask)

    response = client.post("/api/ai/chat/stream", json={"message": "how about silver"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: token" in response.text
    assert "event: done" in response.text


def test_ai_provider_status(monkeypatch) -> None:
    def _mock_provider_status():
        return {
            "provider": "openrouter",
            "openrouter_model": "qwen/qwen3-next-80b-a3b-instruct",
            "openrouter_api_key_present": True,
            "openrouter_cooldown_seconds_remaining": 0,
            "last_openrouter_error": None,
        }

    monkeypatch.setattr(routes_ai_chat.chat_service, "provider_status", _mock_provider_status)

    response = client.get("/api/ai/provider-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "openrouter"
    assert payload["openrouter_model"] == "qwen/qwen3-next-80b-a3b-instruct"


def test_ai_chat_returns_503_when_provider_unavailable(monkeypatch) -> None:
    async def _mock_profile(
        session,
        user_sub: str,
        user_email: str | None,
        user_name: str | None,
        picture_url: str | None,
        user_context=None,
    ):
        _ = session, user_email, user_name, picture_url, user_context
        return UserProfileResponse(
            user_sub=user_sub,
            email="test@example.com",
            name="Test User",
            picture_url=None,
            preferred_region="us",
            email_notifications_enabled=True,
            alert_cooldown_minutes=30,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _mock_allow(key: str, limit: int, window_seconds: int) -> bool:
        _ = key, limit, window_seconds
        return True

    async def _mock_ask(session, user_id: str, message: str, preferred_region: str):
        _ = session, user_id, message, preferred_region
        raise AIProviderUnavailableError("OPENROUTER_API_KEY is missing")

    monkeypatch.setattr(routes_ai_chat.profile_service, "get_or_create", _mock_profile)
    monkeypatch.setattr(routes_ai_chat.limiter, "allow", _mock_allow)
    monkeypatch.setattr(routes_ai_chat.chat_service, "ask", _mock_ask)

    response = client.post("/api/ai/chat", json={"message": "predict the gold price in 2026 end"})
    assert response.status_code == 503
    assert "AI provider unavailable" in response.json()["detail"]


def test_ai_chat_end_to_end_uses_openrouter_model(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def _mock_profile(
        session,
        user_sub: str,
        user_email: str | None,
        user_name: str | None,
        picture_url: str | None,
        user_context=None,
    ):
        _ = session, user_email, user_name, picture_url, user_context
        return UserProfileResponse(
            user_sub=user_sub,
            email="test@example.com",
            name="Test User",
            picture_url=None,
            preferred_region="us",
            email_notifications_enabled=True,
            alert_cooldown_minutes=30,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _mock_allow(key: str, limit: int, window_seconds: int) -> bool:
        _ = key, limit, window_seconds
        return True

    class _OpenRouterClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers or {}
            captured["json"] = json or {}
            return httpx.Response(
                status_code=200,
                request=httpx.Request("POST", str(url)),
                json={"choices": [{"message": {"content": "OpenRouter response for test."}}]},
            )

    async def _build_context(session, user_id: str, message: str, preferred_region: str):
        _ = session, user_id, message, preferred_region
        return QueryContext(
            message="how is gold now",
            intent="market_summary",
            commodity="gold",
            comparison_commodity=None,
            region="us",
            comparison_region=None,
            horizon_days=30,
            target_date=None,
            is_long_term=False,
            concise=False,
        )

    async def _build_data_context(session, query):
        _ = session, query
        return {
            "current_price": {"price": 3300.0, "currency": "USD", "unit": "oz"},
            "historical_trend": {
                "change_pct": 1.2,
                "volatility_pct": 1.1,
                "signal_text": "moderately bullish",
                "direction": "bullish",
                "volatility_label": "moderate",
            },
            "regional_market_signal": "Gold leads upside momentum (+1.20%)",
        }

    monkeypatch.setattr(routes_ai_chat.profile_service, "get_or_create", _mock_profile)
    monkeypatch.setattr(routes_ai_chat.limiter, "allow", _mock_allow)
    monkeypatch.setattr("app.services.ai_chat_service.httpx.AsyncClient", lambda *args, **kwargs: _OpenRouterClient())
    monkeypatch.setattr(routes_ai_chat.chat_service, "_openrouter_api_key", lambda: "test-openrouter-key")
    monkeypatch.setattr(routes_ai_chat.chat_service.engine, "build_context", _build_context)
    monkeypatch.setattr(routes_ai_chat.chat_service.engine, "build_data_context", _build_data_context)

    response = client.post("/api/ai/chat", json={"message": "how is gold now"})
    assert response.status_code == 200
    assert "OpenRouter response" in response.json()["answer"]

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    body = captured["json"]
    assert body["model"] == "qwen/qwen3-next-80b-a3b-instruct"
    assert isinstance(body["messages"], list) and len(body["messages"]) == 2
    assert "temperature" in body
    assert "max_tokens" in body
