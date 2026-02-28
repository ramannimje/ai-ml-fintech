from __future__ import annotations

import logging
from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS: dict[str, tuple[str, bool]] = {
    "commodity": ("VARCHAR", True),
    "region": ("VARCHAR", True),
    "model_name": ("VARCHAR", True),
    "model_version": ("VARCHAR", True),
    "rmse": ("FLOAT", True),
    "mape": ("FLOAT", True),
    "artifact_path": ("VARCHAR", True),
    "trained_at": ("DATETIME", True),
}


async def _sqlite_columns(conn: AsyncConnection, table_name: str) -> dict[str, dict[str, object]]:
    rows = (await conn.execute(text(f"PRAGMA table_info({table_name})"))).all()
    return {
        str(row[1]): {"type": str(row[2]).upper(), "notnull": bool(row[3])}
        for row in rows
    }


async def _sqlite_indexes(conn: AsyncConnection, table_name: str) -> dict[str, dict[str, object]]:
    indexes = (await conn.execute(text(f"PRAGMA index_list({table_name})"))).all()
    out: dict[str, dict[str, object]] = {}
    for idx in indexes:
        name = str(idx[1])
        unique = bool(idx[2])
        cols = (await conn.execute(text(f"PRAGMA index_info({name})"))).all()
        out[name] = {"unique": unique, "columns": [str(c[2]) for c in cols]}
    return out


async def _has_duplicate_model_versions(conn: AsyncConnection) -> bool:
    rows = (
        await conn.execute(
            text(
                "SELECT model_version, COUNT(*) c "
                "FROM training_runs "
                "GROUP BY model_version "
                "HAVING COUNT(*) > 1 "
                "LIMIT 1"
            )
        )
    ).all()
    return bool(rows)


def _compatible_type(actual: str, expected_prefix: str) -> bool:
    if expected_prefix == "DATETIME":
        return "DATE" in actual or "TIME" in actual
    return actual.startswith(expected_prefix)


def _missing_columns(current: Iterable[str]) -> list[str]:
    return [c for c in REQUIRED_COLUMNS if c not in current]


async def ensure_training_runs_schema(conn: AsyncConnection) -> None:
    """
    Validate and repair `training_runs` for older SQLite files.
    Fixes:
    - add missing `region` column (NOT NULL DEFAULT 'us')
    - add unique index for model_version when safe
    """
    dialect = conn.engine.dialect.name
    if dialect != "sqlite":
        return

    table_exists = (
        await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='training_runs'")
        )
    ).first()
    if not table_exists:
        return

    columns = await _sqlite_columns(conn, "training_runs")
    missing = _missing_columns(columns.keys())
    if "region" in missing:
        logger.warning("schema_repair: adding missing column training_runs.region")
        await conn.execute(
            text("ALTER TABLE training_runs ADD COLUMN region VARCHAR(16) NOT NULL DEFAULT 'us'")
        )
        columns = await _sqlite_columns(conn, "training_runs")
        missing = _missing_columns(columns.keys())

    if missing:
        logger.error("schema_check: training_runs missing required columns=%s", ",".join(missing))

    for name, (expected_type, expected_notnull) in REQUIRED_COLUMNS.items():
        col = columns.get(name)
        if not col:
            continue
        actual_type = str(col["type"])
        if not _compatible_type(actual_type, expected_type):
            logger.warning(
                "schema_check: unexpected type training_runs.%s=%s expected_prefix=%s",
                name,
                actual_type,
                expected_type,
            )
        if expected_notnull and not bool(col["notnull"]):
            logger.warning("schema_check: nullable column found training_runs.%s", name)

    indexes = await _sqlite_indexes(conn, "training_runs")
    unique_on_model_version = any(
        bool(info["unique"]) and list(info["columns"]) == ["model_version"] for info in indexes.values()
    )
    if not unique_on_model_version:
        if await _has_duplicate_model_versions(conn):
            logger.warning("schema_check: skipped unique index creation for model_version (duplicates exist)")
        else:
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "uq_training_runs_model_version ON training_runs(model_version)"
                )
            )
            logger.info("schema_repair: created unique index uq_training_runs_model_version")
