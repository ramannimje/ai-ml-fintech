from __future__ import annotations

from datetime import timezone
import hashlib

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news_headline_record import NewsHeadlineRecord
from app.schemas.responses import NewsHeadline
from app.services.news_service import CommodityNewsService


class NewsPersistenceService:
    def __init__(self, news_service: CommodityNewsService | None = None) -> None:
        self.news_service = news_service or CommodityNewsService()

    @staticmethod
    def dedupe_key(commodity: str, headline: NewsHeadline) -> str:
        published = headline.published_at.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        base = "|".join(
            [
                commodity.strip().lower(),
                headline.title.strip().lower(),
                headline.source.strip().lower(),
                published,
            ]
        )
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    async def ingest_headlines(
        self,
        session: AsyncSession,
        *,
        commodity: str,
        headlines: list[NewsHeadline],
    ) -> dict[str, int]:
        unique_headlines = {
            self.dedupe_key(commodity, headline): (
                headline,
                self._normalize_published_at(headline.published_at),
            )
            for headline in headlines
        }
        if not unique_headlines:
            return {"rows_seen": 0, "rows_inserted": 0}

        existing_rows = (
            await session.execute(
                select(NewsHeadlineRecord).where(NewsHeadlineRecord.dedupe_key.in_(list(unique_headlines.keys())))
            )
        ).scalars().all()
        existing_keys = {row.dedupe_key for row in existing_rows}

        inserted = 0
        for dedupe_key, payload in unique_headlines.items():
            headline, published_at = payload
            if dedupe_key in existing_keys:
                continue
            session.add(
                NewsHeadlineRecord(
                    commodity=commodity,
                    title=headline.title,
                    source=headline.source,
                    url=headline.url or None,
                    published_at=published_at,
                    dedupe_key=dedupe_key,
                )
            )
            inserted += 1
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            inserted = 0
        return {"rows_seen": len(unique_headlines), "rows_inserted": inserted}

    async def get_recent_headlines(self, session: AsyncSession, *, commodity: str, limit: int = 6) -> list[NewsHeadline]:
        rows = (
            await session.execute(
                select(NewsHeadlineRecord)
                .where(NewsHeadlineRecord.commodity == commodity)
                .order_by(NewsHeadlineRecord.published_at.desc(), NewsHeadlineRecord.id.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [
            NewsHeadline(title=row.title, source=row.source, url=row.url or "", published_at=row.published_at)
            for row in rows
        ]

    async def get_or_ingest_recent_headlines(
        self,
        session: AsyncSession,
        *,
        commodity: str,
        limit: int = 6,
    ) -> list[NewsHeadline]:
        persisted = await self.get_recent_headlines(session, commodity=commodity, limit=limit)
        if persisted:
            return persisted
        fetched = await self.news_service._fetch_headlines(commodity)
        await self.ingest_headlines(session, commodity=commodity, headlines=fetched)
        return await self.get_recent_headlines(session, commodity=commodity, limit=limit)

    async def build_news_feature_frame(self, session: AsyncSession, *, commodity: str) -> pd.DataFrame:
        headlines = await self.get_or_ingest_recent_headlines(session, commodity=commodity, limit=100)
        if not headlines:
            return pd.DataFrame()
        sentiment = self.news_service._heuristic_sentiment(headlines)
        sentiment_score = {"bullish": 1.0, "neutral": 0.0, "bearish": -1.0}.get(sentiment, 0.0)
        frame = pd.DataFrame(
            [
                {
                    "Date": pd.Timestamp(headline.published_at).normalize(),
                    "news_headline_count": 1,
                    "news_sentiment_score": sentiment_score,
                }
                for headline in headlines
            ]
        )
        aggregated = frame.groupby("Date", as_index=True).agg(
            news_headline_count=("news_headline_count", "sum"),
            news_sentiment_score=("news_sentiment_score", "mean"),
        )
        aggregated.index = pd.to_datetime(aggregated.index)
        return aggregated.sort_index()

    @staticmethod
    def _normalize_published_at(value):
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)
