"""Pricing, contract and cancellation rules. Numbers come from configurable settings.

The configured values are PLACEHOLDER business policy until the business model is approved
(TZ §21, §26); this module only defines how they are applied.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from yondo_api.api.errors import ApplicationError
from yondo_api.config import Settings
from yondo_api.core.money import BPS_DENOMINATOR, apply_bps

PLATFORM_RULES = (
    'community_guidelines',
    'prohibited_services',
    'booking_rules',
    'cancellation_policy',
    'refund_policy',
    'no_show_policy',
    'payment_terms',
    'safety_rules',
)


@dataclass(frozen=True, slots=True)
class Amounts:
    service_amount_minor: int
    platform_fee_minor: int
    total_minor: int
    companion_payout_minor: int


def price(unit_price_minor: int, unit_minutes: int, duration_minutes: int, settings: Settings):
    """Price an exact number of pricing units; no partial-unit rounding is invented."""
    if duration_minutes % unit_minutes:
        raise ApplicationError(
            'invalid_duration',
            f'Duration must be a multiple of the {unit_minutes}-minute pricing unit',
            422,
        )
    service_amount = unit_price_minor * (duration_minutes // unit_minutes)
    fee = apply_bps(service_amount, settings.booking_platform_fee_bps)
    commission = apply_bps(service_amount, settings.booking_companion_commission_bps)
    return Amounts(
        service_amount_minor=service_amount,
        platform_fee_minor=fee,
        total_minor=service_amount + fee,
        companion_payout_minor=service_amount - commission,
    )


def contract_snapshot(
    *,
    settings: Settings,
    customer: dict[str, Any],
    companion: dict[str, Any],
    service: dict[str, Any],
    starts_at: datetime,
    ends_at: datetime,
    timezone: str,
    duration_minutes: int,
    meeting_place: dict[str, Any],
    amounts: Amounts,
    currency: str,
) -> dict[str, Any]:
    """Immutable mini-contract both parties accept (TZ §11)."""
    return {
        'version': settings.booking_contract_version,
        'customer': customer,
        'companion': companion,
        'service': service,
        'starts_at': starts_at.isoformat(),
        'ends_at': ends_at.isoformat(),
        'timezone': timezone,
        'duration_minutes': duration_minutes,
        'meeting_place': meeting_place,
        'price': {
            'service_amount_minor': amounts.service_amount_minor,
            'platform_fee_minor': amounts.platform_fee_minor,
            'total_minor': amounts.total_minor,
            'currency': currency,
        },
        'cancellation_policy': {
            'free_cancellation_hours': settings.booking_free_cancellation_hours,
            'late_cancellation_refund_bps': settings.booking_late_cancellation_refund_bps,
            'after_start_refund_bps': 0,
            'companion_cancellation_refund_bps': BPS_DENOMINATOR,
        },
        'platform_rules': list(PLATFORM_RULES),
    }


@dataclass(frozen=True, slots=True)
class CancellationOutcome:
    policy: str
    refund_bps: int


def cancellation_outcome(
    *,
    paid: bool,
    by_companion: bool,
    now: datetime,
    starts_at: datetime,
    policy: dict[str, Any],
) -> CancellationOutcome:
    """Apply the cancellation policy captured in the booking contract."""
    if not paid:
        return CancellationOutcome('no_payment', 0)
    if by_companion:
        return CancellationOutcome(
            'full_companion_cancel', int(policy['companion_cancellation_refund_bps'])
        )
    if now <= starts_at - timedelta(hours=int(policy['free_cancellation_hours'])):
        return CancellationOutcome('free', BPS_DENOMINATOR)
    if now < starts_at:
        return CancellationOutcome('partial', int(policy['late_cancellation_refund_bps']))
    return CancellationOutcome('none', int(policy['after_start_refund_bps']))
