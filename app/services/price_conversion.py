"""
Price conversion utilities for multi-region support.

Internal canonical unit: price per gram (USD).
All conversions go through grams as the base unit.
"""
from __future__ import annotations

TROY_OZ_TO_GRAMS: float = 31.1035
TEN_GRAMS: float = 10.0

REGION_CURRENCY: dict[str, str] = {
    "india": "INR",
    "us": "USD",
    "europe": "EUR",
}

REGION_UNIT: dict[str, str] = {
    "india": "10g",
    "us": "oz",
    "europe": "g",
}

REGION_SYMBOL: dict[str, str] = {
    "india": "₹",
    "us": "$",
    "europe": "€",
}

# Fallback FX rates (USD base) used when live API is unavailable
FALLBACK_FX: dict[str, float] = {
    "USD": 1.0,
    "INR": 83.5,
    "EUR": 0.92,
}


def grams_to_troy_oz(price_per_gram: float) -> float:
    """Convert price-per-gram to price-per-troy-ounce."""
    return price_per_gram * TROY_OZ_TO_GRAMS


def troy_oz_to_grams(price_per_troy_oz: float) -> float:
    """Convert price-per-troy-ounce to price-per-gram."""
    return price_per_troy_oz / TROY_OZ_TO_GRAMS


def grams_to_10g(price_per_gram: float) -> float:
    """Convert price-per-gram to price-per-10-grams."""
    return price_per_gram * TEN_GRAMS


def convert_price(
    price_per_gram_usd: float,
    region: str,
    fx_rates: dict[str, float] | None = None,
) -> float:
    """
    Convert a canonical USD-per-gram price to the regional display price.

    Args:
        price_per_gram_usd: Price in USD per gram (canonical internal unit).
        region: One of 'india', 'us', 'europe'.
        fx_rates: Dict mapping currency code → rate vs USD (e.g. {'INR': 83.5}).
                  Falls back to FALLBACK_FX if None.

    Returns:
        Price in the regional currency and unit.
    """
    rates = fx_rates or FALLBACK_FX
    region = region.lower()

    if region == "us":
        # USD per troy ounce
        return grams_to_troy_oz(price_per_gram_usd)
    elif region == "india":
        # INR per 10 grams
        inr_rate = rates.get("INR", FALLBACK_FX["INR"])
        price_inr_per_gram = price_per_gram_usd * inr_rate
        return grams_to_10g(price_inr_per_gram)
    elif region == "europe":
        # EUR per gram
        eur_rate = rates.get("EUR", FALLBACK_FX["EUR"])
        return price_per_gram_usd * eur_rate
    else:
        raise ValueError(f"Unknown region: {region!r}. Must be one of: india, us, europe")


def format_price(price: float, region: str) -> str:
    """
    Format a regional price with currency symbol and unit.

    Examples:
        india  → ₹74,520 / 10g
        us     → $2,315 / oz
        europe → €74.12 / g
    """
    region = region.lower()
    symbol = REGION_SYMBOL.get(region, "$")
    unit = REGION_UNIT.get(region, "oz")

    if region == "india":
        # Indian number formatting (no decimals for large INR values)
        formatted = f"{symbol}{price:,.0f} / {unit}"
    elif region == "us":
        formatted = f"{symbol}{price:,.2f} / {unit}"
    else:
        formatted = f"{symbol}{price:,.2f} / {unit}"

    return formatted


def all_regions_price(
    price_per_gram_usd: float,
    fx_rates: dict[str, float] | None = None,
) -> dict[str, dict]:
    """Return prices for all three regions from a single USD/gram price."""
    return {
        region: {
            "price": convert_price(price_per_gram_usd, region, fx_rates),
            "currency": REGION_CURRENCY[region],
            "unit": REGION_UNIT[region],
            "formatted": format_price(convert_price(price_per_gram_usd, region, fx_rates), region),
        }
        for region in ("india", "us", "europe")
    }
