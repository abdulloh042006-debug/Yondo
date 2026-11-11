from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from yondo_api.payments.models import PaymentStatus


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    status: PaymentStatus
    subtotal_minor: int = Field(description='Service amount in integer minor units (tiyin).')
    platform_fee_minor: int = Field(
        description=(
            'Platform commission in minor units. It is deducted from the companion\'s payout '
            'and is NOT charged to the customer.'
        )
    )
    amount_minor: int = Field(
        description=(
            'What the customer pays, in minor units. Equals subtotal_minor: no fee is added '
            'on top (payments created before 2026-11-11 may include the fee).'
        )
    )
    currency: str
    checkout_url: str | None
    refund_required: bool
    created_at: datetime

    @field_validator('created_at')
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
