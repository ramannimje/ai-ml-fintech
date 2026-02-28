"""FX rate fetching with in-memory TTL cache and graceful failover."""
from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_FX_CACHE: dict[str, Any] = {}
_HIST_CACHE: dict[str, Any] = {}

FX_TTL_SECONDS = 60         # 60 seconds
HIST_TTL_SECONDS = 600      # 10 minutes

ECB_FX_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
FALLBACK_FX_URL = "https://open.er-api.com/v6/latest/USD"


def _from_ecb_xml(xml_payload: str) -> dict[str, float]:
    """
    Parse ECB XML (EUR base) into USD base rates.
    Returns mapping like {'USD': 1.0, 'EUR': 0.92, 'INR': 83.5}.
    """
    root = ET.fromstring(xml_payload)
    cube_nodes = root.findall(".//{*}Cube[@currency][@rate]")
    eur_based: dict[str, float] = {"EUR": 1.0}
    for cube in cube_nodes:
        currency = cube.attrib.get("currency")
        rate = cube.attrib.get("rate")
        if not currency or not rate:
            continue
        eur_based[currency] = float(rate)

    usd_per_eur = eur_based.get("USD")
    if not usd_per_eur:
        raise ValueError("ECB payload missing USD rate")

    usd_base: dict[str, float] = {"USD": 1.0}
    for currency, eur_rate in eur_based.items():
        usd_base[currency] = eur_rate / usd_per_eur
    return usd_base


def _fetch_ecb_rates() -> dict[str, float]:
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(ECB_FX_URL)
        resp.raise_for_status()
        return _from_ecb_xml(resp.text)


def _fetch_fallback_rates() -> dict[str, float]:
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(FALLBACK_FX_URL)
        resp.raise_for_status()
        data = resp.json()
    rates: dict[str, float] = data.get("rates", {})
    rates["USD"] = 1.0
    return rates


def get_fx_rates() -> dict[str, float]:
    """
    Return current FX rates relative to USD.
    Order: cached -> ECB -> fallback API -> stale cache.
    """
    now = time.monotonic()
    cached = _FX_CACHE.get("rates")
    if cached and (now - cached["ts"]) < FX_TTL_SECONDS:
        return cached["data"]

    try:
        rates = _fetch_ecb_rates()
        _FX_CACHE["rates"] = {"data": rates, "ts": now}
        logger.info("FX rates refreshed from ECB")
        return rates
    except Exception as exc:
        logger.warning("FX primary source failed (ECB): %s", exc)

    try:
        rates = _fetch_fallback_rates()
        _FX_CACHE["rates"] = {"data": rates, "ts": now}
        logger.info("FX rates refreshed from fallback API")
        return rates
    except Exception as exc:
        logger.warning("FX fallback source failed: %s", exc)

    if cached:
        logger.warning("Serving stale FX rates from cache due to source failures")
        return cached["data"]
    raise RuntimeError("Unable to fetch FX rates and no cached rates available")


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
