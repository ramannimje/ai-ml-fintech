from __future__ import annotations

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.market_data import NormalizedHistoricalSeries
from app.schemas.responses import EngineeredFeatureSnapshot
from app.services.fx_cache import get_fx_rates
from app.services.macro_persistence_service import MacroPersistenceService
from app.services.news_persistence_service import NewsPersistenceService
from ml.data.data_fetcher import MarketDataFetcher
from ml.features.engineer import add_features


class FeatureStoreService:
    def __init__(self, fetcher: MarketDataFetcher | None = None) -> None:
        self.fetcher = fetcher
        self.macro_persistence_service = MacroPersistenceService(fetcher) if fetcher is not None else None
        self.news_persistence_service = NewsPersistenceService() if fetcher is not None else None

    def materialize_from_frame(
        self,
        raw: pd.DataFrame,
        region: str,
        fx: dict[str, float] | None = None,
        macro_frame: pd.DataFrame | None = None,
        news_frame: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        if raw.empty:
            return raw

        feat = add_features(raw)
        feat["Date"] = pd.to_datetime(feat["Date"])
        rates = fx or get_fx_rates()
        inr = rates.get("INR")
        eur = rates.get("EUR")
        if region == "india" and inr:
            fx_series = pd.Series(inr, index=feat.index)
        elif region == "europe" and eur:
            fx_series = pd.Series(eur, index=feat.index)
        else:
            fx_series = pd.Series(1.0, index=feat.index)

        feat["fx_rate"] = fx_series
        feat["fx_volatility"] = fx_series.pct_change().rolling(10, min_periods=2).std().fillna(0.0)
        feat = self._apply_macro_features(feat, macro_frame)
        feat = self._apply_news_features(feat, news_frame)
        return feat

    def materialize_online_features(
        self,
        series: NormalizedHistoricalSeries,
        region: str,
        fx: dict[str, float] | None = None,
        macro_frame: pd.DataFrame | None = None,
        news_frame: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        raw = pd.DataFrame(
            [
                {
                    "Date": pd.Timestamp(bar.date),
                    "Open": bar.open_usd_per_troy_oz,
                    "High": bar.high_usd_per_troy_oz,
                    "Low": bar.low_usd_per_troy_oz,
                    "Close": bar.close_usd_per_troy_oz,
                    "Volume": bar.volume,
                }
                for bar in series.bars
            ]
        )
        return self.materialize_from_frame(
            raw=raw,
            region=region,
            fx=fx,
            macro_frame=macro_frame,
            news_frame=news_frame,
        )

    async def materialize_online_features_for_session(
        self,
        session: AsyncSession | None,
        *,
        commodity: str,
        series: NormalizedHistoricalSeries,
        region: str,
        period: str = "1y",
        fx: dict[str, float] | None = None,
    ) -> pd.DataFrame:
        if session is None or self.fetcher is None or self.macro_persistence_service is None:
            return self.materialize_online_features(series=series, region=region, fx=fx)

        macro_frame = await self.macro_persistence_service.get_or_ingest_macro_frame(session, period=period)
        news_frame = pd.DataFrame()
        if self.news_persistence_service is not None:
            news_frame = await self.news_persistence_service.build_news_feature_frame(session, commodity=commodity)
        return self.materialize_online_features(
            series=series,
            region=region,
            fx=fx,
            macro_frame=macro_frame,
            news_frame=news_frame,
        )

    def build_feature_snapshot(
        self,
        closes: list[float],
        enriched: pd.DataFrame,
    ) -> EngineeredFeatureSnapshot:
        returns = pd.Series(closes).pct_change().dropna()
        returns_1d = float(returns.iloc[-1]) if len(returns) >= 1 else 0.0
        returns_5d = float((closes[-1] / closes[-6]) - 1.0) if len(closes) >= 6 and closes[-6] else 0.0
        returns_20d = float((closes[-1] / closes[-21]) - 1.0) if len(closes) >= 21 and closes[-21] else 0.0
        realized_vol = float(returns.tail(20).std() or 0.0)
        window20 = closes[-20:] if len(closes) >= 20 else closes
        ma20 = sum(window20) / len(window20) if window20 else 0.0
        max20 = max(window20) if window20 else 0.0
        last_close = closes[-1] if closes else 0.0

        latest_row = enriched.iloc[-1] if not enriched.empty else pd.Series(dtype=float)
        latest_date = pd.to_datetime(latest_row.get("Date")) if "Date" in latest_row else pd.Timestamp.utcnow()

        return EngineeredFeatureSnapshot(
            returns_1d=round(returns_1d, 6),
            returns_5d=round(returns_5d, 6),
            returns_20d=round(returns_20d, 6),
            realized_volatility_20d=round(realized_vol, 6),
            momentum_20d=round(returns_20d, 6),
            price_vs_ma20_pct=round(((last_close / ma20) - 1.0) if ma20 else 0.0, 6),
            drawdown_20d_pct=round(((last_close / max20) - 1.0) if max20 else 0.0, 6),
            fx_rate=self._maybe_float(latest_row.get("fx_rate")),
            fx_volatility=self._maybe_float(latest_row.get("fx_volatility")),
            inflation_proxy=self._maybe_float(latest_row.get("inflation_proxy")),
            rate_proxy=self._maybe_float(latest_row.get("interest_rates_fred_ecb_rbi")),
            calendar_month=int(latest_date.month),
        )

    @staticmethod
    def _maybe_float(value: object) -> float | None:
        if value is None:
            return None
        try:
            out = float(value)
        except Exception:
            return None
        if pd.isna(out):
            return None
        return round(out, 6)

    @staticmethod
    def _apply_macro_features(feat: pd.DataFrame, macro_frame: pd.DataFrame | None) -> pd.DataFrame:
        if macro_frame is None or macro_frame.empty or feat.empty:
            feat["inflation_proxy"] = feat["returns"].rolling(30, min_periods=5).mean().fillna(0.0)
            feat["interest_rates_fred_ecb_rbi"] = feat["returns"].rolling(60, min_periods=10).std().fillna(0.0)
            return feat

        macro = macro_frame.copy().sort_index().reset_index().rename(columns={"index": "Date"})
        macro["Date"] = pd.to_datetime(macro["Date"]).astype("datetime64[ns]")
        feat = feat.copy()
        feat["Date"] = pd.to_datetime(feat["Date"]).astype("datetime64[ns]")
        out = pd.merge_asof(
            feat.sort_values("Date"),
            macro.sort_values("Date"),
            on="Date",
            direction="backward",
        )
        dxy = pd.to_numeric(out.get("dxy"), errors="coerce")
        treasury = pd.to_numeric(out.get("treasury_10y"), errors="coerce")
        out["inflation_proxy"] = dxy.pct_change().rolling(30, min_periods=2).mean().fillna(0.0)
        out["interest_rates_fred_ecb_rbi"] = treasury.ffill().bfill().fillna(0.0)
        return out

    @staticmethod
    def _apply_news_features(feat: pd.DataFrame, news_frame: pd.DataFrame | None) -> pd.DataFrame:
        if news_frame is None or news_frame.empty or feat.empty:
            feat["news_headline_count"] = 0.0
            feat["news_sentiment_score"] = 0.0
            return feat

        news = news_frame.copy().sort_index().reset_index().rename(columns={"index": "Date"})
        news["Date"] = pd.to_datetime(news["Date"]).astype("datetime64[ns]")
        feat = feat.copy()
        feat["Date"] = pd.to_datetime(feat["Date"]).astype("datetime64[ns]")
        out = pd.merge_asof(
            feat.sort_values("Date"),
            news.sort_values("Date"),
            on="Date",
            direction="backward",
        )
        out["news_headline_count"] = pd.to_numeric(out.get("news_headline_count"), errors="coerce").fillna(0.0)
        out["news_sentiment_score"] = pd.to_numeric(out.get("news_sentiment_score"), errors="coerce").fillna(0.0)
        return out
