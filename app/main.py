from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import routes as api_routes
from app.api.routes import router
from app.api.routes_ai_chat import router as ai_chat_router
from app.api.routes_settings import router as settings_router
from app.core.auth import TokenVerificationMiddleware
from app.core.config import get_settings
from app.core.secrets import AUTH_SECRETS, get_secret_value
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.schema_guard import ensure_alerts_schema, ensure_training_runs_schema
from app.db.session import AsyncSessionLocal, engine
# Import all models so Base.metadata includes them
from app.models import alert_history, chat_history, price_alert, price_record, training_run, user_profile, user_settings  # noqa: F401
from app.workers.whatsapp_alert_worker import whatsapp_alert_worker

settings = get_settings()
configured_origins = [item.strip() for item in settings.cors_allowed_origins.split(",") if item.strip()]
allow_origins = [
    settings.frontend_url,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    *configured_origins,
]
session_secret = get_secret_value(
    AUTH_SECRETS,
    "JWT_SECRET",
    env_fallback="JWT_SECRET",
    default=settings.jwt_secret or settings.secret_key or "dev-insecure-session-secret",
)
setup_logging()
app = FastAPI(
    title=settings.app_name,
    description="TradeSight — Multi-region commodity market intelligence platform",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(allow_origins)),
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=session_secret or "dev-insecure-session-secret")
app.add_middleware(TokenVerificationMiddleware)
@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "TradeSight Backend is running 🚀",
        "version": "2.0.0"
    }


app.include_router(router, prefix="/api")
app.include_router(ai_chat_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
try:
    from app.api.auth_routes import router as auth_router

    app.include_router(auth_router, prefix="/api")
except ImportError:
    # Auth routes require optional authlib dependency; skip when unavailable.
    pass


@app.on_event("startup")
async def on_startup() -> None:
    import logging
    _log = logging.getLogger(__name__)
    _log.info(
        "startup_config env=%s auth0_domain=%s infisical_enabled=%s",
        settings.environment,
        bool(settings.auth0_domain and "your-tenant" not in settings.auth0_domain),
        bool(settings.infisical_project_id),
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await ensure_training_runs_schema(conn)
        await ensure_alerts_schema(conn)
    async with AsyncSessionLocal() as session:
        await api_routes.service.prewarm_latest_models(session)
    if settings.whatsapp_worker_enabled:
        whatsapp_alert_worker.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if settings.whatsapp_worker_enabled:
        await whatsapp_alert_worker.stop()
