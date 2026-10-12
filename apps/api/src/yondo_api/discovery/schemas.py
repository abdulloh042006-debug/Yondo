from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


class DiscoveryService(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_code: str
    description: str
    price_minor: int
    currency: str
    unit_minutes: int


class DiscoveryPhoto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content_type: str
    width: int
    height: int
    position: int
    caption: str


class CompanionCard(BaseModel):
    id: UUID
    display_name: str
    bio: str
    age: int | None
    gender: str | None
    city: str | None
    languages: list[str]
    interests: list[str]
    verified: bool = True
    rating: float | None = None
    review_count: int = 0
    services: list[DiscoveryService]
    photos: list[DiscoveryPhoto]


TagFilter = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class FavoriteResponse(BaseModel):
    profile_id: UUID
    created_at: datetime

    @field_validator('created_at')
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class DiscoveryPage(BaseModel):
    items: list[CompanionCard]
    limit: int
    offset: int = Field(ge=0)
    has_more: bool
