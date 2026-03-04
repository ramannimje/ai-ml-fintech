from __future__ import annotations

from dataclasses import dataclass
import math

from app.schemas.responses import LivePriceResponse, RegionalHistoricalResponse


@dataclass(slots=True)
class TrendInsight:
    direction: str
    change_pct: float
    volatility_pct: float
    spike_detected: bool


class MarketIntelligenceService:
    def analyze_trend(self, historical: RegionalHistoricalResponse) -> TrendInsight:
        closes = [point.close for point in historical.data if point.close is not None]
        if len(closes) < 3:
            return TrendInsight(direction="neutral", change_pct=0.0, volatility_pct=0.0, spike_detected=False)

        latest = closes[-1]
        previous = closes[-2]
        first = closes[max(0, len(closes) - 8)]
        change_pct = ((latest - first) / first) * 100 if first else 0.0

        returns = []
        for idx in range(1, len(closes)):
            base = closes[idx - 1]
            if base == 0:
                continue
            returns.append((closes[idx] - base) / base)
        if returns:
            mean_ret = sum(returns) / len(returns)
            variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
            volatility_pct = math.sqrt(max(variance, 0.0)) * 100
            last_return = returns[-1]
            spike_detected = abs(last_return) > max(0.025, 2.5 * (math.sqrt(max(variance, 0.0)) or 0.01))
        else:
            volatility_pct = 0.0
            spike_detected = False

        if change_pct > 1.2:
            direction = "bullish"
        elif change_pct < -1.2:
            direction = "bearish"
        else:
            direction = "neutral"

        # Override weak trend calls when immediate momentum is clearly opposite.
        immediate_pct = ((latest - previous) / previous) * 100 if previous else 0.0
        if direction == "neutral" and immediate_pct > 0.8:
            direction = "bullish"
        elif direction == "neutral" and immediate_pct < -0.8:
            direction = "bearish"

        return TrendInsight(
            direction=direction,
            change_pct=round(change_pct, 2),
            volatility_pct=round(volatility_pct, 2),
            spike_detected=spike_detected,
        )

    def rank_trending(
        self,
        live_prices: list[LivePriceResponse],
        historical_by_commodity: dict[str, RegionalHistoricalResponse],
    ) -> list[dict[str, str | float]]:
        ranking: list[dict[str, str | float]] = []
        for item in live_prices:
            historical = historical_by_commodity.get(item.commodity)
            if not historical or len(historical.data) < 3:
                continue
            insight = self.analyze_trend(historical)
            score = (abs(insight.change_pct) * 0.7) + (insight.volatility_pct * 0.3)
            ranking.append(
                {
                    "commodity": item.commodity,
                    "score": round(score, 2),
                    "direction": insight.direction,
                    "change_pct": insight.change_pct,
                    "live_price": round(item.live_price, 4),
                    "currency": item.currency,
                }
            )

        ranking.sort(key=lambda row: float(row["score"]), reverse=True)
        return ranking

