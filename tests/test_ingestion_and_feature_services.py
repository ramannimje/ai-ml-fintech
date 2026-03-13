from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models import ingestion_job as ingestion_job_model  # noqa: F401
from app.models import normalized_market_record as normalized_market_record_model  # noqa: F401
from app.models import raw_market_payload as raw_market_payload_model  # noqa: F401
from app.schemas.market_data import (
    MarketDataProvenanceRecord,
    NormalizedHistoricalBar,
    NormalizedHistoricalSeries,
    NormalizedLiveQuote,
)
from app.services.feature_store_service import FeatureStoreService
from app.services.commodity_service import CommodityService
from app.services.ingestion_service import MarketIngestionService
from app.services.ingestion_persistence_service import IngestionPersistenceService
from app.services.ingestion_replay_service import IngestionReplayService
from app.services.macro_persistence_service import MacroPersistenceService
from app.services.news_persistence_service import NewsPersistenceService
from app.schemas.responses import NewsHeadline
from ml.data.data_fetcher import MarketDataFetcher


class _StaticProvider:
    def __init__(self, provider_name: str, fallback_level: int, quotes: dict[str, float]) -> None:
        self.provider_name = provider_name
        self.fallback_level = fallback_level
        self._quotes = quotes

    async def fetch(self, commodities: list[str]) -> dict[str, NormalizedLiveQuote]:
        now = datetime.now(timezone.utc)
        return {
            commodity: NormalizedLiveQuote(
                commodity=commodity,
                price_usd_per_troy_oz=price,
                observed_at=now,
                provenance=MarketDataProvenanceRecord(
                    source_type="live",
                    provider=self.provider_name,
                    detail=f"{self.provider_name}:{commodity}",
                    observed_at=now,
                    ingested_at=now,
                    fallback_level=self.fallback_level,
                ),
            )
            for commodity, price in self._quotes.items()
            if commodity in commodities
        }


def test_market_ingestion_service_preserves_provider_order(tmp_path) -> None:
    fetcher = MarketDataFetcher(cache_dir=str(tmp_path))
    service = MarketIngestionService(
        fetcher=fetcher,
        live_quote_providers=[
            _StaticProvider("primary", 0, {"gold": 2300.0}),
            _StaticProvider("secondary", 1, {"gold": 2299.0, "silver": 25.0}),
            _StaticProvider("tertiary", 2, {"crude_oil": 81.0}),
        ],
    )

    quotes = asyncio.run(service.fetch_live_quotes(["gold", "silver", "crude_oil"]))

    assert quotes["gold"].price_usd_per_troy_oz == 2300.0
    assert quotes["gold"].provenance.provider == "primary"
    assert quotes["silver"].provenance.fallback_level == 1
    assert quotes["crude_oil"].provenance.provider == "tertiary"


def test_feature_store_materialization_and_snapshot() -> None:
    service = FeatureStoreService()
    series = NormalizedHistoricalSeries(
        commodity="gold",
        region="india",
        provenance=MarketDataProvenanceRecord(source_type="historical", provider="cache"),
        bars=[
            NormalizedHistoricalBar(
                date=date(2026, 1, min(day, 28)),
                open_usd_per_troy_oz=2200.0 + day,
                high_usd_per_troy_oz=2205.0 + day,
                low_usd_per_troy_oz=2195.0 + day,
                close_usd_per_troy_oz=2200.0 + day,
                volume=1000.0 + day,
            )
            for day in range(1, 61)
        ],
    )

    enriched = service.materialize_online_features(series=series, region="india", fx={"USD": 1.0, "INR": 83.2, "EUR": 0.92})
    closes = [bar.close_usd_per_troy_oz for bar in series.bars]
    snapshot = service.build_feature_snapshot(closes=closes, enriched=enriched)

    assert not enriched.empty
    assert "fx_rate" in enriched.columns
    assert float(enriched["fx_rate"].iloc[-1]) == 83.2
    assert snapshot.calendar_month == 1
    assert snapshot.fx_rate == 83.2
    assert snapshot.momentum_20d > 0


def test_feature_store_materialization_uses_persisted_macro_and_news_inputs() -> None:
    service = FeatureStoreService()
    series = NormalizedHistoricalSeries(
        commodity="gold",
        region="us",
        provenance=MarketDataProvenanceRecord(source_type="historical", provider="cache"),
        bars=[
            NormalizedHistoricalBar(
                date=date(2026, 1, min(day, 28)),
                open_usd_per_troy_oz=2200.0 + day,
                high_usd_per_troy_oz=2205.0 + day,
                low_usd_per_troy_oz=2195.0 + day,
                close_usd_per_troy_oz=2200.0 + day,
                volume=1000.0 + day,
            )
            for day in range(1, 61)
        ],
    )
    macro_frame = pd.DataFrame(
        {
            "dxy": [101.0, 102.0, 103.0],
            "treasury_10y": [4.1, 4.2, 4.3],
        },
        index=pd.to_datetime(["2026-01-10", "2026-01-20", "2026-01-28"]),
    )
    news_frame = pd.DataFrame(
        {
            "news_headline_count": [2, 3],
            "news_sentiment_score": [1.0, -1.0],
        },
        index=pd.to_datetime(["2026-01-15", "2026-01-28"]),
    )

    enriched = service.materialize_online_features(
        series=series,
        region="us",
        macro_frame=macro_frame,
        news_frame=news_frame,
    )

    assert "dxy" in enriched.columns
    assert "news_headline_count" in enriched.columns
    assert float(enriched["interest_rates_fred_ecb_rbi"].iloc[-1]) == 4.3
    assert float(enriched["news_sentiment_score"].iloc[-1]) == -1.0


def test_load_historical_series_returns_normalized_contract(tmp_path) -> None:
    fetcher = MarketDataFetcher(cache_dir=str(tmp_path))
    frame = pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=3, freq="D"),
            "Open": [1.0, 2.0, 3.0],
            "High": [1.5, 2.5, 3.5],
            "Low": [0.5, 1.5, 2.5],
            "Close": [1.2, 2.2, 3.2],
            "Volume": [10.0, 11.0, 12.0],
        }
    )
    path = tmp_path / "gold_us.csv"
    frame.to_csv(path, index=False)

    service = MarketIngestionService(fetcher=fetcher)
    series = service.load_historical_series("gold", "us", period="1d")

    assert series.commodity == "gold"
    assert len(series.bars) == 2
    assert series.provenance.provider == "yahoo_finance/cache"
    assert series.bars[-1].close_usd_per_troy_oz == 3.2


def test_ingestion_persistence_service_writes_replay_safe_records(tmp_path: Path) -> None:
    db_path = tmp_path / "ingestion_persistence.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    persistence = IngestionPersistenceService()

    async def _run() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        quote_time = datetime(2026, 3, 12, 12, 0, tzinfo=timezone.utc)
        quotes = {
            "gold": NormalizedLiveQuote(
                commodity="gold",
                price_usd_per_troy_oz=2350.0,
                observed_at=quote_time,
                provenance=MarketDataProvenanceRecord(
                    source_type="live",
                    provider="metals.live",
                    detail="gold/us",
                    observed_at=quote_time,
                    ingested_at=quote_time,
                ),
            )
        }
        series = NormalizedHistoricalSeries(
            commodity="gold",
            region="us",
            provenance=MarketDataProvenanceRecord(
                source_type="historical",
                provider="cache",
                detail="gold/us",
                observed_at=quote_time,
                ingested_at=quote_time,
            ),
            bars=[
                NormalizedHistoricalBar(
                    date=date(2026, 3, 10),
                    open_usd_per_troy_oz=2200.0,
                    high_usd_per_troy_oz=2210.0,
                    low_usd_per_troy_oz=2190.0,
                    close_usd_per_troy_oz=2205.0,
                    volume=1000.0,
                )
            ],
        )

        async with session_factory() as session:
            job = await persistence.create_job(
                session,
                job_type="historical_backfill",
                commodity="gold",
                region="us",
                period="1y",
            )

        async with session_factory() as session:
            await persistence.mark_processing(session, job_id=job.id, message="Persisting market snapshots")
            await persistence.persist_live_quotes(session, quotes=quotes, region="us", job_id=job.id)
            await persistence.persist_historical_series(session, series=series, period="1y", job_id=job.id)
            await persistence.persist_live_quotes(session, quotes=quotes, region="us", job_id=job.id)
            await persistence.persist_historical_series(session, series=series, period="1y", job_id=job.id)
            await persistence.mark_completed(session, job_id=job.id, result_payload={"records": 2})

        async with session_factory() as session:
            records = (
                await session.execute(
                    select(normalized_market_record_model.NormalizedMarketRecord).order_by(
                        normalized_market_record_model.NormalizedMarketRecord.record_type.asc()
                    )
                )
            ).scalars().all()
            raw_payloads = (
                await session.execute(select(raw_market_payload_model.RawMarketPayload))
            ).scalars().all()
            jobs = (await session.execute(select(ingestion_job_model.IngestionJob))).scalars().all()

            assert len(records) == 2
            assert len(raw_payloads) == 4
            assert jobs[0].status == "completed"
            assert records[0].record_type in {"historical", "live"}

        await engine.dispose()

    asyncio.run(_run())


def test_ingestion_persistence_service_handles_duplicate_historical_dates_without_extra_records(tmp_path: Path) -> None:
    db_path = tmp_path / "ingestion_persistence_duplicate_dates.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    persistence = IngestionPersistenceService()

    async def _run() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        observed_at = datetime(2026, 3, 12, 12, 0, tzinfo=timezone.utc)
        series = NormalizedHistoricalSeries(
            commodity="crude_oil",
            region="us",
            provenance=MarketDataProvenanceRecord(
                source_type="historical",
                provider="cache",
                detail="crude_oil/us",
                observed_at=observed_at,
                ingested_at=observed_at,
                raw_symbol="CL=F",
            ),
            bars=[
                NormalizedHistoricalBar(
                    date=date(2026, 3, 10),
                    open_usd_per_troy_oz=70.0,
                    high_usd_per_troy_oz=71.0,
                    low_usd_per_troy_oz=69.0,
                    close_usd_per_troy_oz=70.5,
                    volume=1000.0,
                ),
                NormalizedHistoricalBar(
                    date=date(2026, 3, 10),
                    open_usd_per_troy_oz=70.0,
                    high_usd_per_troy_oz=71.0,
                    low_usd_per_troy_oz=69.0,
                    close_usd_per_troy_oz=70.5,
                    volume=1000.0,
                ),
            ],
        )

        async with session_factory() as session:
            first = await persistence.persist_historical_series(session, series=series, period="1m")
            second = await persistence.persist_historical_series(session, series=series, period="1m")
            records = (
                await session.execute(select(normalized_market_record_model.NormalizedMarketRecord))
            ).scalars().all()
            raw_payloads = (await session.execute(select(raw_market_payload_model.RawMarketPayload))).scalars().all()

            assert first["normalized_records_inserted"] == 1
            assert second["normalized_records_inserted"] == 0
            assert len(records) == 1
            assert len(raw_payloads) == 2

        await engine.dispose()

    asyncio.run(_run())


def test_macro_fetcher_skips_future_incremental_start(tmp_path: Path, monkeypatch) -> None:
    fetcher = MarketDataFetcher(cache_dir=str(tmp_path))
    for name, close in (("macro_dxy.csv", 103.8), ("macro_treasury_10y.csv", 4.2)):
        pd.DataFrame({"Date": [pd.Timestamp("2026-03-13")], "Close": [close]}).to_csv(tmp_path / name, index=False)

    import ml.data.data_fetcher as data_fetcher_module

    calls: list[tuple[object, object]] = []

    def _fake_download(symbol, period=None, start=None, auto_adjust=False, progress=False):  # noqa: ANN001
        _ = symbol, auto_adjust, progress
        calls.append((period, start))
        return pd.DataFrame()

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            base = datetime(2026, 3, 13, 0, 30, tzinfo=timezone.utc)
            if tz is None:
                return base.replace(tzinfo=None)
            return base.astimezone(tz)

    monkeypatch.setattr(data_fetcher_module.yf, "download", _fake_download)
    monkeypatch.setattr(data_fetcher_module, "datetime", _FrozenDatetime)

    frame = fetcher.get_macro_features(period="1y")

    assert not frame.empty
    assert calls == []


def test_commodity_service_historical_persists_without_lock_for_all_regions(tmp_path: Path) -> None:
    db_path = tmp_path / "commodity_historical_regions.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    service = CommodityService()

    def _series_for(region: str) -> NormalizedHistoricalSeries:
        return NormalizedHistoricalSeries(
            commodity="crude_oil",
            region=region,
            provenance=MarketDataProvenanceRecord(
                source_type="historical",
                provider="cache",
                detail=f"crude_oil/{region}",
                observed_at=datetime(2026, 3, 12, 0, 0, tzinfo=timezone.utc),
                ingested_at=datetime(2026, 3, 12, 0, 5, tzinfo=timezone.utc),
                raw_symbol="CL=F",
            ),
            bars=[
                NormalizedHistoricalBar(
                    date=date(2026, 3, 10),
                    open_usd_per_troy_oz=70.0,
                    high_usd_per_troy_oz=71.0,
                    low_usd_per_troy_oz=69.0,
                    close_usd_per_troy_oz=70.5,
                    volume=1000.0,
                ),
                NormalizedHistoricalBar(
                    date=date(2026, 3, 11),
                    open_usd_per_troy_oz=71.0,
                    high_usd_per_troy_oz=72.0,
                    low_usd_per_troy_oz=70.0,
                    close_usd_per_troy_oz=71.5,
                    volume=1100.0,
                ),
            ],
        )

    async def _run() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        for region in ("india", "us", "europe"):
            service.ingestion_service.load_historical_series = lambda commodity, region=region, period="1m": _series_for(region)
            async with session_factory() as session:
                response = await service.historical("crude_oil", region=region, period="1m", session=session)
                assert response.region == region
                assert response.rows == 2

        async with session_factory() as session:
            rows = (
                await session.execute(select(normalized_market_record_model.NormalizedMarketRecord))
            ).scalars().all()
            assert len(rows) == 6

        await engine.dispose()

    asyncio.run(_run())


def test_ingestion_replay_service_runs_backfill_jobs_safely(tmp_path: Path) -> None:
    db_path = tmp_path / "ingestion_replay.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    fetcher = MarketDataFetcher(cache_dir=str(tmp_path))
    persistence = IngestionPersistenceService()
    replay_service = IngestionReplayService(
        ingestion_service=MarketIngestionService(fetcher=fetcher),
        persistence_service=persistence,
    )

    series = NormalizedHistoricalSeries(
        commodity="gold",
        region="us",
        provenance=MarketDataProvenanceRecord(
            source_type="historical",
            provider="cache",
            detail="gold/us",
            observed_at=datetime(2026, 3, 12, 12, 0, tzinfo=timezone.utc),
            ingested_at=datetime(2026, 3, 12, 12, 5, tzinfo=timezone.utc),
        ),
        bars=[
            NormalizedHistoricalBar(
                date=date(2026, 3, 10),
                open_usd_per_troy_oz=2200.0,
                high_usd_per_troy_oz=2210.0,
                low_usd_per_troy_oz=2190.0,
                close_usd_per_troy_oz=2205.0,
                volume=1000.0,
            )
        ],
    )
    replay_service.ingestion_service.load_historical_series = lambda commodity, region, period: series

    async def _run() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            first_job = await replay_service.create_historical_backfill_job(
                session,
                commodity="gold",
                region="us",
                period="1y",
            )
            queued_status = await replay_service.get_job_status(session, job_id=first_job.id)
            assert queued_status is not None
            assert queued_status["status"] == "queued"

        async with session_factory() as session:
            completed_status = await replay_service.run_job(session, job_id=first_job.id)
            assert completed_status["status"] == "completed"
            assert completed_status["result"]["normalized_records_inserted"] == 1

        async with session_factory() as session:
            second_job = await replay_service.create_historical_backfill_job(
                session,
                commodity="gold",
                region="us",
                period="1y",
            )

        async with session_factory() as session:
            second_status = await replay_service.run_job(session, job_id=second_job.id)
            assert second_status["status"] == "completed"
            assert second_status["result"]["normalized_records_inserted"] == 0
            assert second_status["result"]["normalized_records_written"] == 1

        async with session_factory() as session:
            records = (
                await session.execute(select(normalized_market_record_model.NormalizedMarketRecord))
            ).scalars().all()
            raw_payloads = (
                await session.execute(select(raw_market_payload_model.RawMarketPayload))
            ).scalars().all()
            jobs = (await session.execute(select(ingestion_job_model.IngestionJob))).scalars().all()

            assert len(records) == 1
            assert len(raw_payloads) == 2
            assert [job.status for job in jobs] == ["completed", "completed"]

        await engine.dispose()

    asyncio.run(_run())


def test_macro_and_news_persistence_services_are_replay_safe(tmp_path: Path) -> None:
    db_path = tmp_path / "macro_news_persistence.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    fetcher = MarketDataFetcher(cache_dir=str(tmp_path))
    macro_service = MacroPersistenceService(fetcher)
    news_service = NewsPersistenceService()

    async def _run() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        fetcher.get_macro_features = lambda period="1y": pd.DataFrame(
            {
                "dxy": [101.0, 102.0, 102.5],
                "treasury_10y": [4.1, 4.2, 4.25],
            },
            index=pd.to_datetime(["2026-03-10", "2026-03-11", "2026-03-11"]),
        )
        headlines = [
            NewsHeadline(
                title="Gold rises on softer dollar",
                source="Test Feed",
                url="https://example.com/gold-1",
                published_at=datetime(2026, 3, 11, 12, 0, tzinfo=timezone.utc),
            ),
            NewsHeadline(
                title="Gold rises on softer dollar",
                source="Test Feed",
                url="https://example.com/gold-1",
                published_at=datetime(2026, 3, 11, 12, 0, tzinfo=timezone.utc),
            ),
        ]

        async with session_factory() as session:
            first_macro = await macro_service.ingest_macro_series(session, period="1y")
            second_macro = await macro_service.ingest_macro_series(session, period="1y")
            first_news = await news_service.ingest_headlines(session, commodity="gold", headlines=headlines)
            second_news = await news_service.ingest_headlines(session, commodity="gold", headlines=headlines)
            macro_loaded = await macro_service.load_macro_frame(session)
            news_loaded = await news_service.get_recent_headlines(session, commodity="gold", limit=6)
            news_features = await news_service.build_news_feature_frame(session, commodity="gold")

            assert first_macro["rows_inserted"] == 4
            assert second_macro["rows_inserted"] == 0
            assert first_news["rows_inserted"] == 1
            assert second_news["rows_inserted"] == 0
            assert list(macro_loaded.columns) == ["dxy", "treasury_10y"]
            assert len(news_loaded) == 1
            assert float(news_features["news_headline_count"].iloc[-1]) == 1.0

        await engine.dispose()

    asyncio.run(_run())
