from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.auth_routes import router as auth_router
from app.api.routes import router
from app.core.auth import TokenVerificationMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.schema_guard import ensure_training_runs_schema
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.add_middleware(TokenVerificationMiddleware)
app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await ensure_training_runs_schema(conn)
