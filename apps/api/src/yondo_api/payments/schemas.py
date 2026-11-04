from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from yondo_api.core.schemas import Input, Output, UtcDatetime
from yondo_api.gifts.schemas import BookingGifts

IdempotencyKey = str


class BookingCheckout(Input):
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r'^[A-Za-z0-9_.:-]+$')
    # Booking + Add Flowers + Add Gift = One Checkout (ROADMAP Phase 16).
    gifts: BookingGifts | None = None


class PaymentResponse(Output):
    id: UUID
    booking_id: UUID | None
    provider: str
    status: str
    currency: str
    amount_minor: int
    refunded_minor: int
    breakdown: dict[str, Any]
    checkout_url: str | None
    expires_at: UtcDatetime | None
    paid_at: UtcDatetime | None
    failure_reason: str | None
    created_at: UtcDatetime


class SandboxResult(Input):
    result: Literal['succeeded', 'failed']


class WebhookAck(Output):
    outcome: str


class PayoutResponse(Output):
    id: UUID
    booking_id: UUID | None
    gift_order_id: UUID | None
    amount_minor: int
    currency: str
    status: str
    available_at: UtcDatetime | None
    paid_at: UtcDatetime | None
    reference: str | None
    created_at: UtcDatetime


class EarningsSummary(Output):
    currency: str
    held_minor: int
    scheduled_minor: int
    available_minor: int
    paid_minor: int


class Earnings(Output):
    summary: list[EarningsSummary]
    payouts: list[PayoutResponse]
