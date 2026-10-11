from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_validator

from yondo_api.bookings.models import BookingStatus


class BookingCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    service_id: UUID
    starts_at: AwareDatetime
    duration_minutes: int = Field(strict=True, gt=0, le=2_147_483_647)
    timezone: str = Field(min_length=1, max_length=64)
    meeting_place: Annotated[str, StringConstraints(min_length=1, max_length=512)]

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
            raise ValueError('An IANA timezone is required') from exc
        return value

    @field_validator('starts_at')
    @classmethod
    def normalize_start(cls, value: datetime) -> datetime:
        try:
            return value.astimezone(UTC)
        except (OverflowError, ValueError) as exc:
            raise ValueError('Datetime must represent a supported UTC instant') from exc


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    profile_id: UUID
    service_id: UUID
    status: BookingStatus
    service_code: str
    service_description: str
    starts_at: datetime
    ends_at: datetime
    timezone: str
    duration_minutes: int
    meeting_place: str
    price_minor: int
    currency: str
    customer_contract_accepted_at: datetime
    companion_contract_accepted_at: datetime | None
    created_at: datetime

    @field_validator(
        'starts_at',
        'ends_at',
        'customer_contract_accepted_at',
        'companion_contract_accepted_at',
        'created_at',
    )
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class BookingCancel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    reason: str = Field(default='', max_length=2000)
