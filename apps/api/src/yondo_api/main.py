from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI

from yondo_api.api.errors import install_exception_handlers
from yondo_api.api.health import DatabaseHealthCheck, RedisHealthCheck, public_router
from yondo_api.api.middleware import RequestContextMiddleware
from yondo_api.api.v1.router import router as api_v1_router
from yondo_api.auth.providers import (
    DevelopmentOtpProvider,
    NoopOtpRateLimitHook,
    OtpDeliveryProvider,
    RedisOtpRateLimitHook,
    UnconfiguredOtpProvider,
)
from yondo_api.auth.router import router as auth_router
from yondo_api.companions.admin import router as companion_admin_router
from yondo_api.companions.integrations import IdentityEligibility, UnconfiguredIdentityEligibility
from yondo_api.companions.photos import router as companion_photos_router
from yondo_api.companions.resources import router as companion_resources_router
from yondo_api.companions.router import router as companion_router
from yondo_api.config import Settings, get_settings
from yondo_api.db.session import create_database_engine, create_session_factory
from yondo_api.integrations.storage import ObjectStorage
from yondo_api.logging import configure_logging


def create_application(
    settings: Settings | None = None,
    *,
    otp_provider: OtpDeliveryProvider | None = None,
    object_storage: ObjectStorage | None = None,
    identity_eligibility: IdentityEligibility | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)
    selected_otp_provider = otp_provider or (
        DevelopmentOtpProvider()
        if app_settings.environment in {'development', 'test'}
        else UnconfiguredOtpProvider()
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(
            app_settings.database_url_async,
            echo=app_settings.debug and app_settings.environment == 'development',
        )
        redis_client = redis.from_url(app_settings.redis_url, decode_responses=True)
        app.state.db_engine = engine
        app.state.db_session_factory = create_session_factory(engine)
        app.state.redis = redis_client
        app.state.otp_provider = selected_otp_provider
        app.state.otp_rate_limit_hook = (
            RedisOtpRateLimitHook(
                redis_client, app_settings.auth_otp_provider_rate_limit_per_minute
            )
            if app_settings.auth_otp_provider_rate_limit_per_minute > 0
            else NoopOtpRateLimitHook()
        )
        app.state.readiness_checks = {
            'database': DatabaseHealthCheck(engine),
            'redis': RedisHealthCheck(redis_client),
        }
        try:
            yield
        finally:
            await redis_client.aclose()
            await engine.dispose()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.debug,
        lifespan=lifespan,
        docs_url='/docs' if app_settings.environment != 'production' else None,
        redoc_url=None,
    )
    app.state.settings = app_settings
    app.state.object_storage = object_storage
    app.state.identity_eligibility = identity_eligibility or UnconfiguredIdentityEligibility()
    app.add_middleware(RequestContextMiddleware)
    install_exception_handlers(app)
    app.include_router(public_router)
    app.include_router(api_v1_router, prefix=app_settings.api_v1_prefix)
    app.include_router(auth_router, prefix=app_settings.api_v1_prefix)
    for companion_routes in (
        companion_router,
        companion_resources_router,
        companion_photos_router,
        companion_admin_router,
    ):
        app.include_router(companion_routes, prefix=app_settings.api_v1_prefix)
    return app


app = create_application()
