"""Registry of domain routers and integration defaults, kept out of ``main`` for clarity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from yondo_api.companions.integrations import IdentityEligibility, UnconfiguredIdentityEligibility

if TYPE_CHECKING:
    from fastapi import FastAPI

    from yondo_api.config import Settings


def _routers() -> list:
    from yondo_api.bookings.meeting import router as meeting_router
    from yondo_api.bookings.router import router as bookings_router
    from yondo_api.chat.router import router as chat_router
    from yondo_api.discovery.router import favorites_router
    from yondo_api.discovery.router import router as discovery_router
    from yondo_api.payments.router import payouts_router
    from yondo_api.payments.router import router as payments_router
    from yondo_api.realtime.router import router as realtime_router
    from yondo_api.reviews.router import router as reviews_router
    from yondo_api.safety.disputes import router as disputes_router

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
    ]


ROUTERS: list = _routers()


def default_identity_eligibility() -> IdentityEligibility:
    return UnconfiguredIdentityEligibility()


def configure_state(app: FastAPI, settings: Settings) -> None:
    from yondo_api.payments.providers import SandboxPaymentProvider

    providers = {}
    if settings.effective_payment_provider == 'sandbox':
        providers['sandbox'] = SandboxPaymentProvider(
            settings.payment_webhook_secret.get_secret_value().encode(),
            settings.payment_checkout_base_url,
        )
    app.state.payment_providers = providers
