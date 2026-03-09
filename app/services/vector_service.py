from __future__ import annotations

import hashlib
import logging
import re
from typing import Any
import json
import inspect

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.vector_models import KnowledgeBase, MarketPattern, PGVECTOR_ENABLED

logger = logging.getLogger(__name__)

PATTERN_DIM = 30
TEXT_EMBED_DIM = 768


class VectorService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.pgvector_enabled = PGVECTOR_ENABLED

    def normalize_price_window(self, prices: pd.Series) -> np.ndarray:
        """
        Takes a time series of prices, z-score normalizes it so that it's scale-invariant,
        and extracts the last PATTERN_DIM (30) days for embedding generation.
        """
        data = prices.to_numpy()[-PATTERN_DIM:]
        if len(data) < PATTERN_DIM:
            data = np.pad(data, (PATTERN_DIM - len(data), 0), mode="edge")

        std_val = np.std(data)
        if std_val == 0:
            std_val = 1e-8

        normalized = (data - np.mean(data)) / std_val
        return normalized.astype(float)

    def _local_text_embedding(self, text: str, dim: int = TEXT_EMBED_DIM) -> list[float]:
        """
        Deterministic local embedding (hashing trick) used when external embedding APIs are not configured.
        """
        tokens = re.findall(r"[a-zA-Z0-9_]+", (text or "").lower())
        if not tokens:
            return [0.0] * dim

        vec = np.zeros(dim, dtype=np.float32)
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % dim
            sign = 1.0 if (digest[4] % 2 == 0) else -1.0
            vec[idx] += sign

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.astype(float).tolist()

    async def find_similar_patterns(
        self, session: AsyncSession, commodity: str, region: str, current_window: pd.Series, top_k: int = 3
    ) -> list[tuple[MarketPattern, float]]:
        """
        Uses pgvector Cosine Distance '<=>' to find historical 30-day windows that
        most closely match the normalized shape of the `current_window`.
        """
        query_vector = self.normalize_price_window(current_window).tolist()
        if self._can_use_pgvector(session):
            stmt = (
                select(MarketPattern, MarketPattern.embedding.cosine_distance(query_vector).label("distance"))
                .where(MarketPattern.commodity == commodity)
                .where(MarketPattern.region == region)
                .order_by(MarketPattern.embedding.cosine_distance(query_vector))
                .limit(top_k)
            )
            result = await session.execute(stmt)
            return [(row[0], float(row[1])) for row in result.all()]

        stmt = (
            select(MarketPattern)
            .where(MarketPattern.commodity == commodity)
            .where(MarketPattern.region == region)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        scored: list[tuple[MarketPattern, float]] = []
        for pattern in rows:
            vec = self._coerce_vector(pattern.embedding)
            if vec is None:
                continue
            scored.append((pattern, self._cosine_distance(query_vector, vec)))
        scored.sort(key=lambda item: item[1])
        return scored[:top_k]

    async def store_market_pattern(
        self, session: AsyncSession, commodity: str, region: str, date: Any, prices: pd.Series
    ) -> None:
        """Stores a new rolling normalized 30-day window in pgvector for future retrieval."""
        embedding = self.normalize_price_window(prices).tolist()
        pattern = MarketPattern(
            commodity=commodity,
            region=region,
            window_end_date=date,
            embedding=embedding,
        )
        session.add(pattern)
        await session.commit()

    async def get_text_embedding(self, text: str) -> list[float]:
        """Returns a deterministic local embedding for retrieval indexing."""
        return self._local_text_embedding(text)

    async def index_knowledge_document(
        self, session: AsyncSession, source: str, content: str, metadata: dict | None = None
    ) -> None:
        """Embeds a document (like a news summary) and stores it in the vector base."""
        vector = await self.get_text_embedding(content)
        kb_entry = KnowledgeBase(
            source=source,
            content=content,
            embedding=vector,
            metadata_=metadata or {},
        )
        session.add(kb_entry)
        await session.commit()

    async def search_knowledge_base(
        self, session: AsyncSession, query_text: str, top_k: int = 5
    ) -> list[tuple[KnowledgeBase, float]]:
        """
        Retrieval-Augmented Generation retrieval step.
        Converts the user's question into an embedding and retrieves the top_k
        closest factual documents via Cosine distance.
        """
        query_vector = await self.get_text_embedding(query_text)
        if self._can_use_pgvector(session):
            stmt = (
                select(KnowledgeBase, KnowledgeBase.embedding.cosine_distance(query_vector).label("distance"))
                .order_by(KnowledgeBase.embedding.cosine_distance(query_vector))
                .limit(top_k)
            )
            result = await session.execute(stmt)
            return [(row[0], float(row[1])) for row in result.all()]

        stmt = select(KnowledgeBase)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        scored: list[tuple[KnowledgeBase, float]] = []
        for entry in rows:
            vec = self._coerce_vector(entry.embedding)
            if vec is None:
                continue
            scored.append((entry, self._cosine_distance(query_vector, vec)))
        scored.sort(key=lambda item: item[1])
        return scored[:top_k]

    def _can_use_pgvector(self, session: AsyncSession) -> bool:
        if not self.pgvector_enabled:
            return False
        get_bind = getattr(session, "get_bind", None)
        if get_bind is None:
            return False
        if inspect.iscoroutinefunction(get_bind):
            # Test doubles sometimes model `get_bind` as async; keep legacy "enabled" behavior.
            return True
        bind = get_bind()
        if bind is None:
            return False
        dialect = getattr(bind, "dialect", None)
        if dialect is None:
            return False
        return getattr(dialect, "name", "") == "postgresql"

    @staticmethod
    def _coerce_vector(value: Any) -> list[float] | None:
        if value is None:
            return None
        if isinstance(value, list):
            try:
                return [float(v) for v in value]
            except Exception:
                return None
        if isinstance(value, tuple):
            try:
                return [float(v) for v in value]
            except Exception:
                return None
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [float(v) for v in parsed]
            except Exception:
                return None
        return None

    @staticmethod
    def _cosine_distance(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            return 1.0
        a_arr = np.asarray(a, dtype=np.float32)
        b_arr = np.asarray(b, dtype=np.float32)
        a_norm = float(np.linalg.norm(a_arr))
        b_norm = float(np.linalg.norm(b_arr))
        if a_norm == 0.0 or b_norm == 0.0:
            return 1.0
        similarity = float(np.dot(a_arr, b_arr) / (a_norm * b_norm))
        similarity = max(-1.0, min(1.0, similarity))
        return 1.0 - similarity


vector_service = VectorService()
