from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.schema_guard import ensure_ingestion_schema, ensure_training_runs_schema


def test_schema_guard_adds_region_and_unique_index(tmp_path: Path) -> None:
    db_path = tmp_path / "schema_guard.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async def _run() -> None:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE TABLE training_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        commodity VARCHAR(32) NOT NULL,
                        model_name VARCHAR(64) NOT NULL,
                        model_version VARCHAR(64) NOT NULL,
                        rmse FLOAT NOT NULL,
                        mape FLOAT NOT NULL,
                        artifact_path VARCHAR(255) NOT NULL,
                        trained_at DATETIME NOT NULL
                    )
                    """
                )
            )
            await ensure_training_runs_schema(conn)
            cols = (await conn.execute(text("PRAGMA table_info(training_runs)"))).all()
            names = {str(c[1]) for c in cols}
            assert "region" in names
            trained_at = next(c for c in cols if str(c[1]) == "trained_at")
            assert "DATE" in str(trained_at[2]).upper() or "TIME" in str(trained_at[2]).upper()
            region_col = next(c for c in cols if str(c[1]) == "region")
            assert int(region_col[3]) == 1  # not null

            indexes = (await conn.execute(text("PRAGMA index_list(training_runs)"))).all()
            idx_names = {str(i[1]) for i in indexes}
            assert "uq_training_runs_model_version" in idx_names

    asyncio.run(_run())


def test_schema_guard_skips_unique_when_duplicates_exist(tmp_path: Path) -> None:
    db_path = tmp_path / "schema_guard_dup.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async def _run() -> None:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE TABLE training_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        commodity VARCHAR(32) NOT NULL,
                        model_name VARCHAR(64) NOT NULL,
                        model_version VARCHAR(64) NOT NULL,
                        rmse FLOAT NOT NULL,
                        mape FLOAT NOT NULL,
                        artifact_path VARCHAR(255) NOT NULL,
                        trained_at DATETIME NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO training_runs "
                    "(commodity, model_name, model_version, rmse, mape, artifact_path, trained_at) "
                    "VALUES "
                    "('gold', 'xgb', 'dup_v1', 1.0, 1.0, 'a.joblib', '2026-02-28 12:21:36'), "
                    "('silver', 'xgb', 'dup_v1', 1.0, 1.0, 'b.joblib', '2026-02-28 12:21:37')"
                )
            )
            await ensure_training_runs_schema(conn)
            indexes = (await conn.execute(text("PRAGMA index_list(training_runs)"))).all()
            idx_names = {str(i[1]) for i in indexes}
            assert "uq_training_runs_model_version" not in idx_names

    asyncio.run(_run())


def test_schema_guard_adds_ingestion_indexes(tmp_path: Path) -> None:
    db_path = tmp_path / "schema_guard_ingestion.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async def _run() -> None:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE TABLE ingestion_jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        commodity VARCHAR(32),
                        region VARCHAR(16),
                        job_type VARCHAR(32) NOT NULL,
                        status VARCHAR(16) NOT NULL,
                        created_at DATETIME NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE normalized_market_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        record_type VARCHAR(16) NOT NULL,
                        commodity VARCHAR(32) NOT NULL,
                        region VARCHAR(16) NOT NULL,
                        period VARCHAR(16),
                        observed_at DATETIME NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE macro_metric_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_key VARCHAR(64) NOT NULL,
                        observed_at DATETIME NOT NULL,
                        value FLOAT NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE news_headline_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        commodity VARCHAR(32) NOT NULL,
                        published_at DATETIME NOT NULL,
                        dedupe_key VARCHAR(64) NOT NULL
                    )
                    """
                )
            )
            await ensure_ingestion_schema(conn)
            ingestion_indexes = (await conn.execute(text("PRAGMA index_list(ingestion_jobs)"))).all()
            normalized_indexes = (await conn.execute(text("PRAGMA index_list(normalized_market_records)"))).all()
            macro_indexes = (await conn.execute(text("PRAGMA index_list(macro_metric_records)"))).all()
            news_indexes = (await conn.execute(text("PRAGMA index_list(news_headline_records)"))).all()
            assert "idx_ingestion_jobs_status" in {str(i[1]) for i in ingestion_indexes}
            assert "idx_ingestion_jobs_lookup" in {str(i[1]) for i in ingestion_indexes}
            assert "idx_normalized_market_records_lookup" in {str(i[1]) for i in normalized_indexes}
            assert "idx_macro_metric_records_dedupe" in {str(i[1]) for i in macro_indexes}
            assert "idx_news_headline_records_dedupe" in {str(i[1]) for i in news_indexes}
            assert "idx_news_headline_records_lookup" in {str(i[1]) for i in news_indexes}

    asyncio.run(_run())
