from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_history import AlertHistory
from app.models.price_alert import PriceAlert
from app.schemas.responses import AlertCreateRequest, AlertEvaluationResponse, AlertHistoryResponse, PriceAlertResponse
from app.services.email_service import EmailService
from app.services.market_quote_service import MarketQuoteService


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
        quote = self.market.fetch_quote(payload.commodity, payload.region)
        alert = PriceAlert(
            user_sub=user_sub,
            user_email=user_email,
            commodity=payload.commodity,
            region=payload.region,
            currency=quote.currency,
            unit=quote.unit,
            alert_type=payload.alert_type,
            threshold=payload.threshold,
            enabled=True,
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)
        return self._to_alert_response(alert)

    async def delete_alert(self, session: AsyncSession, user_sub: str, alert_id: int) -> None:
        await session.execute(
            delete(PriceAlert).where(PriceAlert.user_sub == user_sub).where(PriceAlert.id == alert_id)
        )
        await session.commit()

    async def alert_history(self, session: AsyncSession, user_sub: str) -> list[AlertHistoryResponse]:
        result = await session.execute(
            select(AlertHistory)
            .where(AlertHistory.user_sub == user_sub)
            .order_by(AlertHistory.triggered_at.desc())
            .limit(200)
        )
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
            quote = self.market.fetch_quote(alert.commodity, alert.region)
            observed = quote.price if alert.alert_type in {"above", "below"} else quote.daily_change_pct
            should_trigger = self._is_triggered(alert.alert_type, observed, alert.threshold)
            if not should_trigger:
                continue

            # Debounce repeated notifications for 30 minutes per alert.
            if alert.last_triggered_at and (datetime.utcnow() - alert.last_triggered_at) < timedelta(minutes=30):
                continue

            descriptor = (
                f"{alert.commodity.replace('_', ' ').title()} {alert.alert_type.replace('_', ' ')} alert: "
                f"observed {observed:.2f} {quote.currency} vs threshold {alert.threshold:.2f}"
            )
            subject = f"Commodity Alert: {alert.commodity.replace('_', ' ').title()}"
            email_status = await self.email.send_alert(user_email or alert.user_email, subject, descriptor)

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
                email_status=email_status,
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
            last_triggered_at=row.last_triggered_at,
            created_at=row.created_at,
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
            triggered_at=row.triggered_at,
        )
