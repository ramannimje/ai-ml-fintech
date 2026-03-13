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


async def ensure_vector_extension(conn: AsyncConnection) -> None:
    """Ensure pgvector extension is enabled for PostgreSQL dialects."""
    dialect = conn.engine.dialect.name
    if dialect == "postgresql":
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logger.info("schema_check: pgvector extension verified")


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


async def ensure_ingestion_schema(conn: AsyncConnection) -> None:
    """
    Validate ingestion persistence tables for SQLite files.
    Fixes:
    - ensure replay-safe lookup indexes exist on normalized market records
    - ensure job status index exists for ingestion jobs
    """
    dialect = conn.engine.dialect.name
    if dialect != "sqlite":
        return

    normalized_exists = (
        await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='normalized_market_records'")
        )
    ).first()
    if normalized_exists:
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_normalized_market_records_lookup "
                "ON normalized_market_records(record_type, commodity, region, period, observed_at)"
            )
        )

    jobs_exists = (
        await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='ingestion_jobs'")
        )
    ).first()
    if jobs_exists:
        job_columns = await _sqlite_columns(conn, "ingestion_jobs")
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON ingestion_jobs(status, created_at)")
        )
        if {"job_type", "commodity", "region", "created_at"}.issubset(job_columns):
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_lookup "
                    "ON ingestion_jobs(job_type, commodity, region, created_at)"
                )
            )

    macro_exists = (
        await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='macro_metric_records'")
        )
    ).first()
    if macro_exists:
        macro_columns = await _sqlite_columns(conn, "macro_metric_records")
        if {"metric_key", "observed_at"}.issubset(macro_columns):
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_macro_metric_records_dedupe "
                    "ON macro_metric_records(metric_key, observed_at)"
                )
            )

    news_exists = (
        await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='news_headline_records'")
        )
    ).first()
    if news_exists:
        news_columns = await _sqlite_columns(conn, "news_headline_records")
        if {"dedupe_key"}.issubset(news_columns):
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_news_headline_records_dedupe "
                    "ON news_headline_records(dedupe_key)"
                )
            )
        if {"commodity", "published_at"}.issubset(news_columns):
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_news_headline_records_lookup "
                    "ON news_headline_records(commodity, published_at)"
                )
            )


async def ensure_alerts_schema(conn: AsyncConnection) -> None:
    """
    Validate and repair alert tables for older SQLite files.
    Fixes:
    - add missing cooldown/email settings columns on `price_alerts`
    - add delivery tracking columns on `alert_history`
    """
    dialect = conn.engine.dialect.name
    if dialect != "sqlite":
        return

    price_alerts_exists = (
        await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='price_alerts'")
        )
    ).first()
    if price_alerts_exists:
        columns = await _sqlite_columns(conn, "price_alerts")
        if "user_id" not in columns:
            logger.warning("schema_repair: adding missing column price_alerts.user_id")
            await conn.execute(
                text("ALTER TABLE price_alerts ADD COLUMN user_id VARCHAR(128) NOT NULL DEFAULT ''")
            )
            await conn.execute(text("UPDATE price_alerts SET user_id = user_sub WHERE user_id = ''"))
        if "target_price" not in columns:
            logger.warning("schema_repair: adding missing column price_alerts.target_price")
            await conn.execute(
                text("ALTER TABLE price_alerts ADD COLUMN target_price FLOAT NOT NULL DEFAULT 0")
            )
            await conn.execute(text("UPDATE price_alerts SET target_price = threshold WHERE target_price = 0"))
        if "direction" not in columns:
            logger.warning("schema_repair: adding missing column price_alerts.direction")
            await conn.execute(text("ALTER TABLE price_alerts ADD COLUMN direction VARCHAR(16)"))
            await conn.execute(
                text(
                    "UPDATE price_alerts SET direction = alert_type "
                    "WHERE direction IS NULL AND alert_type IN ('above','below')"
                )
            )
        if "whatsapp_number" not in columns:
            logger.warning("schema_repair: adding missing column price_alerts.whatsapp_number")
            await conn.execute(text("ALTER TABLE price_alerts ADD COLUMN whatsapp_number VARCHAR(32)"))
        if "is_active" not in columns:
            logger.warning("schema_repair: adding missing column price_alerts.is_active")
            await conn.execute(
                text("ALTER TABLE price_alerts ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")
            )
            await conn.execute(text("UPDATE price_alerts SET is_active = enabled"))
        if "is_triggered" not in columns:
            logger.warning("schema_repair: adding missing column price_alerts.is_triggered")
            await conn.execute(
                text("ALTER TABLE price_alerts ADD COLUMN is_triggered BOOLEAN NOT NULL DEFAULT 0")
            )
        if "triggered_at" not in columns:
            logger.warning("schema_repair: adding missing column price_alerts.triggered_at")
            await conn.execute(text("ALTER TABLE price_alerts ADD COLUMN triggered_at DATETIME"))
        if "cooldown_minutes" not in columns:
            logger.warning("schema_repair: adding missing column price_alerts.cooldown_minutes")
            await conn.execute(
                text("ALTER TABLE price_alerts ADD COLUMN cooldown_minutes INTEGER NOT NULL DEFAULT 30")
            )
        if "email_notifications_enabled" not in columns:
            logger.warning("schema_repair: adding missing column price_alerts.email_notifications_enabled")
            await conn.execute(
                text("ALTER TABLE price_alerts ADD COLUMN email_notifications_enabled BOOLEAN NOT NULL DEFAULT 1")
            )

    history_exists = (
        await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='alert_history'")
        )
    ).first()
    if history_exists:
        columns = await _sqlite_columns(conn, "alert_history")
        if "delivery_provider" not in columns:
            logger.warning("schema_repair: adding missing column alert_history.delivery_provider")
            await conn.execute(text("ALTER TABLE alert_history ADD COLUMN delivery_provider VARCHAR(32)"))
        if "delivery_error" not in columns:
            logger.warning("schema_repair: adding missing column alert_history.delivery_error")
            await conn.execute(text("ALTER TABLE alert_history ADD COLUMN delivery_error VARCHAR(512)"))
        if "delivery_attempts" not in columns:
            logger.warning("schema_repair: adding missing column alert_history.delivery_attempts")
            await conn.execute(
                text("ALTER TABLE alert_history ADD COLUMN delivery_attempts INTEGER NOT NULL DEFAULT 0")
            )
