from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Request
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.integrations import verified_user_ids
from yondo_api.companions.models import (
    CompanionApplication,
    CompanionAvailability,
    CompanionPhoto,
    CompanionProfile,
    CompanionService,
)
from yondo_api.companions.service import public_profile_conditions
from yondo_api.core.time import as_utc, utc_now
from yondo_api.discovery.models import FavoriteCompanion
from yondo_api.discovery.schemas import (
    AvailabilitySlot,
    CompanionCard,
    CompanionStats,
    DiscoveryFilters,
    PhotoView,
    PublicProfile,
    ServiceSummary,
)
from yondo_api.discovery.stats import badges_for, companion_stats
from yondo_api.models.user import User

# MVP scale bound for in-memory filtering/sorting of the public candidate set.
MAX_CANDIDATES = 2000
PUBLIC_PHOTO_URL_SECONDS = 3600
PROFILE_AVAILABILITY_DAYS = 14


@dataclass(slots=True)
class Candidate:
    profile: CompanionProfile
    user: User
    services: list[CompanionService]
    distance_km: float | None = None
    stats: CompanionStats | None = None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _escape_like(value: str) -> str:
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def local_day_bounds(day: date, timezone: str) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone)
    start = datetime.combine(day, time.min, tzinfo=zone)
    return as_utc(start), as_utc(start + timedelta(days=1))


async def excluded_user_ids(session: AsyncSession, viewer_id: UUID) -> set[UUID]:
    """Users hidden from the viewer: themselves plus any block in either direction."""
    from yondo_api.safety.service import blocked_either_way

    return {viewer_id} | await blocked_either_way(session, viewer_id)


async def public_candidates(
    session: AsyncSession,
    request: Request,
    viewer: User,
    filters: DiscoveryFilters,
) -> list[Candidate]:
    settings = request.app.state.settings
    query = (
        select(CompanionProfile, User)
        .join(CompanionApplication, CompanionProfile.application_id == CompanionApplication.id)
        .join(User, CompanionApplication.user_id == User.id)
        .where(public_profile_conditions())
    )
    excluded = await excluded_user_ids(session, viewer.id)
    query = query.where(User.id.not_in(excluded))
    if filters.q:
        pattern = f'%{_escape_like(filters.q)}%'
        query = query.where(
            or_(
                CompanionProfile.display_name.ilike(pattern, escape='\\'),
                CompanionProfile.bio.ilike(pattern, escape='\\'),
            )
        )
    if filters.gender:
        query = query.where(func.lower(User.gender) == filters.gender.lower())
    if filters.city:
        query = query.where(func.lower(User.city) == filters.city.lower())
    if filters.age_min is not None:
        query = query.where(User.age >= filters.age_min)
    if filters.age_max is not None:
        query = query.where(User.age <= filters.age_max)
    if filters.service or filters.price_min is not None or filters.price_max is not None:
        service_conditions = [CompanionService.profile_id == CompanionProfile.id]
        if filters.service:
            service_conditions.append(CompanionService.service_code == filters.service)
        if filters.price_min is not None:
            service_conditions.append(CompanionService.price_minor >= filters.price_min)
        if filters.price_max is not None:
            service_conditions.append(CompanionService.price_minor <= filters.price_max)
        if filters.currency:
            service_conditions.append(CompanionService.currency == filters.currency)
        query = query.where(exists().where(*service_conditions))
    if filters.available_on is not None:
        start, end = local_day_bounds(filters.available_on, settings.booking_default_timezone)
        start = max(start, utc_now())
        query = query.where(
            exists().where(
                CompanionAvailability.profile_id == CompanionProfile.id,
                CompanionAvailability.starts_at < end,
                CompanionAvailability.ends_at > start,
            )
        )
    if filters.favorites_only:
        query = query.where(
            exists().where(
                FavoriteCompanion.profile_id == CompanionProfile.id,
                FavoriteCompanion.user_id == viewer.id,
            )
        )
    if filters.latitude is not None and filters.radius_km is not None:
        # Bounding box prefilter; the exact great-circle distance is applied below.
        delta_lat = filters.radius_km / 111.0
        delta_lon = filters.radius_km / max(
            111.0 * math.cos(math.radians(filters.latitude)), 0.001
        )
        query = query.where(
            CompanionProfile.approx_latitude.between(
                filters.latitude - delta_lat, filters.latitude + delta_lat
            ),
            CompanionProfile.approx_longitude.between(
                filters.longitude - delta_lon, filters.longitude + delta_lon
            ),
        )
    rows = list((await session.execute(query.limit(MAX_CANDIDATES))).all())
    if not rows:
        return []
    verified = await verified_identities(session, request, [user.id for _, user in rows])
    rows = [(profile, user) for profile, user in rows if user.id in verified]
    language = filters.language.casefold() if filters.language else None
    interest = filters.interest.casefold() if filters.interest else None
    candidates: list[Candidate] = []
    services = await services_by_profile(session, [profile.id for profile, _ in rows])
    for profile, user in rows:
        if language and language not in {item.casefold() for item in profile.languages}:
            continue
        if interest and interest not in {item.casefold() for item in profile.interests}:
            continue
        candidate = Candidate(profile=profile, user=user, services=services.get(profile.id, []))
        if filters.latitude is not None:
            if profile.approx_latitude is not None and profile.approx_longitude is not None:
                candidate.distance_km = round(
                    haversine_km(
                        filters.latitude,
                        filters.longitude,
                        profile.approx_latitude,
                        profile.approx_longitude,
                    ),
                    1,
                )
            if filters.radius_km is not None and (
                candidate.distance_km is None or candidate.distance_km > filters.radius_km
            ):
                continue
        candidates.append(candidate)
    stats = await companion_stats(session, [candidate.user.id for candidate in candidates])
    for candidate in candidates:
        candidate.stats = stats.get(candidate.user.id, CompanionStats())
    if filters.rating_min is not None:
        candidates = [
            candidate
            for candidate in candidates
            if candidate.stats.rating_average is not None
            and candidate.stats.rating_average >= filters.rating_min
        ]
    sort_candidates(candidates, filters)
    return candidates


async def verified_identities(
    session: AsyncSession, request: Request, user_ids: list[UUID]
) -> set[UUID]:
    try:
        return await verified_user_ids(request.app.state.identity_eligibility, session, user_ids)
    except Exception as exc:
        raise ApplicationError(
            'identity_status_unavailable', 'Identity eligibility is currently unavailable', 503
        ) from exc


def _min_price(candidate: Candidate, service_code: str | None) -> int | None:
    prices = [
        item.price_minor
        for item in candidate.services
        if service_code is None or item.service_code == service_code
    ]
    return min(prices) if prices else None


def sort_candidates(candidates: list[Candidate], filters: DiscoveryFilters) -> None:
    newest = lambda c: as_utc(c.profile.created_at).timestamp()  # noqa: E731
    rating = lambda c: (c.stats.rating_average or 0.0, c.stats.rating_count)  # noqa: E731
    if filters.sort == 'newest':
        candidates.sort(key=newest, reverse=True)
    elif filters.sort == 'rating':
        candidates.sort(key=lambda c: (*rating(c), newest(c)), reverse=True)
    elif filters.sort in {'price_asc', 'price_desc'}:
        missing = math.inf if filters.sort == 'price_asc' else -math.inf
        candidates.sort(
            key=lambda c: (
                _min_price(c, filters.service)
                if _min_price(c, filters.service) is not None
                else missing
            ),
            reverse=filters.sort == 'price_desc',
        )
    elif filters.sort == 'distance':
        candidates.sort(key=lambda c: c.distance_km if c.distance_km is not None else math.inf)
    else:
        # Recommended: rating quality, then completed experience, then freshness.
        candidates.sort(
            key=lambda c: (
                c.stats.rating_average or 0.0,
                c.stats.completed_bookings,
                newest(c),
            ),
            reverse=True,
        )


async def services_by_profile(
    session: AsyncSession, profile_ids: list[UUID]
) -> dict[UUID, list[CompanionService]]:
    result: dict[UUID, list[CompanionService]] = {}
    if not profile_ids:
        return result
    for item in await session.scalars(
        select(CompanionService)
        .where(CompanionService.profile_id.in_(profile_ids))
        .order_by(CompanionService.price_minor, CompanionService.service_code)
    ):
        result.setdefault(item.profile_id, []).append(item)
    return result


async def photo_view(request: Request, photo: CompanionPhoto) -> PhotoView:
    storage = request.app.state.object_storage
    url = None
    if storage is not None:
        try:
            url = await storage.create_download_url(photo.storage_key, PUBLIC_PHOTO_URL_SECONDS)
        except Exception:
            url = None
    return PhotoView(
        id=photo.id, url=url, width=photo.width, height=photo.height, caption=photo.caption
    )


async def primary_photos(
    session: AsyncSession, request: Request, profile_ids: list[UUID]
) -> dict[UUID, PhotoView]:
    photos: dict[UUID, CompanionPhoto] = {}
    if profile_ids:
        for photo in await session.scalars(
            select(CompanionPhoto)
            .where(
                CompanionPhoto.profile_id.in_(profile_ids), CompanionPhoto.deleted_at.is_(None)
            )
            .order_by(CompanionPhoto.profile_id, CompanionPhoto.position)
        ):
            photos.setdefault(photo.profile_id, photo)
    return {profile_id: await photo_view(request, photo) for profile_id, photo in photos.items()}


async def favorite_profile_ids(session: AsyncSession, viewer_id: UUID) -> set[UUID]:
    return set(
        await session.scalars(
            select(FavoriteCompanion.profile_id).where(FavoriteCompanion.user_id == viewer_id)
        )
    )


async def build_cards(
    session: AsyncSession,
    request: Request,
    viewer: User,
    candidates: list[Candidate],
    service_code: str | None = None,
) -> list[CompanionCard]:
    profile_ids = [candidate.profile.id for candidate in candidates]
    photos = await primary_photos(session, request, profile_ids)
    favorites = await favorite_profile_ids(session, viewer.id)
    cards = []
    for candidate in candidates:
        stats = candidate.stats or CompanionStats()
        price = _min_price(candidate, service_code)
        currency = next(
            (item.currency for item in candidate.services if item.price_minor == price), None
        )
        cards.append(
            CompanionCard(
                profile_id=candidate.profile.id,
                display_name=candidate.profile.display_name,
                age=candidate.user.age,
                gender=candidate.user.gender,
                city=candidate.user.city,
                area=candidate.profile.area,
                primary_photo=photos.get(candidate.profile.id),
                services=sorted({item.service_code for item in candidate.services}),
                min_price_minor=price,
                currency=currency,
                distance_km=candidate.distance_km,
                is_favorite=candidate.profile.id in favorites,
                badges=badges_for(stats),
                stats=stats,
            )
        )
    return cards


async def public_candidate(
    session: AsyncSession, request: Request, viewer: User, profile_id: UUID
) -> Candidate:
    """Load one publicly visible companion or raise 404 (never reveal hidden profiles)."""
    row = (
        await session.execute(
            select(CompanionProfile, User)
            .join(
                CompanionApplication,
                CompanionProfile.application_id == CompanionApplication.id,
            )
            .join(User, CompanionApplication.user_id == User.id)
            .where(public_profile_conditions(), CompanionProfile.id == profile_id)
        )
    ).first()
    if row is None or row[1].id in await excluded_user_ids(session, viewer.id):
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    profile, user = row
    if user.id not in await verified_identities(session, request, [user.id]):
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    services = await services_by_profile(session, [profile.id])
    stats = await companion_stats(session, [user.id])
    return Candidate(
        profile=profile,
        user=user,
        services=services.get(profile.id, []),
        stats=stats.get(user.id, CompanionStats()),
    )


async def busy_intervals(
    session: AsyncSession, companion_user_id: UUID, start: datetime, end: datetime
) -> list[tuple[datetime, datetime]]:
    # Reservations are introduced by the booking engine (Phase 8).
    return []


def subtract_intervals(
    window: tuple[datetime, datetime], busy: list[tuple[datetime, datetime]]
) -> list[tuple[datetime, datetime]]:
    free = [window]
    for busy_start, busy_end in sorted(busy):
        next_free = []
        for free_start, free_end in free:
            if busy_end <= free_start or busy_start >= free_end:
                next_free.append((free_start, free_end))
                continue
            if busy_start > free_start:
                next_free.append((free_start, busy_start))
            if busy_end < free_end:
                next_free.append((busy_end, free_end))
        free = next_free
    return free


async def free_slots(
    session: AsyncSession,
    profile_id: UUID,
    companion_user_id: UUID,
    start: datetime,
    end: datetime,
) -> list[AvailabilitySlot]:
    windows = list(
        await session.scalars(
            select(CompanionAvailability)
            .where(
                CompanionAvailability.profile_id == profile_id,
                CompanionAvailability.starts_at < end,
                CompanionAvailability.ends_at > start,
            )
            .order_by(CompanionAvailability.starts_at)
        )
    )
    busy = await busy_intervals(session, companion_user_id, start, end)
    slots = []
    for window in windows:
        clipped = (max(as_utc(window.starts_at), start), min(as_utc(window.ends_at), end))
        for slot_start, slot_end in subtract_intervals(clipped, busy):
            if slot_end > slot_start:
                slots.append(
                    AvailabilitySlot(
                        starts_at=slot_start, ends_at=slot_end, timezone=window.timezone
                    )
                )
    return slots


async def public_profile(
    session: AsyncSession, request: Request, viewer: User, profile_id: UUID
) -> PublicProfile:
    candidate = await public_candidate(session, request, viewer, profile_id)
    card = (await build_cards(session, request, viewer, [candidate]))[0]
    photos = [
        await photo_view(request, photo)
        for photo in await session.scalars(
            select(CompanionPhoto)
            .where(
                CompanionPhoto.profile_id == profile_id, CompanionPhoto.deleted_at.is_(None)
            )
            .order_by(CompanionPhoto.position)
        )
    ]
    now = utc_now()
    availability = await free_slots(
        session,
        profile_id,
        candidate.user.id,
        now,
        now + timedelta(days=PROFILE_AVAILABILITY_DAYS),
    )
    return PublicProfile(
        **card.model_dump(),
        bio=candidate.profile.bio,
        languages=candidate.profile.languages,
        interests=candidate.profile.interests,
        photos=photos,
        service_details=[ServiceSummary.model_validate(item) for item in candidate.services],
        availability=availability,
        member_since=candidate.user.created_at,
    )
