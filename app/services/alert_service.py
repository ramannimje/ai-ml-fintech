from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_history import AlertHistory
from app.models.price_alert import PriceAlert
from app.models.user_profile import UserProfile
from app.schemas.responses import (
    AlertCreateRequest,
    AlertEvaluationResponse,
    AlertHistoryResponse,
    AlertUpdateRequest,
    PriceAlertResponse,
)
from app.services.market_quote_service import ALERT_COMMODITY_UNITS
from app.services.email_service import EmailService
from app.services.market_quote_service import MarketQuoteService
from app.services.price_conversion import REGION_CURRENCY


class AlertService:
    def __init__(self) -> None:
        self.market = MarketQuoteService()
        self.email = EmailService()

    async def list_alerts(self, session: AsyncSession, user_sub: str) -> list[PriceAlertResponse]:
        result = await session.execute(
            select(PriceAlert).where(PriceAlert.user_sub == user_sub).order_by(PriceAlert.created_at.desc())
        )
        rows = result.scalars().all()
        return [self._to_alert_response(row) for row in rows]

    async def create_alert(
        self,
        session: AsyncSession,
        user_sub: str,
        user_email: str | None,
        payload: AlertCreateRequest,
    ) -> PriceAlertResponse:
        try:
            quote = self.market.fetch_quote(payload.commodity, payload.region)
            currency = quote.currency
            unit = quote.unit
        except Exception:
            # Alert creation should not fail when live quote providers are temporarily unavailable.
            currency = REGION_CURRENCY[payload.region]
            unit = ALERT_COMMODITY_UNITS[payload.commodity][payload.region]
        profile = await self._profile(session, user_sub)
        default_cooldown = profile.alert_cooldown_minutes if profile else 30
        default_email_enabled = profile.email_notifications_enabled if profile else True
        alert = PriceAlert(
            user_sub=user_sub,
            user_email=user_email,
            commodity=payload.commodity,
            region=payload.region,
            currency=currency,
            unit=unit,
            alert_type=payload.alert_type,
            threshold=payload.threshold,
            enabled=payload.enabled,
            cooldown_minutes=payload.cooldown_minutes or default_cooldown,
            email_notifications_enabled=payload.email_notifications_enabled and default_email_enabled,
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)
        return self._to_alert_response(alert)

    async def update_alert(
        self,
        session: AsyncSession,
        user_sub: str,
        alert_id: int,
        payload: AlertUpdateRequest,
    ) -> PriceAlertResponse:
        result = await session.execute(
            select(PriceAlert).where(PriceAlert.user_sub == user_sub).where(PriceAlert.id == alert_id).limit(1)
        )
        alert = result.scalar_one_or_none()
        if not alert:
            raise ValueError("Alert not found")
        if payload.threshold is not None:
            alert.threshold = payload.threshold
        if payload.enabled is not None:
            alert.enabled = payload.enabled
        if payload.cooldown_minutes is not None:
            alert.cooldown_minutes = payload.cooldown_minutes
        if payload.email_notifications_enabled is not None:
            alert.email_notifications_enabled = payload.email_notifications_enabled
        await session.commit()
        await session.refresh(alert)
        return self._to_alert_response(alert)

    async def delete_alert(self, session: AsyncSession, user_sub: str, alert_id: int) -> None:
        await session.execute(
            delete(PriceAlert).where(PriceAlert.user_sub == user_sub).where(PriceAlert.id == alert_id)
        )
        await session.commit()

    async def alert_history(
        self,
        session: AsyncSession,
        user_sub: str,
        commodity: str | None = None,
        alert_type: str | None = None,
        email_status: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        search: str | None = None,
        limit: int = 200,
    ) -> list[AlertHistoryResponse]:
        stmt = select(AlertHistory).where(AlertHistory.user_sub == user_sub)
        if commodity:
            stmt = stmt.where(AlertHistory.commodity == commodity)
        if alert_type:
            stmt = stmt.where(AlertHistory.alert_type == alert_type)
        if email_status:
            stmt = stmt.where(AlertHistory.email_status == email_status)
        if start_at:
            stmt = stmt.where(AlertHistory.triggered_at >= start_at)
        if end_at:
            stmt = stmt.where(AlertHistory.triggered_at <= end_at)
        if search:
            stmt = stmt.where(AlertHistory.message.ilike(f"%{search.strip()}%"))
        stmt = stmt.order_by(AlertHistory.triggered_at.desc()).limit(min(1000, max(1, limit)))
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_history_response(row) for row in rows]

    async def evaluate_user_alerts(
        self,
        session: AsyncSession,
        user_sub: str,
        user_email: str | None,
    ) -> AlertEvaluationResponse:
        result = await session.execute(
            select(PriceAlert)
            .where(PriceAlert.user_sub == user_sub)
            .where(PriceAlert.enabled.is_(True))
            .order_by(PriceAlert.created_at.desc())
        )
        alerts = result.scalars().all()

        events: list[AlertHistoryResponse] = []
        for alert in alerts:
            try:
                quote = self.market.fetch_quote(alert.commodity, alert.region)
            except Exception:
                # Skip evaluation for this alert when quote provider is unavailable.
                continue
            observed = quote.price if alert.alert_type in {"above", "below"} else quote.daily_change_pct
            should_trigger = self._is_triggered(alert.alert_type, observed, alert.threshold)
            if not should_trigger:
                continue

            # Debounce repeated notifications for 30 minutes per alert.
            cooldown_minutes = max(5, int(alert.cooldown_minutes or 30))
            if alert.last_triggered_at and (datetime.utcnow() - alert.last_triggered_at) < timedelta(minutes=cooldown_minutes):
                continue

            descriptor = (
                f"{alert.commodity.replace('_', ' ').title()} {alert.alert_type.replace('_', ' ')} alert: "
                f"observed {observed:.2f} {'%' if alert.alert_type in {'pct_change_24h', 'spike', 'drop'} else quote.currency} "
                f"vs threshold {alert.threshold:.2f}"
            )
            subject = f"Commodity Alert: {alert.commodity.replace('_', ' ').title()}"
            market_context = f"{alert.region.upper()} market, current {quote.price:.2f} {quote.currency}, daily move {quote.daily_change_pct:.2f}%"
            email_result = await self.email.send_alert(
                user_email or alert.user_email,
                subject,
                descriptor,
                market_context=market_context,
                send_enabled=alert.email_notifications_enabled,
            )

            alert.last_triggered_at = datetime.now(timezone.utc).replace(tzinfo=None)
            event = AlertHistory(
                alert_id=alert.id,
                user_sub=user_sub,
                commodity=alert.commodity,
                region=alert.region,
                currency=quote.currency,
                alert_type=alert.alert_type,
                threshold=alert.threshold,
                observed_value=observed,
                message=descriptor,
                email_status=email_result.status,
                delivery_provider=email_result.provider,
                delivery_error=email_result.error,
                delivery_attempts=email_result.attempts,
            )
            session.add(event)
            await session.flush()
            events.append(self._to_history_response(event))

        await session.commit()
        return AlertEvaluationResponse(checked=len(alerts), triggered=len(events), events=events)

    def _is_triggered(self, alert_type: str, observed: float, threshold: float) -> bool:
        if alert_type == "above":
            return observed > threshold
        if alert_type == "below":
            return observed < threshold
        if alert_type == "pct_change_24h":
            return abs(observed) >= threshold
        if alert_type == "spike":
            return observed >= threshold
        if alert_type == "drop":
            return observed <= -abs(threshold)
        return False

    def _to_alert_response(self, row: PriceAlert) -> PriceAlertResponse:
        return PriceAlertResponse(
            id=row.id,
            commodity=row.commodity,
            region=row.region,
            currency=row.currency,
            unit=row.unit,
            alert_type=row.alert_type,
            threshold=row.threshold,
            enabled=row.enabled,
            cooldown_minutes=row.cooldown_minutes,
            email_notifications_enabled=row.email_notifications_enabled,
            last_triggered_at=row.last_triggered_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_history_response(self, row: AlertHistory) -> AlertHistoryResponse:
        return AlertHistoryResponse(
            id=row.id,
            alert_id=row.alert_id,
            commodity=row.commodity,
            region=row.region,
            currency=row.currency,
            alert_type=row.alert_type,
            threshold=row.threshold,
            observed_value=row.observed_value,
            message=row.message,
            email_status=row.email_status,
            delivery_provider=row.delivery_provider,
            delivery_error=row.delivery_error,
            delivery_attempts=row.delivery_attempts,
            triggered_at=row.triggered_at,
        )

    async def _profile(self, session: AsyncSession, user_sub: str) -> UserProfile | None:
        result = await session.execute(select(UserProfile).where(UserProfile.user_sub == user_sub).limit(1))
        return result.scalar_one_or_none()
