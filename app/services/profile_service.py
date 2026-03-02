from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_profile import UserProfile
from app.schemas.responses import UserProfileResponse, UserProfileUpdateRequest


class ProfileService:
    async def get_or_create(
        self,
        session: AsyncSession,
        user_sub: str,
        user_email: str | None = None,
        user_name: str | None = None,
        picture_url: str | None = None,
        user_context: dict | None = None,
    ) -> UserProfileResponse:
        result = await session.execute(select(UserProfile).where(UserProfile.user_sub == user_sub).limit(1))
        profile = result.scalar_one_or_none()
        if not profile:
            profile = UserProfile(
                user_sub=user_sub,
                email=user_email,
                name=user_name,
                picture_url=picture_url,
                preferred_region=self._infer_region(user_context),
                email_notifications_enabled=True,
                alert_cooldown_minutes=30,
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)
            return self._to_response(profile)

        dirty = False
        if user_email and profile.email != user_email:
            profile.email = user_email
            dirty = True
        if user_name and profile.name != user_name:
            profile.name = user_name
            dirty = True
        if picture_url and profile.picture_url != picture_url:
            profile.picture_url = picture_url
            dirty = True
        if dirty:
            await session.commit()
            await session.refresh(profile)
        return self._to_response(profile)

    async def update(
        self,
        session: AsyncSession,
        user_sub: str,
        payload: UserProfileUpdateRequest,
        user_email: str | None = None,
    ) -> UserProfileResponse:
        current = await self.get_or_create(session, user_sub, user_email=user_email)
        result = await session.execute(select(UserProfile).where(UserProfile.user_sub == user_sub).limit(1))
        profile = result.scalar_one()

        if payload.name is not None:
            profile.name = payload.name.strip() or None
        if payload.picture_url is not None:
            profile.picture_url = payload.picture_url.strip() or None
        if payload.preferred_region is not None:
            profile.preferred_region = payload.preferred_region
        if payload.email_notifications_enabled is not None:
            profile.email_notifications_enabled = payload.email_notifications_enabled
        if payload.alert_cooldown_minutes is not None:
            profile.alert_cooldown_minutes = payload.alert_cooldown_minutes
        if user_email and profile.email != user_email:
            profile.email = user_email

        await session.commit()
        await session.refresh(profile)
        _ = current
        return self._to_response(profile)

    def _to_response(self, row: UserProfile) -> UserProfileResponse:
        return UserProfileResponse(
            user_sub=row.user_sub,
            email=row.email,
            name=row.name,
            picture_url=row.picture_url,
            preferred_region=row.preferred_region,  # type: ignore[arg-type]
            email_notifications_enabled=row.email_notifications_enabled,
            alert_cooldown_minutes=row.alert_cooldown_minutes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _infer_region(self, user_context: dict | None) -> str:
        if not user_context:
            return "us"

        values: list[str] = []
        for key, raw in user_context.items():
            key_lower = str(key).lower()
            if key_lower in {"locale", "zoneinfo", "region", "country"} or "country" in key_lower or "locale" in key_lower:
                if isinstance(raw, str):
                    values.append(raw.lower())

        for value in values:
            if "asia/kolkata" in value or "india" in value:
                return "india"
            tokens = set(re.findall(r"[a-z]+", value))
            if {"in", "ind", "inr"} & tokens:
                return "india"
            if "europe" in value or "eur" in tokens:
                return "europe"
        return "us"
