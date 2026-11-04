from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator, model_validator

from yondo_api.bookings.models import BookingStatus
from yondo_api.core.schemas import Input, Output, UtcDatetime


class MeetingPlace(Input):
    name: str = Field(min_length=1, max_length=200)
    address: str = Field(default='', max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode='after')
    def paired(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('latitude and longitude must be provided together')
        return self


class BookingRequest(Input):
    profile_id: UUID
    service_id: UUID
    starts_at: AwareDatetime
    duration_minutes: int = Field(strict=True, gt=0, le=24 * 60)
    meeting_place: MeetingPlace
    note: str = Field(default='', max_length=2000)
    rebooked_from_id: UUID | None = None

    @field_validator('starts_at')
    @classmethod
    def whole_minute(cls, value):
        if value.second or value.microsecond:
            raise ValueError('starts_at must be on a whole minute')
        return value


class BookingCreate(BookingRequest):
    # The customer explicitly accepts the booking contract and platform rules (TZ §11).
    accept_contract: Literal[True]


class Quote(Output):
    service_code: str
    unit_price_minor: int
    unit_minutes: int
    duration_minutes: int
    currency: str
    service_amount_minor: int
    platform_fee_minor: int
    total_minor: int
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    timezone: str
    contract: dict[str, Any]


class Party(Output):
    id: UUID
    display_name: str | None
    age: int | None = None
    gender: str | None = None
    rating_average: float | None = None
    rating_count: int = 0


class BookingResponse(Output):
    id: UUID
    status: BookingStatus
    role: Literal['customer', 'companion', 'admin']
    customer: Party
    companion: Party
    profile_id: UUID
    service_id: UUID | None
    service_code: str
    unit_price_minor: int
    unit_minutes: int
    currency: str
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    duration_minutes: int
    timezone: str
    meeting_place: MeetingPlace
    note: str
    service_amount_minor: int
    platform_fee_minor: int
    total_minor: int
    companion_payout_minor: int | None
    refund_minor: int
    contract: dict[str, Any]
    contract_version: str
    customer_accepted_at: UtcDatetime
    companion_accepted_at: UtcDatetime | None
    request_expires_at: UtcDatetime
    payment_due_at: UtcDatetime | None
    confirmed_at: UtcDatetime | None
    cancelled_at: UtcDatetime | None
    cancellation_reason: str | None
    cancellation_note: str | None
    customer_checked_in_at: UtcDatetime | None
    companion_checked_in_at: UtcDatetime | None
    started_at: UtcDatetime | None
    ended_at: UtcDatetime | None
    no_show_party: str | None
    rebooked_from_id: UUID | None
    created_at: UtcDatetime
    actions: list[str]


class BookingEventResponse(Output):
    id: UUID
    event: str
    actor_id: UUID | None
    from_status: str | None
    to_status: str
    data: dict[str, Any]
    created_at: UtcDatetime


class DecisionNote(Input):
    note: str = Field(default='', max_length=2000)


class CancellationPreview(Output):
    refund_minor: int
    refund_bps: int
    refund_percent: float
    policy: Literal['no_payment', 'free', 'partial', 'none', 'full_companion_cancel']


class RebookTemplate(Output):
    profile_id: UUID
    service_id: UUID | None
    service_code: str
    duration_minutes: int
    meeting_place: MeetingPlace
