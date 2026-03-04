from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.responses import AIChatResponse, UserProfileResponse
from app.api import routes_ai_chat

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
            "provider": "gemini",
            "openai_model": "gpt-5.2",
            "openai_fallback_models": ["gpt-5", "gpt-4.1"],
            "openai_api_key_present": True,
            "openai_cooldown_seconds_remaining": 0,
            "last_openai_error": None,
            "gemini_model": "gemini-1.5-pro",
            "gemini_fallback_models": ["gemini-1.5-flash"],
            "gemini_api_key_present": True,
            "gemini_cooldown_seconds_remaining": 0,
            "last_gemini_error": None,
        }

    monkeypatch.setattr(routes_ai_chat.chat_service, "provider_status", _mock_provider_status)

    response = client.get("/api/ai/provider-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "gemini"
    assert payload["openai_model"] == "gpt-5.2"
    assert payload["gemini_model"] == "gemini-1.5-pro"
