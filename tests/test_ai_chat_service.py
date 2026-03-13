from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.ai_reasoning_engine import AIReasoningEngine, QueryContext


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _ExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _ScalarResult(self._rows)


class _HistoryRow:
    def __init__(self, message: str):
        self.message = message
        self.created_at = datetime.now(timezone.utc)


class _SessionStub:
    def __init__(self, messages: list[str] | None = None):
        self._messages = messages or []

    async def execute(self, _stmt):
        rows = [_HistoryRow(msg) for msg in self._messages]
        return _ExecuteResult(rows)


def test_intent_understanding_market_summary() -> None:
    engine = AIReasoningEngine()
    context = asyncio.run(
        engine.build_context(
            session=_SessionStub(),  # type: ignore[arg-type]
            user_id="u1",
            message="how about silver",
            preferred_region="india",
        )
    )
    assert context.intent == "market_summary"
    assert context.commodity == "silver"
    assert context.region == "india"


def test_intent_understanding_forecast_calendar() -> None:
    engine = AIReasoningEngine()
    context = asyncio.run(
        engine.build_context(
            session=_SessionStub(),  # type: ignore[arg-type]
            user_id="u1",
            message="what will silver price be in august 2026",
            preferred_region="us",
        )
    )
    assert context.intent == "price_forecast"
    assert context.commodity == "silver"
    assert context.target_date is not None
    assert context.target_date.year == 2026
    assert context.target_date.month == 8
    assert context.horizon_days > 90


def test_intent_understanding_forecast_calendar_year_month_order() -> None:
    engine = AIReasoningEngine()
    context = asyncio.run(
        engine.build_context(
            session=_SessionStub(),  # type: ignore[arg-type]
            user_id="u1",
            message="Tell me the gold price in 2026 December.",
            preferred_region="india",
        )
    )
    assert context.intent == "price_forecast"
    assert context.commodity == "gold"
    assert context.region == "india"
    assert context.target_date is not None
    assert context.target_date.year == 2026
    assert context.target_date.month == 12
    assert context.horizon_days > 90


def test_follow_up_context_carries_commodity() -> None:
    engine = AIReasoningEngine()
    context = asyncio.run(
        engine.build_context(
            session=_SessionStub(messages=["how about silver"]),  # type: ignore[arg-type]
            user_id="u1",
            message="what about in august",
            preferred_region="us",
        )
    )
    assert context.commodity == "silver"
    assert context.target_date is not None


def test_intent_understanding_investment_query_maps_to_trading_outlook() -> None:
    engine = AIReasoningEngine()
    context = asyncio.run(
        engine.build_context(
            session=_SessionStub(),  # type: ignore[arg-type]
            user_id="u1",
            message="Should I invest in silver?",
            preferred_region="india",
        )
    )
    assert context.intent == "trading_outlook"
    assert context.commodity == "silver"


def test_intent_understanding_shall_i_invest_maps_to_trading_outlook() -> None:
    engine = AIReasoningEngine()
    context = asyncio.run(
        engine.build_context(
            session=_SessionStub(),  # type: ignore[arg-type]
            user_id="u1",
            message="shall I invest in silver now?",
            preferred_region="india",
        )
    )
    assert context.intent == "trading_outlook"
    assert context.commodity == "silver"


def test_trading_outlook_includes_investment_view_section() -> None:
    engine = AIReasoningEngine()
    query = QueryContext(
        message="Should I invest in silver?",
        intent="trading_outlook",
        commodity="silver",
        comparison_commodity=None,
        region="india",
        comparison_region=None,
        horizon_days=30,
        target_date=None,
        is_long_term=False,
        concise=False,
    )
    text = engine.generate_answer(
        query=query,
        data={
            "current_price": {"price": 2558.65, "currency": "INR", "unit": "10g"},
            "historical_trend": {
                "change_pct": 12.3,
                "volatility_pct": 1.6,
                "volatility_label": "moderate",
                "direction": "bullish",
                "signal_text": "moderately bullish",
                "avg_return": 0.01,
            },
            "prediction": {"point": 2650.0, "low": 2480.0, "high": 2810.0, "currency": "INR", "basis": "test-model"},
            "long_term_projection": None,
            "regional_market_signal": "Gold leads momentum (+2.10%)",
        },
    )
    assert "Investment View" in text
    assert "Bias:" in text


def test_build_data_context_for_modeled_commodity_uses_extracted_services(monkeypatch) -> None:
    engine = AIReasoningEngine()
    query = QueryContext(
        message="gold outlook",
        intent="trading_outlook",
        commodity="gold",
        comparison_commodity=None,
        region="us",
        comparison_region=None,
        horizon_days=30,
        target_date=None,
        is_long_term=False,
        concise=False,
    )

    async def _live_price(commodity: str, region: str):
        _ = commodity, region
        return SimpleNamespace(commodity="gold", live_price=2350.0, currency="USD", unit="oz", source="metals.live")

    def _historical_response(commodity: str, region: str, period: str):
        _ = commodity, region, period
        return SimpleNamespace(
            data=[SimpleNamespace(close=value) for value in [2280.0, 2300.0, 2325.0, 2340.0, 2360.0]]
        )

    async def _prediction(session, commodity: str, region: str, horizon: int):
        _ = session, commodity, region, horizon
        return SimpleNamespace(
            point_forecast=2400.0,
            confidence_interval=(2340.0, 2460.0),
            currency="USD",
            model_used="xgb_us_test",
        )

    async def _bundle(session, commodity: str, region: str, horizon: int, include_news: bool):
        _ = session, commodity, region, horizon, include_news
        return SimpleNamespace(model_dump=lambda mode="json": {"signal": {"label": "bullish", "confidence": 0.71}})

    monkeypatch.setattr(engine, "_modeled_live_price_response", _live_price)
    monkeypatch.setattr(engine, "_modeled_historical_response", _historical_response)
    monkeypatch.setattr(engine, "_modeled_prediction_response", _prediction)
    monkeypatch.setattr(engine, "_regional_signal", lambda region: asyncio.sleep(0, result=f"Gold leads in {region}"))
    monkeypatch.setattr(engine.market_signal_service, "build_market_intelligence", _bundle)

    data = asyncio.run(engine.build_data_context(session=_SessionStub(), query=query))  # type: ignore[arg-type]
    assert data["current_price"]["price"] == 2350.0
    assert data["prediction"]["point"] == 2400.0
    assert data["signal_bundle"]["signal"]["label"] == "bullish"
