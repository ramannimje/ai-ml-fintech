import asyncio
from unittest.mock import AsyncMock
import numpy as np
import pandas as pd
import pytest

from app.services.vector_service import VectorService
from app.models.vector_models import MarketPattern, KnowledgeBase


@pytest.fixture
def vector_service():
    """Returns a VectorService instance configured for isolated tests."""
    service = VectorService()
    service.pgvector_enabled = True
    return service


def test_normalize_price_window(vector_service: VectorService):
    """Ensure that 30-day z-score normalization works correctly and handles padding."""
    
    # Test 1: Exactly 30 days of data
    prices_30 = pd.Series(np.linspace(100, 130, 30))
    normalized = vector_service.normalize_price_window(prices_30)
    
    assert len(normalized) == 30
    assert abs(np.mean(normalized)) < 1e-6  # Z-score mean should be 0
    assert abs(np.std(normalized) - 1.0) < 1e-6  # Z-score std should be 1
    
    # Test 2: Less than 30 days of data (should pad to 30)
    prices_15 = pd.Series(np.linspace(100, 115, 15))
    padded = vector_service.normalize_price_window(prices_15)
    
    assert len(padded) == 30
    # Values at the front should be padded with the first edge value.
    # We pad to the *left* using mode='edge'
    assert padded[0] == padded[1]


def test_find_similar_patterns(vector_service: VectorService):
    """Mock the DB session and check that the SQLAlchemy Cosine Distance query is structured properly."""
    try:
        _ = MarketPattern.embedding.cosine_distance  # type: ignore[attr-defined]
    except AttributeError:
        pytest.skip("pgvector comparator unavailable in this environment")

    from unittest.mock import MagicMock
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    # Mock return rows: [(MarketPattern, distance)]
    dummy_pattern = MarketPattern(commodity="gold", region="us")
    mock_result.all.return_value = [(dummy_pattern, 0.05)]
    mock_session.execute.return_value = mock_result
    
    current_window = pd.Series(np.random.normal(150, 5, 30))
    
    results = asyncio.run(
        vector_service.find_similar_patterns(
            session=mock_session,
            commodity="gold",
            region="us",
            current_window=current_window,
            top_k=3,
        )
    )
    
    assert len(results) == 1
    assert results[0][0].commodity == "gold"
    assert results[0][1] == 0.05
    assert mock_session.execute.called


def test_search_knowledge_base(vector_service: VectorService):
    """Ensure the RAG pipeline correctly generates an embedding and runs the Cosine similarity query."""
    try:
        _ = KnowledgeBase.embedding.cosine_distance  # type: ignore[attr-defined]
    except AttributeError:
        pytest.skip("pgvector comparator unavailable in this environment")

    from unittest.mock import MagicMock
    mock_session = AsyncMock()
    mock_result = MagicMock()

    dummy_kb = KnowledgeBase(source="news", content="Inflation drops.")
    mock_result.all.return_value = [(dummy_kb, 0.1)]
    mock_session.execute.return_value = mock_result

    results = asyncio.run(
        vector_service.search_knowledge_base(
            session=mock_session,
            query_text="Is inflation dropping?",
            top_k=2,
        )
    )

    assert len(results) == 1
    assert results[0][0].source == "news"
    assert results[0][0].content == "Inflation drops."
    assert mock_session.execute.called
