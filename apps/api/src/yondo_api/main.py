from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as redis
from anyio import CapacityLimiter
from fastapi import FastAPI

from yondo_api.account.admin import router as account_admin_router
from yondo_api.account.router import legal_router
from yondo_api.account.router import router as account_router
from yondo_api.admin.router import router as admin_router
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
from yondo_api.auth.telegram_gateway import TelegramGatewayOtpProvider
from yondo_api.beta.router import router as beta_router
from yondo_api.bookings.router import router as bookings_router
from yondo_api.cancellations.abuse import BookingRateLimiter, DatabaseBookingRateLimiter
from yondo_api.cancellations.admin import router as cancellations_admin_router
from yondo_api.cancellations.router import router as cancellations_router
from yondo_api.chat.router import router as chat_router
from yondo_api.companions.admin import router as companion_admin_router
from yondo_api.companions.integrations import IdentityEligibility, UnconfiguredIdentityEligibility
from yondo_api.companions.photos import router as companion_photos_router
from yondo_api.companions.resources import router as companion_resources_router
from yondo_api.companions.router import router as companion_router
from yondo_api.config import Settings, get_settings
from yondo_api.db.session import create_database_engine, create_session_factory
from yondo_api.discovery.router import router as discovery_router
from yondo_api.gifts.click_test import router as click_test_router
from yondo_api.gifts.router import router as gifts_router
from yondo_api.gifts.test_orders import router as gift_test_orders_router
from yondo_api.gifts.vendor import router as vendor_router
from yondo_api.integration.router import router as integration_router
from yondo_api.integrations.storage import ObjectStorage
from yondo_api.logging import configure_logging
from yondo_api.meetings.router import router as meetings_router
from yondo_api.notifications.router import router as notifications_router
from yondo_api.payments.provider import PaymentProvider, UnconfiguredPaymentProvider
from yondo_api.payments.router import router as payments_router
from yondo_api.payments.tezcheck import TezCheckPaymentProvider
from yondo_api.reviews.router import router as reviews_router
from yondo_api.safety.admin import router as safety_admin_router
from yondo_api.safety.router import router as safety_router


def select_otp_provider(settings: Settings) -> OtpDeliveryProvider:
    """Pick the OTP provider: a configured real provider wins in every environment."""
    if settings.telegram_gateway_token is not None:
        return TelegramGatewayOtpProvider(
            settings.telegram_gateway_token.get_secret_value(),
            base_url=settings.telegram_gateway_base_url,
            timeout_seconds=settings.telegram_gateway_timeout_seconds,
        )
    if settings.environment in {'development', 'test'}:
        return DevelopmentOtpProvider()
    return UnconfiguredOtpProvider()


def create_application(
    settings: Settings | None = None,
    *,
    otp_provider: OtpDeliveryProvider | None = None,
    object_storage: ObjectStorage | None = None,
    identity_eligibility: IdentityEligibility | None = None,
    payment_provider: PaymentProvider | None = None,
    booking_rate_limiter: BookingRateLimiter | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)
    selected_otp_provider = otp_provider or select_otp_provider(app_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.companion_image_limiter = CapacityLimiter(2)
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
    app.state.payment_provider = payment_provider or (
        TezCheckPaymentProvider.from_settings(app_settings)
        if app_settings.tezcheck_token.get_secret_value()
        else UnconfiguredPaymentProvider()
    )
    app.state.booking_rate_limiter = booking_rate_limiter or DatabaseBookingRateLimiter()
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
        discovery_router,
        bookings_router,
        cancellations_router,
        cancellations_admin_router,
        payments_router,
        chat_router,
        gifts_router,
        gift_test_orders_router,
        click_test_router,
        vendor_router,
        integration_router,
        notifications_router,
        beta_router,
        admin_router,
        safety_router,
        safety_admin_router,
        account_router,
        account_admin_router,
        legal_router,
        reviews_router,
        meetings_router,
    ):
        app.include_router(companion_routes, prefix=app_settings.api_v1_prefix)
    return app


app = create_application()
