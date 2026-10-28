from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from yondo_api.payments.models import PaymentStatus


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    status: PaymentStatus
    subtotal_minor: int
    platform_fee_minor: int
    amount_minor: int
    currency: str
    checkout_url: str | None
    refund_required: bool
    created_at: datetime

    @field_validator('created_at')
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
