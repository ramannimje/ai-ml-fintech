from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_session
from app.schemas.responses import AIChatRequest, AIChatResponse, AIProviderStatusResponse
from app.services.ai_chat_service import AIChatService, AIProviderUnavailableError
from app.services.profile_service import ProfileService
from app.services.rate_limiter import RedisRateLimiter

router = APIRouter()
chat_service = AIChatService()
profile_service = ProfileService()
limiter = RedisRateLimiter()


@router.post("/ai/chat", response_model=AIChatResponse)
async def ai_chat(
    payload: AIChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> AIChatResponse:
    user_sub = current_user.get("sub", "unknown")
    allowed = await limiter.allow(key=f"ai-chat:{user_sub}", limit=40, window_seconds=60)
    if not allowed:
        raise HTTPException(status_code=429, detail="AI chat rate limit exceeded. Please retry in a minute.")

    profile = await profile_service.get_or_create(
        session=session,
        user_sub=user_sub,
        user_email=current_user.get("email"),
        user_name=current_user.get("name"),
        picture_url=current_user.get("picture"),
        user_context=current_user,
    )
    try:
        return await chat_service.ask(
            session=session,
            user_id=user_sub,
            message=payload.message,
            preferred_region=profile.preferred_region,
        )
    except AIProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"AI provider unavailable: {exc}") from exc


@router.post("/ai/chat/stream")
async def ai_chat_stream(
    payload: AIChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    user_sub = current_user.get("sub", "unknown")
    allowed = await limiter.allow(key=f"ai-chat:{user_sub}", limit=40, window_seconds=60)
    if not allowed:
        raise HTTPException(status_code=429, detail="AI chat rate limit exceeded. Please retry in a minute.")

    profile = await profile_service.get_or_create(
        session=session,
        user_sub=user_sub,
        user_email=current_user.get("email"),
        user_name=current_user.get("name"),
        picture_url=current_user.get("picture"),
        user_context=current_user,
    )
    try:
        response = await chat_service.ask(
            session=session,
            user_id=user_sub,
            message=payload.message,
            preferred_region=profile.preferred_region,
        )
    except AIProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"AI provider unavailable: {exc}") from exc

    async def event_stream():
        text = response.answer
        chunk_size = 22
        for idx in range(0, len(text), chunk_size):
            chunk = text[idx : idx + chunk_size]
            yield f"event: token\ndata: {json.dumps({'delta': chunk}, ensure_ascii=True)}\n\n"
            await asyncio.sleep(0.01)
        yield f"event: done\ndata: {response.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/ai/provider-status", response_model=AIProviderStatusResponse)
async def ai_provider_status() -> AIProviderStatusResponse:
    return AIProviderStatusResponse(**chat_service.provider_status())
