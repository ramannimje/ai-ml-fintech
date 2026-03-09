from sqlalchemy import Column, Integer, String, Date, JSON

try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_ENABLED = True
except Exception:  # pragma: no cover - optional dependency
    PGVECTOR_ENABLED = False

    def Vector(_dimensions: int):  # type: ignore[misc]
        return JSON

from app.db.base import Base

class MarketPattern(Base):
    __tablename__ = "market_patterns"
    id = Column(Integer, primary_key=True, index=True)
    commodity = Column(String(32), index=True, nullable=False)
    region = Column(String(32), index=True, nullable=False)
    window_end_date = Column(Date, index=True, nullable=False)
    
    # 30-day normalized pricing vector (dim 30)
    embedding = Column(Vector(30), nullable=False)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(64), index=True, nullable=False)  # 'news', 'fed_report', 'metals_live_summary'
    content = Column(String, nullable=False)
    
    # Gemini text-embedding-004 vector (dim 768)
    embedding = Column(Vector(768), nullable=False)
    
    # Arbitrary metadata for filtering (date, title, url, etc)
    metadata_ = Column(JSON, nullable=True)
