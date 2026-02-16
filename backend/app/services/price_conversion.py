from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

REGIONS = {
    "india": {"currency": "INR", "unit": "10g", "grams_per_unit": 10.0, "symbol": "₹"},
    "us": {"currency": "USD", "unit": "oz", "grams_per_unit": 31.1034768, "symbol": "$"},
    "europe": {"currency": "EUR", "unit": "g", "grams_per_unit": 1.0, "symbol": "€"},
}


class FXRateService:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, datetime]] = {}

    async def usd_to(self, currency: str) -> float:
        if currency == "USD":
            return 1.0
        now = datetime.now(timezone.utc)
        cached = self._cache.get(currency)
        if cached and cached[1] > now:
            return cached[0]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get("https://api.exchangerate.host/latest", params={"base": "USD", "symbols": currency})
                response.raise_for_status()
                rate = float(response.json()["rates"][currency])
        except Exception:
            rate = {"INR": 83.0, "EUR": 0.92}.get(currency, 1.0)
        self._cache[currency] = (rate, now + timedelta(hours=1))
        return rate


class PriceConverter:
    def __init__(self) -> None:
        self.fx = FXRateService()

    @staticmethod
    def grams_to_unit(price_per_gram: float, region: str) -> float:
        return price_per_gram * REGIONS[region]["grams_per_unit"]

    @staticmethod
    def unit_to_grams(price_per_unit: float, region: str) -> float:
        return price_per_unit / REGIONS[region]["grams_per_unit"]

    async def usd_per_gram_to_region(self, price_usd_per_gram: float, region: str) -> float:
        cfg = REGIONS[region]
        fx = await self.fx.usd_to(cfg["currency"])
        return self.grams_to_unit(price_usd_per_gram * fx, region)
