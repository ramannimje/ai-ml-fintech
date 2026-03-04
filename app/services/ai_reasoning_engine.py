from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math
import re
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import yfinance as yf

from app.models.chat_history import ChatHistory
from app.services.commodity_service import CommodityService
from app.services.market_intelligence import MarketIntelligenceService
from app.services.market_quote_service import ALERT_COMMODITY_SYMBOLS, MarketQuoteService

INTENTS = (
    "market_summary",
    "price_forecast",
    "historical_trend_analysis",
    "commodity_comparison",
    "region_comparison",
    "trading_outlook",
    "volatility_explanation",
)
REGIONS = ("india", "us", "europe")
COMMODITIES = ("gold", "silver", "crude_oil", "natural_gas", "copper")
MODEL_COMMODITIES = ("gold", "silver", "crude_oil")
MONTH_MAP = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}
COMMODITY_ALIASES = {
    "gold": ("gold", "xau"),
    "silver": ("silver", "xag"),
    "crude_oil": ("crude oil", "oil", "wti", "brent", "crude"),
    "natural_gas": ("natural gas", "natgas", "gas", "ng"),
    "copper": ("copper", "cu"),
}


@dataclass(slots=True)
class QueryContext:
    message: str
    intent: str
    commodity: str
    comparison_commodity: str | None
    region: str
    comparison_region: str | None
    horizon_days: int
    target_date: date | None
    is_long_term: bool
    concise: bool


class AIReasoningEngine:
    def __init__(self) -> None:
        self.commodity_service = CommodityService()
        self.intelligence = MarketIntelligenceService()
        self.market_quote = MarketQuoteService()

    async def build_context(
        self,
        session: AsyncSession,
        user_id: str,
        message: str,
        preferred_region: str,
    ) -> QueryContext:
        clean = message.strip()
        prior_messages = await self._recent_user_messages(session, user_id=user_id)
        commodity, comparison_commodity = self._resolve_commodities(clean, prior_messages)
        region, comparison_region = self._resolve_regions(clean, preferred_region, prior_messages)
        target_date, horizon_days = self._resolve_horizon(clean, prior_messages)
        intent = self._infer_intent(clean, comparison_commodity is not None, comparison_region is not None)
        if intent in {"price_forecast", "trading_outlook"} and target_date is None and horizon_days <= 1:
            horizon_days = 30
        concise = len(clean.split()) <= 4 and intent in {"market_summary", "volatility_explanation"}
        return QueryContext(
            message=clean,
            intent=intent,
            commodity=commodity,
            comparison_commodity=comparison_commodity,
            region=region,
            comparison_region=comparison_region,
            horizon_days=min(1095, max(1, horizon_days)),
            target_date=target_date,
            is_long_term=horizon_days > 90,
            concise=concise,
        )

    async def build_data_context(self, session: AsyncSession, query: QueryContext) -> dict[str, Any]:
        data: dict[str, Any] = {
            "commodity": query.commodity,
            "region": query.region,
            "comparison_commodity": query.comparison_commodity,
            "comparison_region": query.comparison_region,
            "current_price": None,
            "historical_trend": None,
            "prediction": None,
            "volatility": None,
            "regional_market_signal": None,
            "comparison": None,
            "long_term_projection": None,
        }

        current_row = await self._get_live_price(query.commodity, query.region)
        data["current_price"] = current_row
        historical = await self._get_historical(query.commodity, query.region, period="6m")
        trend = self._trend_summary(historical)
        data["historical_trend"] = trend
        data["volatility"] = trend["volatility_label"]
        data["regional_market_signal"] = await self._regional_signal(query.region)

        if query.intent in {"price_forecast", "trading_outlook"}:
            prediction, long_term_projection = await self._prediction_bundle(
                session=session,
                commodity=query.commodity,
                region=query.region,
                horizon_days=query.horizon_days,
                trend=trend,
            )
            data["prediction"] = prediction
            data["long_term_projection"] = long_term_projection

        if query.intent == "commodity_comparison" and query.comparison_commodity:
            base = trend
            other_hist = await self._get_historical(query.comparison_commodity, query.region, period="6m")
            other_trend = self._trend_summary(other_hist)
            other_live = await self._get_live_price(query.comparison_commodity, query.region)
            data["comparison"] = {
                "left": {
                    "commodity": query.commodity,
                    "trend": base,
                    "live": current_row,
                },
                "right": {
                    "commodity": query.comparison_commodity,
                    "trend": other_trend,
                    "live": other_live,
                },
            }

        if query.intent == "region_comparison" and query.comparison_region:
            left_live = current_row
            right_live = await self._get_live_price(query.commodity, query.comparison_region)
            right_hist = await self._get_historical(query.commodity, query.comparison_region, period="6m")
            data["comparison"] = {
                "left": {
                    "region": query.region,
                    "live": left_live,
                    "trend": trend,
                },
                "right": {
                    "region": query.comparison_region,
                    "live": right_live,
                    "trend": self._trend_summary(right_hist),
                },
            }

        return data

    def generate_answer(self, query: QueryContext, data: dict[str, Any]) -> str:
        heading = f"{self._label(query.commodity)} Market Outlook - {query.region.upper()}"
        current = data["current_price"]
        trend = data["historical_trend"]
        prediction = data.get("prediction")
        long_term = data.get("long_term_projection")
        signal = data.get("regional_market_signal")

        if query.intent == "commodity_comparison" and data.get("comparison"):
            return self._commodity_comparison_answer(query, data["comparison"])
        if query.intent == "region_comparison" and data.get("comparison"):
            return self._region_comparison_answer(query, data["comparison"])

        lines: list[str] = [heading, ""]
        lines.append("Current Market")
        lines.append(
            f"{self._label(query.commodity)} is trading near {current['price']:.2f} {current['currency']} per {current['unit']} "
            f"with {trend['direction']} momentum in recent sessions."
        )
        lines.append("")
        lines.append("Trend Analysis")
        lines.append(
            f"Over the latest window, price change is {trend['change_pct']:+.2f}% with {trend['volatility_label']} volatility "
            f"({trend['volatility_pct']:.2f}% realized)."
        )

        if prediction:
            prediction_currency = prediction.get("currency") or current["currency"]
            lines.append("")
            lines.append("Forecast")
            if query.target_date:
                lines.append(
                    f"For {query.target_date.isoformat()}, the model-implied range is "
                    f"{prediction['low']:.2f} - {prediction['high']:.2f} {prediction_currency} "
                    f"with a central estimate near {prediction['point']:.2f}."
                )
            else:
                lines.append(
                    f"For the next {query.horizon_days} days, expected range is "
                    f"{prediction['low']:.2f} - {prediction['high']:.2f} {prediction_currency} "
                    f"(base case {prediction['point']:.2f})."
                )
            lines.append(f"Model basis: {prediction['basis']}.")

        if long_term:
            lines.append("")
            lines.append("Longer-term Outlook")
            lines.append(
                f"Horizon exceeds direct model coverage. Trend extrapolation suggests "
                f"{long_term['low']:.2f} - {long_term['high']:.2f} {current['currency']} "
                f"with midpoint {long_term['mid']:.2f}."
            )

        lines.append("")
        lines.append("Key Drivers")
        for driver in self._drivers(query.commodity, trend["direction"], trend["volatility_label"]):
            lines.append(f"- {driver}")
        lines.append("")
        lines.append("Market Signal")
        lines.append(
            f"Current sentiment: {trend['signal_text']}. Regional pulse: {signal}."
        )

        if query.concise:
            return "\n".join(lines[:7] + ["", lines[-1]])
        return "\n".join(lines)

    async def _recent_user_messages(self, session: AsyncSession, user_id: str) -> list[str]:
        rows = (
            await session.execute(
                select(ChatHistory)
                .where(ChatHistory.user_id == user_id)
                .order_by(ChatHistory.created_at.desc())
                .limit(6)
            )
        ).scalars().all()
        return [row.message for row in rows]

    def _resolve_commodities(self, message: str, history: list[str]) -> tuple[str, str | None]:
        text = message.lower()
        found = self._extract_commodities(text)
        if not found:
            for prev in history:
                prev_found = self._extract_commodities(prev.lower())
                if prev_found:
                    found = prev_found
                    break
        if not found:
            found = ["gold"]
        comparison = found[1] if len(found) > 1 else None
        return found[0], comparison

    def _resolve_regions(self, message: str, preferred_region: str, history: list[str]) -> tuple[str, str | None]:
        text = message.lower()
        regions = self._extract_regions(text)
        if not regions:
            for prev in history:
                prev_regions = self._extract_regions(prev.lower())
                if prev_regions:
                    regions = prev_regions
                    break
        if not regions:
            regions = [preferred_region if preferred_region in REGIONS else "us"]
        comparison = regions[1] if len(regions) > 1 else None
        return regions[0], comparison

    def _resolve_horizon(self, message: str, history: list[str]) -> tuple[date | None, int]:
        text = message.lower()
        today = datetime.now(timezone.utc).date()
        explicit = self._extract_date_horizon(text, today)
        if explicit:
            return explicit
        if "next quarter" in text:
            return None, 90
        if "this quarter" in text:
            return None, 60
        if "this month" in text:
            return None, 30
        if "next month" in text:
            return None, 45
        match = re.search(r"(\d{1,3})\s*(day|days|d|week|weeks|month|months|year|years)", text)
        if match:
            value = max(1, int(match.group(1)))
            unit = match.group(2)
            if unit.startswith("week"):
                value *= 7
            elif unit.startswith("month"):
                value *= 30
            elif unit.startswith("year"):
                value *= 365
            return None, value

        # Follow-up date-only question like "what about in august".
        for month_name, month_val in MONTH_MAP.items():
            if re.search(rf"\bin\s+{month_name}\b", text):
                year = today.year if today.month <= month_val else today.year + 1
                target = self._month_end(year, month_val)
                return target, max(1, (target - today).days)

        for prev in history:
            prev_explicit = self._extract_date_horizon(prev.lower(), today)
            if prev_explicit:
                return prev_explicit
        return None, 30

    def _extract_date_horizon(self, text: str, today: date) -> tuple[date | None, int] | None:
        end_year_match = re.search(r"(end of|by)\s+(20\d{2})", text)
        if end_year_match:
            target = date(int(end_year_match.group(2)), 12, 31)
            return target, max(1, (target - today).days)

        month_year_match = re.search(
            r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
            r"sep(?:tember)?|sept|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(20\d{2})",
            text,
        )
        if month_year_match:
            month_raw = month_year_match.group(1)
            month = MONTH_MAP[month_raw]
            year = int(month_year_match.group(2))
            target = self._month_end(year, month)
            return target, max(1, (target - today).days)

        year_month_match = re.search(
            r"(20\d{2})\s+"
            r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
            r"sep(?:tember)?|sept|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)",
            text,
        )
        if year_month_match:
            year = int(year_month_match.group(1))
            month_raw = year_month_match.group(2)
            month = MONTH_MAP[month_raw]
            target = self._month_end(year, month)
            return target, max(1, (target - today).days)
        return None

    def _infer_intent(self, message: str, has_comparison_commodity: bool, has_comparison_region: bool) -> str:
        text = message.lower()
        if has_comparison_region or ("compare" in text and any(r in text for r in REGIONS)):
            return "region_comparison"
        if has_comparison_commodity or "compare" in text or "vs" in text:
            return "commodity_comparison"
        if any(word in text for word in ("forecast", "predict", "will", "price in", "target", "future", "by ")):
            return "price_forecast"
        if any(word in text for word in ("outlook", "bullish", "bearish", "best commodity", "best to watch")):
            return "trading_outlook"
        if any(word in text for word in ("volatility", "volatile", "spike", "sudden move")):
            return "volatility_explanation"
        if any(word in text for word in ("historical", "history", "trend", "chart")):
            return "historical_trend_analysis"
        return "market_summary"

    def _extract_commodities(self, text: str) -> list[str]:
        out: list[str] = []
        for commodity, aliases in COMMODITY_ALIASES.items():
            if any(self._contains_alias(text, alias) for alias in aliases):
                out.append(commodity)
        return out

    def _extract_regions(self, text: str) -> list[str]:
        region_aliases = {
            "india": ("india", "indian"),
            "us": ("us", "usa", "united states", "america"),
            "europe": ("europe", "eu", "european"),
        }
        out: list[str] = []
        for region, aliases in region_aliases.items():
            if any(self._contains_alias(text, alias) for alias in aliases):
                out.append(region)
        return out

    @staticmethod
    def _contains_alias(text: str, alias: str) -> bool:
        if " " in alias:
            return alias in text
        return re.search(rf"\b{re.escape(alias)}\b", text) is not None

    @staticmethod
    def _month_end(year: int, month: int) -> date:
        if month == 12:
            return date(year, month, 31)
        return (date(year, month, 28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    async def _get_live_price(self, commodity: str, region: str) -> dict[str, Any]:
        if commodity in MODEL_COMMODITIES:
            rows = await self.commodity_service.live_prices(region=region)
            row = next((item for item in rows if item.commodity == commodity), None)
            if row:
                return {
                    "price": float(row.live_price),
                    "currency": row.currency,
                    "unit": row.unit,
                    "source": row.source,
                }
        quote = self.market_quote.fetch_quote(commodity=commodity, region=region)
        return {
            "price": float(quote.price),
            "currency": quote.currency,
            "unit": quote.unit,
            "source": quote.source,
        }

    async def _get_historical(self, commodity: str, region: str, period: str = "6m") -> list[float]:
        if commodity in MODEL_COMMODITIES:
            history = await self.commodity_service.historical(commodity, region=region, period=period)
            return [point.close for point in history.data if point.close is not None]
        symbol = ALERT_COMMODITY_SYMBOLS[commodity]
        frame = yf.download(symbol, period=period, auto_adjust=False, progress=False)
        if frame.empty or "Close" not in frame.columns:
            return []
        close_series = pd.to_numeric(frame["Close"], errors="coerce").dropna()
        return [float(value) for value in close_series.tolist()]

    def _trend_summary(self, closes: list[float]) -> dict[str, Any]:
        if len(closes) < 3:
            return {
                "change_pct": 0.0,
                "volatility_pct": 0.0,
                "volatility_label": "low",
                "direction": "neutral",
                "signal_text": "neutral",
                "avg_return": 0.0,
            }
        lookback = closes[-90:] if len(closes) > 90 else closes
        first = lookback[0]
        last = lookback[-1]
        change_pct = ((last - first) / first) * 100 if first else 0.0
        returns = []
        for idx in range(1, len(lookback)):
            base = lookback[idx - 1]
            if base == 0:
                continue
            returns.append((lookback[idx] - base) / base)
        avg_ret = float(sum(returns) / len(returns)) if returns else 0.0
        vol = math.sqrt(sum((ret - avg_ret) ** 2 for ret in returns) / len(returns)) * 100 if returns else 0.0
        if change_pct > 1.0:
            direction = "bullish"
        elif change_pct < -1.0:
            direction = "bearish"
        else:
            direction = "neutral"
        if vol >= 2.5:
            vol_label = "high"
        elif vol >= 1.0:
            vol_label = "moderate"
        else:
            vol_label = "low"
        signal = "moderately bullish" if direction == "bullish" and vol_label != "high" else direction
        if direction == "neutral" and vol_label == "high":
            signal = "directionless but volatile"
        return {
            "change_pct": round(change_pct, 2),
            "volatility_pct": round(vol, 2),
            "volatility_label": vol_label,
            "direction": direction,
            "signal_text": signal,
            "avg_return": avg_ret,
            "last": last,
        }

    async def _prediction_bundle(
        self,
        session: AsyncSession,
        commodity: str,
        region: str,
        horizon_days: int,
        trend: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        if commodity in MODEL_COMMODITIES:
            model_horizon = min(90, max(1, horizon_days))
            pred = await self.commodity_service.predict(
                session=session,
                commodity=commodity,
                region=region,
                horizon=model_horizon,
            )
            prediction = {
                "point": float(pred.point_forecast),
                "low": float(pred.confidence_interval[0]),
                "high": float(pred.confidence_interval[1]),
                "currency": pred.currency,
                "basis": f"platform model ({pred.model_used})",
            }
            if horizon_days <= 90:
                return prediction, None

            # Long-term extension from model anchor + trend slope.
            extra_days = horizon_days - 90
            monthly_drift = float(trend.get("avg_return", 0.0)) * 21
            projected_ret = max(-0.25, min(0.25, monthly_drift * (extra_days / 30)))
            mid = prediction["point"] * (1.0 + projected_ret)
            spread = max(0.03, abs(projected_ret) * 0.6) * prediction["point"]
            long_term = {
                "mid": round(mid, 2),
                "low": round(max(0.0, mid - spread), 2),
                "high": round(mid + spread, 2),
            }
            return prediction, long_term

        # Unsupported by predictive model: trend-based projection.
        last = float(trend.get("last", 0.0))
        monthly_drift = float(trend.get("avg_return", 0.0)) * 21
        projected_ret = max(-0.30, min(0.30, monthly_drift * (horizon_days / 30)))
        point = last * (1.0 + projected_ret)
        spread = max(abs(point) * 0.03, abs(point) * (float(trend.get("volatility_pct", 1.0)) / 100) * 1.4)
        prediction = {
            "point": round(point, 2),
            "low": round(max(0.0, point - spread), 2),
            "high": round(point + spread, 2),
            "currency": None,
            "basis": "trend extrapolation (model unavailable for this commodity)",
        }
        return prediction, None

    async def _regional_signal(self, region: str) -> str:
        rows = await self.commodity_service.live_prices(region=region)
        historical_map: dict[str, Any] = {}
        for commodity in MODEL_COMMODITIES:
            historical = await self.commodity_service.historical(commodity, region=region, period="1m")
            historical_map[commodity] = historical
        ranked = self.intelligence.rank_trending(rows, historical_map)
        if not ranked:
            return "insufficient cross-commodity signal"
        top = ranked[0]
        return f"{self._label(str(top['commodity']))} leads momentum ({float(top['change_pct']):+.2f}%)"

    def _drivers(self, commodity: str, direction: str, volatility_label: str) -> list[str]:
        common = [
            "USD and local FX moves influencing commodity translation",
            "Rate and inflation expectations shaping risk appetite",
        ]
        commodity_specific = {
            "gold": "Safe-haven demand and central-bank accumulation",
            "silver": "Industrial demand from electronics and solar manufacturing",
            "crude_oil": "Inventory levels and OPEC+ supply discipline",
            "natural_gas": "Weather-driven demand and storage positioning",
            "copper": "Manufacturing cycle and infrastructure demand",
        }
        mood = {
            "bullish": "Price action shows buyers absorbing pullbacks",
            "bearish": "Downside pressure remains visible on rebounds",
            "neutral": "Market is range-bound with balanced flows",
        }[direction]
        risk = (
            "Elevated volatility increases short-term forecast uncertainty"
            if volatility_label == "high"
            else "Volatility remains contained, supporting clearer directional reads"
        )
        return [commodity_specific[commodity], common[0], common[1], mood, risk]

    def _commodity_comparison_answer(self, query: QueryContext, comparison: dict[str, Any]) -> str:
        left = comparison["left"]
        right = comparison["right"]
        left_trend = left["trend"]
        right_trend = right["trend"]
        left_live = left["live"]
        right_live = right["live"]
        winner = query.commodity if abs(left_trend["change_pct"]) >= abs(right_trend["change_pct"]) else query.comparison_commodity
        return "\n".join(
            [
                f"Commodity Comparison - {query.region.upper()}",
                "",
                f"{self._label(query.commodity)}: {left_live['price']:.2f} {left_live['currency']} | "
                f"{left_trend['change_pct']:+.2f}% trend | volatility {left_trend['volatility_label']}.",
                f"{self._label(query.comparison_commodity or '')}: {right_live['price']:.2f} {right_live['currency']} | "
                f"{right_trend['change_pct']:+.2f}% trend | volatility {right_trend['volatility_label']}.",
                "",
                f"Relative read: {self._label(winner or query.commodity)} currently shows stronger directional momentum.",
            ]
        )

    def _region_comparison_answer(self, query: QueryContext, comparison: dict[str, Any]) -> str:
        left = comparison["left"]
        right = comparison["right"]
        return "\n".join(
            [
                f"Region Comparison - {self._label(query.commodity)}",
                "",
                f"{left['region'].upper()}: {left['live']['price']:.2f} {left['live']['currency']} | "
                f"{left['trend']['change_pct']:+.2f}% trend.",
                f"{right['region'].upper()}: {right['live']['price']:.2f} {right['live']['currency']} | "
                f"{right['trend']['change_pct']:+.2f}% trend.",
                "",
                "Pricing differs mainly due to currency conversion and region-specific market basis.",
            ]
        )

    @staticmethod
    def _label(commodity: str) -> str:
        return commodity.replace("_", " ").title()
