from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.alert_history import AlertHistory
from app.models.price_alert import PriceAlert
from app.services.market_quote_service import MarketQuoteService
from app.services.rate_limiter import RedisRateLimiter
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)

REGION_SYMBOL = {"india": "₹", "us": "$", "europe": "€"}
UNIT_ALIAS = {"10g_24k": "10g", "exchange_standard": "unit"}


def _format_indian_number(value: float) -> str:
    s = f"{value:,.0f}"
    parts = s.split(".")
    head = parts[0].replace(",", "")
    if len(head) <= 3:
        return head
    lead = head[:-3]
    tail = head[-3:]
    grouped = []
    while len(lead) > 2:
        grouped.append(lead[-2:])
        lead = lead[:-2]
    if lead:
        grouped.append(lead)
    return ",".join(reversed(grouped)) + "," + tail


def _format_price(region: str, price: float, unit: str) -> str:
    symbol = REGION_SYMBOL.get(region, "$")
    out_unit = UNIT_ALIAS.get(unit, unit)
    if region == "india":
        return f"{symbol}{_format_indian_number(price)}/{out_unit}"
    return f"{symbol}{price:,.2f}/{out_unit}"


def _is_breach(direction: str, live_price: float, target_price: float) -> bool:
    if direction == "above":
        return live_price >= target_price
    return live_price <= target_price


class WhatsAppAlertWorker:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self.market = MarketQuoteService()
        self.whatsapp = WhatsAppService()
        self.rate_limiter = RedisRateLimiter()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="whatsapp-alert-worker")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        settings = get_settings()
        interval = max(5, int(settings.whatsapp_alert_poll_interval_seconds))
        while True:
            try:
                await self.process_pending_alerts()
            except Exception as exc:
                logger.exception("whatsapp_alert_worker_iteration_failed error=%s", exc)
            await asyncio.sleep(interval)

    async def process_pending_alerts(self) -> int:
        settings = get_settings()
        processed = 0
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PriceAlert)
                .where(PriceAlert.is_active.is_(True))
                .where(PriceAlert.is_triggered.is_(False))
                .where(PriceAlert.whatsapp_number.is_not(None))
                .where(PriceAlert.direction.in_(("above", "below")))
                .order_by(PriceAlert.created_at.asc())
            )
            alerts = result.scalars().all()
            for alert in alerts:
                try:
                    quote = await asyncio.to_thread(self.market.fetch_quote, alert.commodity, alert.region)
                except Exception as exc:
                    logger.warning("whatsapp_alert_quote_failed alert_id=%s error=%s", alert.id, exc)
                    continue

                target_price = float(alert.target_price or alert.threshold)
                if not alert.direction or not _is_breach(alert.direction, quote.price, target_price):
                    continue

                limiter_key = f"whatsapp:alerts:{alert.user_id or alert.user_sub}:{alert.whatsapp_number}"
                allowed = await self.rate_limiter.allow(
                    key=limiter_key,
                    limit=max(1, int(settings.whatsapp_rate_limit_max_messages)),
                    window_seconds=max(60, int(settings.whatsapp_rate_limit_window_seconds)),
                )
                if not allowed:
                    logger.info("whatsapp_alert_rate_limited alert_id=%s", alert.id)
                    continue

                live = _format_price(alert.region, quote.price, quote.unit)
                target = _format_price(alert.region, target_price, quote.unit)
                message = (
                    f"🚨 {alert.commodity.replace('_', ' ').title()} Alert:\n"
                    f"{live}\n"
                    f"Your target of {target} was hit."
                )
                delivery = await self.whatsapp.send_alert(alert.whatsapp_number, message)
                if delivery.status == "sent":
                    now = datetime.now(timezone.utc).replace(tzinfo=None)
                    alert.is_triggered = True
                    alert.is_active = False
                    alert.enabled = False
                    alert.last_triggered_at = now
                    alert.triggered_at = now
                    session.add(
                        AlertHistory(
                            alert_id=alert.id,
                            user_sub=alert.user_sub,
                            commodity=alert.commodity,
                            region=alert.region,
                            currency=quote.currency,
                            alert_type=alert.direction,
                            threshold=target_price,
                            observed_value=quote.price,
                            message=message,
                            email_status="sent",
                            delivery_provider=delivery.provider or settings.whatsapp_provider,
                            delivery_error=None,
                            delivery_attempts=max(1, delivery.attempts),
                        )
                    )
                    processed += 1
                else:
                    logger.warning(
                        "whatsapp_alert_send_failed alert_id=%s status=%s provider=%s error=%s",
                        alert.id,
                        delivery.status,
                        delivery.provider,
                        delivery.error,
                    )

            await session.commit()
        return processed


whatsapp_alert_worker = WhatsAppAlertWorker()
