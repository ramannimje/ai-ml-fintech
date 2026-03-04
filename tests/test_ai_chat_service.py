from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.services.ai_reasoning_engine import AIReasoningEngine


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
