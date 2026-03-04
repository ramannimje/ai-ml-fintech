from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_session
from app.schemas.responses import UserSettingsResponse, UserSettingsUpdateRequest
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])
settings_service = SettingsService()


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> UserSettingsResponse:
    return await settings_service.get_or_create(
        session=session,
        user_id=current_user.get("sub", "unknown"),
    )


@router.post("", response_model=UserSettingsResponse)
async def update_settings(
    payload: UserSettingsUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> UserSettingsResponse:
    return await settings_service.update(
        session=session,
        user_id=current_user.get("sub", "unknown"),
        payload=payload,
    )
