import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.alert_history import AlertHistory
from app.models.price_alert import PriceAlert
from app.services.alert_service import AlertService
from app.services.market_quote_service import MarketQuote
from app.services.whatsapp_service import WhatsAppDeliveryResult
from app.workers.whatsapp_alert_worker import WhatsAppAlertWorker
from app.workers import whatsapp_alert_worker as worker_module


def _mk_quote(price: float, commodity: str = "gold", region: str = "india") -> MarketQuote:
    return MarketQuote(
        commodity=commodity,
        region=region,
        currency="INR" if region == "india" else "USD",
        unit="10g_24k" if region == "india" else "oz",
        price=price,
        daily_change_pct=1.2,
        timestamp=datetime.now(timezone.utc),
        source="unit-test",
    )


def test_email_alert_evaluation_sends_message(monkeypatch) -> None:
    async def _run() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        try:
            async with Session() as session:
                session.add(
                    PriceAlert(
                        user_sub="u1",
                        user_id="u1",
                        user_email="u1@example.com",
                        commodity="gold",
                        region="india",
                        currency="INR",
                        unit="10g_24k",
                        alert_type="above",
                        direction="above",
                        threshold=175000.0,
                        target_price=175000.0,
                        enabled=True,
                        is_active=True,
                        email_notifications_enabled=True,
                    )
                )
                await session.commit()

                service = AlertService()
                monkeypatch.setattr(service.market, "fetch_quote", lambda commodity, region: _mk_quote(175200.0, commodity, region))

                sent_calls: list[dict[str, str]] = []

                async def _fake_send(to_email, subject, message, market_context="", send_enabled=True):
                    _ = market_context, send_enabled
                    sent_calls.append({"to_email": to_email, "subject": subject, "message": message})
                    return type(
                        "EmailResult",
                        (),
                        {"status": "sent", "provider": "test", "error": None, "attempts": 1},
                    )()

                monkeypatch.setattr(service.email, "send_alert", _fake_send)

                outcome = await service.evaluate_user_alerts(session=session, user_sub="u1", user_email="u1@example.com")
                assert outcome.checked == 1
                assert outcome.triggered == 1
                assert len(sent_calls) == 1
                assert sent_calls[0]["to_email"] == "u1@example.com"
                assert "Commodity Alert" in sent_calls[0]["subject"]

                history_rows = (await session.execute(select(AlertHistory))).scalars().all()
                assert len(history_rows) == 1
                assert history_rows[0].email_status == "sent"
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_whatsapp_worker_sends_once_and_marks_triggered(monkeypatch) -> None:
    async def _run() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Worker uses module-level AsyncSessionLocal; redirect it to this test DB.
        monkeypatch.setattr(worker_module, "AsyncSessionLocal", Session)

        try:
            async with Session() as session:
                session.add(
                    PriceAlert(
                        user_sub="u2",
                        user_id="u2",
                        commodity="gold",
                        region="india",
                        currency="INR",
                        unit="10g_24k",
                        alert_type="above",
                        direction="above",
                        threshold=175000.0,
                        target_price=175000.0,
                        enabled=True,
                        is_active=True,
                        is_triggered=False,
                        email_notifications_enabled=False,
                        whatsapp_number="+919999999999",
                    )
                )
                await session.commit()

            worker = WhatsAppAlertWorker()
            monkeypatch.setattr(worker.market, "fetch_quote", lambda commodity, region: _mk_quote(175220.0, commodity, region))

            sent_messages: list[dict[str, str]] = []

            async def _fake_whatsapp_send(to_number, message):
                sent_messages.append({"to": to_number, "message": message})
                return WhatsAppDeliveryResult(status="sent", provider="twilio", attempts=1)

            async def _allow_all(key, limit, window_seconds):
                _ = key, limit, window_seconds
                return True

            monkeypatch.setattr(worker.whatsapp, "send_alert", _fake_whatsapp_send)
            monkeypatch.setattr(worker.rate_limiter, "allow", _allow_all)

            processed_first = await worker.process_pending_alerts()
            processed_second = await worker.process_pending_alerts()

            assert processed_first == 1
            assert processed_second == 0
            assert len(sent_messages) == 1
            assert "Gold Alert" in sent_messages[0]["message"]
            assert "Your target of" in sent_messages[0]["message"]

            async with Session() as session:
                alert = (await session.execute(select(PriceAlert))).scalars().one()
                assert alert.is_triggered is True
                assert alert.is_active is False

                history_rows = (await session.execute(select(AlertHistory))).scalars().all()
                assert len(history_rows) == 1
                assert history_rows[0].delivery_provider == "twilio"
                assert history_rows[0].email_status == "sent"
        finally:
            await engine.dispose()

    asyncio.run(_run())
