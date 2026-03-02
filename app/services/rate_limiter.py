from __future__ import annotations

import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover - optional dependency in local envs
    redis = None  # type: ignore[assignment]


class RedisRateLimiter:
    def __init__(self) -> None:
        self._client = None
        self._available = redis is not None

    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        if not self._available:
            return True

        if self._client is None:
            settings = get_settings()
            self._client = redis.from_url(settings.redis_url, decode_responses=True)

        try:
            current = await self._client.incr(key)
            if current == 1:
                await self._client.expire(key, window_seconds)
            return current <= limit
        except Exception as exc:
            logger.warning("rate_limiter_error key=%s error=%s", key, exc)
            # Fail open so alert processing is not blocked by Redis outages.
            return True
