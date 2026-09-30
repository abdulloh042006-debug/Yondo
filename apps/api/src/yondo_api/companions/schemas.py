from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from yondo_api.companions.integrations import IdentityStatus
from yondo_api.companions.models import ApplicationStatus, ContentStatus
from yondo_api.models.user import AccountStatus

Text128 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ApplicationWrite(Input):
    statement: str = Field(default='', max_length=4000)


class ApplicationResponse(Output):
    id: UUID
    user_id: UUID
    statement: str
    status: ApplicationStatus
    review_note: str | None


class ApprovalDecision(Input):
    decision: Literal['approve', 'reject']
    note: str = Field(min_length=1, max_length=2000)


class ProfileWrite(Input):
    display_name: Text128
    bio: str = Field(default='', max_length=8000)
    languages: list[Tag] = Field(default_factory=list, max_length=100)
    interests: list[Tag] = Field(default_factory=list, max_length=100)

    @field_validator('languages', 'interests')
    @classmethod
    def unique_tags(cls, values: list[str]) -> list[str]:
        if len({value.casefold() for value in values}) != len(values):
            raise ValueError('Entries must be unique, ignoring case')
        return values


class ProfileResponse(Output):
    id: UUID
    application_id: UUID
    display_name: str
    bio: str
    languages: list[str]
    interests: list[str]
    content_status: ContentStatus
    activation_requested: bool
    review_note: str | None


class ServiceWrite(Input):
    service_code: Annotated[str, StringConstraints(pattern=r'^[a-z][a-z0-9_]{0,63}$')]
    description: str = Field(default='', max_length=4000)
    price_minor: int = Field(strict=True, ge=0, le=9_223_372_036_854_775_807)
    currency: Annotated[str, StringConstraints(pattern=r'^[A-Z]{3}$')]
    unit_minutes: int = Field(strict=True, gt=0, le=2_147_483_647)


class ServiceResponse(ServiceWrite, Output):
    id: UUID
    profile_id: UUID


class AvailabilityWrite(Input):
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    timezone: str = Field(min_length=1, max_length=64)

    @field_validator('timezone')
    @classmethod
    def known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError('An IANA timezone is required') from exc
        return value

    @model_validator(mode='after')
    def ordered_interval(self) -> Self:
        self.starts_at = self.starts_at.astimezone(UTC)
        self.ends_at = self.ends_at.astimezone(UTC)
        if self.ends_at <= self.starts_at:
            raise ValueError('ends_at must be after starts_at')
        return self


class AvailabilityResponse(Output):
    id: UUID
    profile_id: UUID
    starts_at: datetime
    ends_at: datetime
    timezone: str

    @field_validator('starts_at', 'ends_at')
    @classmethod
    def utc_for_sqlite(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class PhotoCaption(Input):
    caption: str = Field(max_length=512)


class PhotoOrder(Input):
    photo_ids: list[UUID] = Field(max_length=1000)

    @field_validator('photo_ids')
    @classmethod
    def unique_ids(cls, values: list[UUID]) -> list[UUID]:
        if len(set(values)) != len(values):
            raise ValueError('Photo IDs must be unique')
        return values


class PhotoResponse(Output):
    id: UUID
    profile_id: UUID
    content_type: str
    size_bytes: int
    width: int
    height: int
    position: int
    caption: str


class PhotoDownload(Output):
    url: str


class CompanionStatus(Output):
    application_status: ApplicationStatus
    content_status: ContentStatus
    account_status: AccountStatus
    identity_status: IdentityStatus
    activation_requested: bool
    publicly_active: bool
    blockers: list[str]
