from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.schema_guard import ensure_training_runs_schema


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
