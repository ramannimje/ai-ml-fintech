"""Tests for price conversion utilities."""
from __future__ import annotations

import pytest
from app.services.price_conversion import (
    FALLBACK_FX,
    TROY_OZ_TO_GRAMS,
    all_regions_price,
    convert_price,
    format_price,
    grams_to_10g,
    grams_to_troy_oz,
    troy_oz_to_grams,
)

MOCK_FX = {"USD": 1.0, "INR": 84.0, "EUR": 0.93}


class TestUnitConversions:
    def test_grams_to_troy_oz(self) -> None:
        """1 troy oz = 31.1035 grams, so 31.1035 g/g price → 1 oz price."""
        price_per_gram = 1.0
        result = grams_to_troy_oz(price_per_gram)
        assert abs(result - TROY_OZ_TO_GRAMS) < 0.001

    def test_troy_oz_to_grams(self) -> None:
        """Round-trip: troy_oz_to_grams(grams_to_troy_oz(x)) == x."""
        price = 65.0
        assert abs(troy_oz_to_grams(grams_to_troy_oz(price)) - price) < 0.001

    def test_grams_to_10g(self) -> None:
        """10g price = 10 × per-gram price."""
        assert grams_to_10g(7500.0) == pytest.approx(75000.0)

    def test_grams_to_troy_oz_gold_price(self) -> None:
        """Typical gold: ~$65/g → ~$2022/oz."""
        result = grams_to_troy_oz(65.0)
        assert 2000 < result < 2100


class TestConvertPrice:
    def test_convert_price_us(self) -> None:
        """US region: USD per troy ounce."""
        price_per_gram_usd = 65.0
        result = convert_price(price_per_gram_usd, "us", MOCK_FX)
        expected = grams_to_troy_oz(price_per_gram_usd)
        assert abs(result - expected) < 0.01

    def test_convert_price_india(self) -> None:
        """India region: INR per 10 grams."""
        price_per_gram_usd = 65.0
        result = convert_price(price_per_gram_usd, "india", MOCK_FX)
        expected = grams_to_10g(price_per_gram_usd * MOCK_FX["INR"])
        assert abs(result - expected) < 0.01

    def test_convert_price_europe(self) -> None:
        """Europe region: EUR per gram."""
        price_per_gram_usd = 65.0
        result = convert_price(price_per_gram_usd, "europe", MOCK_FX)
        expected = price_per_gram_usd * MOCK_FX["EUR"]
        assert abs(result - expected) < 0.01

    def test_convert_price_case_insensitive(self) -> None:
        """Region names should be case-insensitive."""
        r1 = convert_price(65.0, "US", MOCK_FX)
        r2 = convert_price(65.0, "us", MOCK_FX)
        assert r1 == r2

    def test_convert_price_fallback_fx(self) -> None:
        """When fx_rates=None, uses FALLBACK_FX."""
        result = convert_price(65.0, "india", None)
        expected = grams_to_10g(65.0 * FALLBACK_FX["INR"])
        assert abs(result - expected) < 0.01

    def test_convert_price_unknown_region(self) -> None:
        """Unknown region raises ValueError."""
        with pytest.raises(ValueError, match="Unknown region"):
            convert_price(65.0, "mars", MOCK_FX)


class TestFormatPrice:
    def test_format_price_india(self) -> None:
        """India format: ₹ symbol, /10g_24k unit."""
        result = format_price(74520.0, "india")
        assert "₹" in result
        assert "10g_24k" in result

    def test_format_price_us(self) -> None:
        """US format: $ symbol, /oz unit."""
        result = format_price(2315.50, "us")
        assert "$" in result
        assert "oz" in result

    def test_format_price_europe(self) -> None:
        """Europe format: € symbol, /exchange_standard unit."""
        result = format_price(74.12, "europe")
        assert "€" in result
        assert "/ exchange_standard" in result


class TestAllRegionsPrice:
    def test_all_regions_price_returns_three_regions(self) -> None:
        result = all_regions_price(65.0, MOCK_FX)
        assert set(result.keys()) == {"india", "us", "europe"}

    def test_all_regions_price_structure(self) -> None:
        result = all_regions_price(65.0, MOCK_FX)
        for region, info in result.items():
            assert "price" in info
            assert "currency" in info
            assert "unit" in info
            assert "formatted" in info
            assert info["price"] > 0

    def test_india_price_higher_than_us_per_unit(self) -> None:
        """India INR price should be numerically much larger than USD/oz."""
        result = all_regions_price(65.0, MOCK_FX)
        assert result["india"]["price"] > result["us"]["price"]
