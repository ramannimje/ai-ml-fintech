from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.responses import (
    AlertEvaluationResponse,
    AlertHistoryResponse,
    PriceAlertResponse,
    UserProfileResponse,
)
from app.api import routes

client = TestClient(app)


def test_profile_get_and_update(monkeypatch) -> None:
    async def _mock_get_or_create(
        session,
        user_sub: str,
        user_email: str | None,
        user_name: str | None,
        picture_url: str | None,
        user_context=None,
    ):
        _ = session, picture_url, user_context
        return UserProfileResponse(
            user_sub=user_sub,
            email=user_email,
            name=user_name,
            picture_url=None,
            preferred_region="us",
            email_notifications_enabled=True,
            alert_cooldown_minutes=30,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _mock_update(session, user_sub: str, payload, user_email: str | None):
        _ = session
        return UserProfileResponse(
            user_sub=user_sub,
            email=user_email,
            name="Updated User",
            picture_url=None,
            preferred_region=payload.preferred_region or "us",
            email_notifications_enabled=True,
            alert_cooldown_minutes=payload.alert_cooldown_minutes or 30,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(routes.profile_service, "get_or_create", _mock_get_or_create)
    monkeypatch.setattr(routes.profile_service, "update", _mock_update)

    get_res = client.get("/api/profile")
    assert get_res.status_code == 200
    assert get_res.json()["preferred_region"] == "us"

    put_res = client.put("/api/profile", json={"preferred_region": "india", "alert_cooldown_minutes": 45})
    assert put_res.status_code == 200
    assert put_res.json()["preferred_region"] == "india"
    assert put_res.json()["alert_cooldown_minutes"] == 45


def test_alert_patch_and_history_export(monkeypatch) -> None:
    async def _mock_patch(session, user_sub: str, alert_id: int, payload):
        _ = session, payload
        return PriceAlertResponse(
            id=alert_id,
            commodity="gold",
            region="us",
            currency="USD",
            unit="oz",
            alert_type="above",
            threshold=2000.0,
            enabled=False,
            cooldown_minutes=30,
            email_notifications_enabled=True,
            last_triggered_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _mock_history(session, user_sub: str, **kwargs):
        _ = session, user_sub, kwargs
        return [
            AlertHistoryResponse(
                id=1,
                alert_id=2,
                commodity="gold",
                region="us",
                currency="USD",
                alert_type="above",
                threshold=2000.0,
                observed_value=2100.0,
                message="Gold above alert triggered",
                email_status="sent",
                delivery_provider="resend",
                delivery_error=None,
                delivery_attempts=1,
                triggered_at=datetime.now(timezone.utc),
            )
        ]

    async def _mock_eval(session, user_sub: str, user_email: str | None):
        _ = session, user_sub, user_email
        return AlertEvaluationResponse(checked=1, triggered=0, events=[])

    monkeypatch.setattr(routes.alert_service, "update_alert", _mock_patch)
    monkeypatch.setattr(routes.alert_service, "alert_history", _mock_history)
    monkeypatch.setattr(routes.alert_service, "evaluate_user_alerts", _mock_eval)

    patch_res = client.patch("/api/alerts/99", json={"enabled": False})
    assert patch_res.status_code == 200
    assert patch_res.json()["enabled"] is False

    export_res = client.get("/api/alerts/history/export")
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers["content-type"]
    assert "Gold above alert triggered" in export_res.text


def test_create_alert_survives_quote_provider_failure(monkeypatch) -> None:
    def _boom(*args, **kwargs):
        _ = args, kwargs
        raise RuntimeError("provider-down")

    monkeypatch.setattr(routes.alert_service.market, "fetch_quote", _boom)
    response = client.post(
        "/api/alerts",
        json={
            "commodity": "gold",
            "region": "india",
            "alert_type": "above",
            "threshold": 1.0,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["currency"] == "INR"
