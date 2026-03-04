from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_settings import UserSettings
from app.schemas.responses import UserSettingsResponse, UserSettingsUpdateRequest


class SettingsService:
    async def get_or_create(self, session: AsyncSession, user_id: str) -> UserSettingsResponse:
        result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id).limit(1))
        settings = result.scalar_one_or_none()
        if not settings:
            settings = UserSettings(
                user_id=user_id,
                default_region="us",
                default_commodity="gold",
                prediction_horizon=30,
                email_notifications=True,
                alert_cooldown_minutes=30,
                alerts_enabled=True,
                enable_chronos_bolt=False,
                enable_xgboost=True,
                auto_retrain=False,
                theme_preference="system",
            )
            session.add(settings)
            await session.commit()
            await session.refresh(settings)
        return self._to_response(settings)

    async def update(
        self,
        session: AsyncSession,
        user_id: str,
        payload: UserSettingsUpdateRequest,
    ) -> UserSettingsResponse:
        result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id).limit(1))
        settings = result.scalar_one_or_none()
        if not settings:
            _ = await self.get_or_create(session, user_id)
            result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id).limit(1))
            settings = result.scalar_one()

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)

        await session.commit()
        await session.refresh(settings)
        return self._to_response(settings)

    def _to_response(self, row: UserSettings) -> UserSettingsResponse:
        return UserSettingsResponse(
            id=row.id,
            user_id=row.user_id,
            default_region=row.default_region,  # type: ignore[arg-type]
            default_commodity=row.default_commodity,  # type: ignore[arg-type]
            prediction_horizon=row.prediction_horizon,
            email_notifications=row.email_notifications,
            alert_cooldown_minutes=row.alert_cooldown_minutes,
            alerts_enabled=row.alerts_enabled,
            enable_chronos_bolt=row.enable_chronos_bolt,
            enable_xgboost=row.enable_xgboost,
            auto_retrain=row.auto_retrain,
            theme_preference=row.theme_preference,  # type: ignore[arg-type]
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
