from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine
# Import all models so Base.metadata includes them
from app.models import training_run, price_record  # noqa: F401

settings = get_settings()
setup_logging()
app = FastAPI(
    title=settings.app_name,
    description="Multi-region commodity market intelligence platform",
    version="2.0.0",
)
app.include_router(router, prefix="/api")


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
