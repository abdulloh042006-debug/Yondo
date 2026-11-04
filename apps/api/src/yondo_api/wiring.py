"""Registry of domain routers and integration defaults, kept out of ``main`` for clarity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from yondo_api.companions.integrations import IdentityEligibility

if TYPE_CHECKING:
    from fastapi import FastAPI

    from yondo_api.config import Settings


def _routers() -> list:
    from yondo_api.admin.analytics import router as admin_analytics_router
    from yondo_api.admin.commerce import router as admin_commerce_router
    from yondo_api.admin.gifts import router as admin_gifts_router
    from yondo_api.admin.trust import router as admin_trust_router
    from yondo_api.admin.users import router as admin_users_router
    from yondo_api.bookings.meeting import router as meeting_router
    from yondo_api.bookings.router import router as bookings_router
    from yondo_api.chat.router import router as chat_router
    from yondo_api.discovery.router import favorites_router
    from yondo_api.discovery.router import router as discovery_router
    from yondo_api.gifts.catalog import favorites_router as product_favorites_router
    from yondo_api.gifts.catalog import router as gifts_router
    from yondo_api.gifts.vendor import router as vendor_router
    from yondo_api.payments.router import payouts_router
    from yondo_api.payments.router import router as payments_router
    from yondo_api.realtime.router import router as realtime_router
    from yondo_api.reviews.router import router as reviews_router
    from yondo_api.safety.disputes import router as disputes_router
    from yondo_api.safety.identity import router as verification_router
    from yondo_api.safety.router import router as safety_router

    return [
        discovery_router,
        favorites_router,
        bookings_router,
        payments_router,
        payouts_router,
        chat_router,
        realtime_router,
        meeting_router,
        reviews_router,
        disputes_router,
        verification_router,
        safety_router,
        admin_users_router,
        admin_trust_router,
        admin_commerce_router,
        admin_analytics_router,
        gifts_router,
        product_favorites_router,
        vendor_router,
        admin_gifts_router,
    ]


ROUTERS: list = _routers()


def default_identity_eligibility() -> IdentityEligibility:
    """Trust & Safety verification records are the authoritative identity source."""
    from yondo_api.safety.identity import DatabaseIdentityEligibility

    return DatabaseIdentityEligibility()


def configure_state(app: FastAPI, settings: Settings) -> None:
    from yondo_api.payments.providers import SandboxPaymentProvider

    providers = {}
    if settings.effective_payment_provider == 'sandbox':
        providers['sandbox'] = SandboxPaymentProvider(
            settings.payment_webhook_secret.get_secret_value().encode(),
            settings.payment_checkout_base_url,
        )
    app.state.payment_providers = providers
    app.state.push_provider = build_push_provider(settings)


def build_push_provider(settings: Settings):
    from yondo_api.integrations.push import FcmPushProvider, LogPushProvider

    if settings.push_provider == 'fcm':
        if not settings.fcm_service_account_file:
            raise ValueError('YONDO_FCM_SERVICE_ACCOUNT_FILE is required for FCM push')
        return FcmPushProvider.from_file(
            settings.fcm_service_account_file, settings.fcm_project_id or None
        )
    if settings.push_provider == 'log':
        return LogPushProvider()
    return None
