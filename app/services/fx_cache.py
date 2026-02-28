"""
FX rate fetching with in-memory TTL cache.

Uses open.er-api.com (free, no API key required).
Falls back to hardcoded rates if the API is unreachable.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.services.price_conversion import FALLBACK_FX

logger = logging.getLogger(__name__)

_FX_CACHE: dict[str, Any] = {}
_HIST_CACHE: dict[str, Any] = {}

FX_TTL_SECONDS = 3600       # 1 hour
HIST_TTL_SECONDS = 600      # 10 minutes

FX_API_URL = "https://open.er-api.com/v6/latest/USD"


def get_fx_rates() -> dict[str, float]:
    """
    Return current FX rates relative to USD.
    Cached for 1 hour; falls back to FALLBACK_FX on error.

    Returns:
        Dict like {'USD': 1.0, 'INR': 83.5, 'EUR': 0.92, ...}
    """
    now = time.monotonic()
    cached = _FX_CACHE.get("rates")
    if cached and (now - cached["ts"]) < FX_TTL_SECONDS:
        return cached["data"]

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(FX_API_URL)
            resp.raise_for_status()
            data = resp.json()
            rates: dict[str, float] = data.get("rates", {})
            # Ensure USD is always present
            rates["USD"] = 1.0
            _FX_CACHE["rates"] = {"data": rates, "ts": now}
            logger.info("FX rates refreshed from %s", FX_API_URL)
            return rates
    except Exception as exc:
        logger.warning("FX rate fetch failed (%s), using fallback rates", exc)
        return dict(FALLBACK_FX)


def get_cached_historical(key: str) -> Any | None:
    """Retrieve a cached historical dataset by key (commodity_region)."""
    entry = _HIST_CACHE.get(key)
    if entry and (time.monotonic() - entry["ts"]) < HIST_TTL_SECONDS:
        return entry["data"]
    return None


def set_cached_historical(key: str, data: Any) -> None:
    """Store a historical dataset in cache with 10-minute TTL."""
    _HIST_CACHE[key] = {"data": data, "ts": time.monotonic()}


def clear_caches() -> None:
    """Clear all in-memory caches (useful for testing)."""
    _FX_CACHE.clear()
    _HIST_CACHE.clear()
