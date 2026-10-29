"""Story rules: caption hygiene, live free windows, and the public/own views of a story."""

import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.companions.models import (
    CompanionAvailability,
    CompanionPhoto,
    CompanionProfile,
    CompanionService,
)
from yondo_api.discovery.schemas import DiscoveryPhoto, DiscoveryService
from yondo_api.stories.models import CompanionStory, StoryKind
from yondo_api.stories.schemas import OwnStory, StorySlide, StoryWindow

# Presentation limits only (no business meaning): hide slivers, keep the card readable.
MIN_FREE_MINUTES = 30
MAX_WINDOWS = 3
SLOT_STATUSES = (
    BookingStatus.PENDING,
    BookingStatus.ACCEPTED,
    BookingStatus.CONFIRMED,
    BookingStatus.ACTIVE,
)
# Links, handles and long digit runs are how contact details leak around the platform.
_CONTACT = re.compile(r'(https?:|://|www\.|t\.me|\.(com|uz|ru|org|net|me|io)\b|@\w)', re.IGNORECASE)
_MAX_DIGITS = 6


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def clean_caption(raw: str) -> str:
    caption = ' '.join(raw.split())
    if _CONTACT.search(caption) or sum(ch.isdigit() for ch in caption) > _MAX_DIGITS:
        raise ApplicationError(
            'story_caption_contact_info',
            'A story caption must not contain links, handles or phone numbers',
            422,
        )
    return caption


async def free_windows(
    session: AsyncSession, profile_id: UUID, now: datetime, until: datetime
) -> list[tuple[datetime, datetime]]:
    """Availability inside [now, until] minus bookings that still hold the slot."""
    availability = (
        await session.execute(
            select(CompanionAvailability.starts_at, CompanionAvailability.ends_at)
            .where(
                CompanionAvailability.profile_id == profile_id,
                CompanionAvailability.ends_at > now,
                CompanionAvailability.starts_at < until,
            )
            .order_by(CompanionAvailability.starts_at)
        )
    ).all()
    busy = sorted(
        (as_utc(start), as_utc(end))
        for start, end in (
            await session.execute(
                select(Booking.starts_at, Booking.ends_at).where(
                    Booking.profile_id == profile_id,
                    Booking.status.in_([status.value for status in SLOT_STATUSES]),
                    Booking.ends_at > now,
                    Booking.starts_at < until,
                )
            )
        ).all()
    )
    segments: list[tuple[datetime, datetime]] = []
    for raw_start, raw_end in availability:
        cursor, end = max(as_utc(raw_start), now), min(as_utc(raw_end), until)
        for busy_start, busy_end in busy:
            if busy_end <= cursor or busy_start >= end:
                continue
            if busy_start > cursor:
                segments.append((cursor, busy_start))
            cursor = max(cursor, busy_end)
        if cursor < end:
            segments.append((cursor, end))
    minimum = timedelta(minutes=MIN_FREE_MINUTES)
    return [(start, end) for start, end in segments if end - start >= minimum][:MAX_WINDOWS]


async def _parts(session: AsyncSession, story: CompanionStory):
    photo = None
    if story.photo_id is not None:
        photo = await session.scalar(
            select(CompanionPhoto).where(
                CompanionPhoto.id == story.photo_id,
                CompanionPhoto.profile_id == story.profile_id,
                CompanionPhoto.deleted_at.is_(None),
            )
        )
    offer = (
        await session.get(CompanionService, story.service_id)
        if story.service_id is not None
        else None
    )
    return (
        DiscoveryPhoto.model_validate(photo) if photo else None,
        DiscoveryService.model_validate(offer) if offer else None,
    )


def is_active(story: CompanionStory, now: datetime) -> bool:
    return story.removed_at is None and as_utc(story.expires_at) > now


async def slide_for(
    session: AsyncSession, story: CompanionStory, now: datetime
) -> StorySlide | None:
    """The public view; None when the card has nothing true to show (no free window left)."""
    photo, offer = await _parts(session, story)
    windows: list[StoryWindow] = []
    if story.kind == StoryKind.AVAILABILITY:
        found = await free_windows(session, story.profile_id, now, as_utc(story.expires_at))
        if not found:
            return None
        windows = [StoryWindow(starts_at=start, ends_at=end) for start, end in found]
    return StorySlide(
        id=story.id,
        kind=story.kind,
        caption=story.caption,
        created_at=story.created_at,
        expires_at=story.expires_at,
        photo=photo,
        service=offer,
        windows=windows,
    )


async def own_view(session: AsyncSession, story: CompanionStory, now: datetime) -> OwnStory:
    state = 'removed' if story.removed_at else 'active' if is_active(story, now) else 'expired'
    photo, offer = await _parts(session, story)
    windows: list[StoryWindow] = []
    if state == 'active' and story.kind == StoryKind.AVAILABILITY:
        found = await free_windows(session, story.profile_id, now, as_utc(story.expires_at))
        windows = [StoryWindow(starts_at=start, ends_at=end) for start, end in found]
    return OwnStory(
        id=story.id,
        kind=story.kind,
        caption=story.caption,
        created_at=story.created_at,
        expires_at=story.expires_at,
        photo=photo,
        service=offer,
        windows=windows,
        state=state,
        removal_note=story.removal_note if state == 'removed' else None,
    )


async def public_slides(
    session: AsyncSession, profile: CompanionProfile, now: datetime
) -> list[StorySlide]:
    stories = await session.scalars(
        select(CompanionStory)
        .where(
            CompanionStory.profile_id == profile.id,
            CompanionStory.removed_at.is_(None),
            CompanionStory.expires_at > now,
        )
        .order_by(CompanionStory.created_at, CompanionStory.id)
    )
    slides = [await slide_for(session, story, now) for story in stories]
    return [slide for slide in slides if slide is not None]
