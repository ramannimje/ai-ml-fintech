from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine

settings = get_settings()
setup_logging()
app = FastAPI(title=settings.app_name)
app.include_router(router)


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
