from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from yondo_api.companions.schemas import Input, Output
from yondo_api.discovery.schemas import DiscoveryPhoto, DiscoveryService

StoryKindName = Literal['availability', 'note']


class StoryWrite(Input):
    kind: StoryKindName
    # Required for `note`, optional for `availability`. Contact details are refused server-side.
    caption: str = Field(default='', max_length=80)
    photo_id: UUID | None = Field(default=None, description='One of the owner\'s own photos.')
    service_id: UUID | None = Field(default=None, description='One of the owner\'s own services.')


class StoryWindow(BaseModel):
    starts_at: datetime
    ends_at: datetime


class StorySlide(Output):
    id: UUID
    kind: StoryKindName
    caption: str
    created_at: datetime
    expires_at: datetime
    photo: DiscoveryPhoto | None = None
    service: DiscoveryService | None = None
    # Free windows computed now (availability minus active bookings); empty for notes.
    windows: list[StoryWindow] = Field(default_factory=list)


class OwnStory(StorySlide):
    state: Literal['active', 'expired', 'removed']
    removal_note: str | None = None


class StoryRing(BaseModel):
    profile_id: UUID
    display_name: str
    verified: bool = True
    photo: DiscoveryPhoto | None = None
    count: int
    latest_at: datetime
    has_availability: bool


class StoryReportWrite(Input):
    category: Literal['inappropriate_request', 'fake_profile', 'fraud', 'other']
    description: str = Field(default='', max_length=500)


class StoryReportResponse(BaseModel):
    id: UUID
    status: str


class StoryRemove(Input):
    note: str = Field(min_length=3, max_length=500)


class AdminStory(BaseModel):
    id: UUID
    profile_id: UUID
    display_name: str
    kind: StoryKindName
    caption: str
    created_at: datetime
    expires_at: datetime
    state: Literal['active', 'expired', 'removed']
    removed_at: datetime | None = None
    removal_note: str | None = None
    report_count: int
    model_config = ConfigDict(from_attributes=True)
