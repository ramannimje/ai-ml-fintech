from __future__ import annotations

from app.schemas.responses import (
    DataProvenance,
    EngineeredFeatureSnapshot,
    MarketSignalResponse,
    MarketSignalSummary,
)


class SignalService:
    def summarize(
        self,
        *,
        current_price: float,
        point_forecast: float,
        forecast_range: tuple[float, float],
        features: EngineeredFeatureSnapshot,
    ) -> MarketSignalSummary:
        upside = ((point_forecast / current_price) - 1.0) if current_price else 0.0
        range_width = ((forecast_range[1] - forecast_range[0]) / point_forecast) if point_forecast else 0.0
        score = (
            upside * 45.0
            + features.momentum_20d * 25.0
            + features.price_vs_ma20_pct * 20.0
            - features.realized_volatility_20d * 18.0
        )
        score = max(-1.0, min(1.0, score))

        confidence = 0.5
        confidence += 0.18 if abs(upside) >= 0.015 else -0.05
        confidence += 0.12 if abs(features.momentum_20d) >= 0.02 else 0.0
        confidence += 0.10 if range_width <= 0.08 else -0.12
        confidence += 0.05 if features.realized_volatility_20d <= 0.015 else -0.05
        confidence = max(0.05, min(0.95, confidence))

        thresholds: list[str] = []
        if upside >= 0.015:
            thresholds.append("forecast_upside>=1.5%")
        elif upside <= -0.015:
            thresholds.append("forecast_downside<=-1.5%")
        if features.momentum_20d >= 0.02:
            thresholds.append("momentum_20d>=2%")
        elif features.momentum_20d <= -0.02:
            thresholds.append("momentum_20d<=-2%")
        if features.realized_volatility_20d >= 0.02:
            thresholds.append("volatility_20d>=2%")

        if score >= 0.2:
            label = "bullish"
            scenario = "bull"
        elif score <= -0.2:
            label = "bearish"
            scenario = "bear"
        elif confidence < 0.45 or range_width > 0.12:
            label = "cautious"
            scenario = "base"
        else:
            label = "neutral"
            scenario = "base"

        rationale_parts = [
            f"forecast spread {upside * 100:.2f}%",
            f"20d momentum {features.momentum_20d * 100:.2f}%",
            f"20d realized vol {features.realized_volatility_20d * 100:.2f}%",
        ]
        if features.fx_volatility is not None:
            rationale_parts.append(f"fx proxy vol {features.fx_volatility * 100:.2f}%")

        return MarketSignalSummary(
            label=label,
            score=round(score, 4),
            confidence=round(confidence, 4),
            scenario=scenario,
            rationale=", ".join(rationale_parts),
            thresholds_applied=thresholds,
        )

    def build_response(
        self,
        *,
        commodity: str,
        region: str,
        horizon_days: int,
        current_price: float,
        point_forecast: float,
        forecast_range: tuple[float, float],
        scenario_forecasts: dict[str, float],
        features: EngineeredFeatureSnapshot,
        provenance: list[DataProvenance],
    ) -> MarketSignalResponse:
        return MarketSignalResponse(
            commodity=commodity,
            region=region,
            horizon_days=horizon_days,
            live_price=round(float(current_price), 4),
            forecast_point=round(float(point_forecast), 4),
            forecast_range=(round(float(forecast_range[0]), 4), round(float(forecast_range[1]), 4)),
            scenario_forecasts={k: round(float(v), 4) for k, v in scenario_forecasts.items()},
            signal=self.summarize(
                current_price=current_price,
                point_forecast=point_forecast,
                forecast_range=forecast_range,
                features=features,
            ),
            features=features,
            provenance=provenance,
        )
