from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from yondo_api.core.schemas import Input, Output, UtcDatetime

SortOrder = Literal['recommended', 'rating', 'price_asc', 'price_desc', 'newest', 'distance']


class DiscoveryFilters(Input):
    q: str | None = Field(default=None, max_length=100, description='Name/bio text search')
    service: str | None = Field(default=None, max_length=64)
    gender: str | None = Field(default=None, max_length=64)
    age_min: int | None = Field(default=None, ge=0, le=150)
    age_max: int | None = Field(default=None, ge=0, le=150)
    price_min: int | None = Field(default=None, ge=0)
    price_max: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, pattern=r'^[A-Z]{3}$')
    language: str | None = Field(default=None, max_length=64)
    interest: str | None = Field(default=None, max_length=64)
    city: str | None = Field(default=None, max_length=128)
    available_on: date | None = None
    rating_min: float | None = Field(default=None, ge=1, le=5)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float | None = Field(default=None, gt=0, le=200)
    favorites_only: bool = False
    sort: SortOrder = 'recommended'
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=10_000)

    @model_validator(mode='after')
    def coherent(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('latitude and longitude must be provided together')
        if self.radius_km is not None and self.latitude is None:
            raise ValueError('radius_km requires latitude and longitude')
        if self.sort == 'distance' and self.latitude is None:
            raise ValueError('distance sort requires latitude and longitude')
        if None not in (self.age_min, self.age_max) and self.age_min > self.age_max:
            raise ValueError('age_min must not exceed age_max')
        if None not in (self.price_min, self.price_max) and self.price_min > self.price_max:
            raise ValueError('price_min must not exceed price_max')
        return self


class ServiceSummary(Output):
    id: UUID
    service_code: str
    description: str
    price_minor: int
    currency: str
    unit_minutes: int


class PhotoView(Output):
    id: UUID
    url: str | None
    width: int
    height: int
    caption: str


class CompanionStats(Output):
    rating_average: float | None = None
    rating_count: int = 0
    completed_bookings: int = 0


class CompanionCard(Output):
    profile_id: UUID
    display_name: str
    age: int | None
    gender: str | None
    city: str | None
    area: str | None
    primary_photo: PhotoView | None
    services: list[str]
    min_price_minor: int | None
    currency: str | None
    distance_km: float | None
    is_favorite: bool
    badges: list[str]
    stats: CompanionStats


class SearchResult(Output):
    items: list[CompanionCard]
    total: int
    next_offset: int | None


class AvailabilitySlot(Output):
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    timezone: str


class PublicProfile(CompanionCard):
    bio: str
    languages: list[str]
    interests: list[str]
    photos: list[PhotoView]
    service_details: list[ServiceSummary]
    availability: list[AvailabilitySlot]
    member_since: UtcDatetime


class ExperienceCount(Output):
    service_code: str
    companions: int


class HomeSection(Output):
    key: str
    title: str
    items: list[CompanionCard]


class HomeResponse(Output):
    sections: list[HomeSection]
    popular_experiences: list[ExperienceCount]
