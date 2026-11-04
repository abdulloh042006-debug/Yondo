"""Registry of domain routers and integration defaults, kept out of ``main`` for clarity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from yondo_api.companions.integrations import IdentityEligibility, UnconfiguredIdentityEligibility

if TYPE_CHECKING:
    from fastapi import FastAPI

    from yondo_api.config import Settings

def _routers() -> list:
    from yondo_api.discovery.router import favorites_router
    from yondo_api.discovery.router import router as discovery_router

    return [discovery_router, favorites_router]


ROUTERS: list = _routers()


def default_identity_eligibility() -> IdentityEligibility:
    return UnconfiguredIdentityEligibility()


def configure_state(app: FastAPI, settings: Settings) -> None:
    return None
