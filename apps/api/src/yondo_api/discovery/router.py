from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import delete

from yondo_api.core.db import commit
from yondo_api.core.deps import CurrentUser, Session
from yondo_api.core.time import utc_now
from yondo_api.discovery import service
from yondo_api.discovery.models import FavoriteCompanion
from yondo_api.discovery.schemas import (
    AvailabilitySlot,
    CompanionCard,
    DiscoveryFilters,
    ExperienceCount,
    HomeResponse,
    HomeSection,
    PublicProfile,
    SearchResult,
)

router = APIRouter(prefix='/discovery', tags=['discovery'])
favorites_router = APIRouter(prefix='/favorites', tags=['favorites'])
HOME_SECTION_SIZE = 10


@router.get('/companions', response_model=SearchResult)
async def search(
    filters: Annotated[DiscoveryFilters, Query()],
    request: Request,
    viewer: CurrentUser,
    session: Session,
):
    candidates = await service.public_candidates(session, request, viewer, filters)
    page = candidates[filters.offset : filters.offset + filters.limit]
    has_more = filters.offset + filters.limit < len(candidates)
    return SearchResult(
        items=await service.build_cards(session, request, viewer, page, filters.service),
        total=len(candidates),
        next_offset=filters.offset + filters.limit if has_more else None,
    )


@router.get('/home', response_model=HomeResponse)
async def home(
    request: Request,
    viewer: CurrentUser,
    session: Session,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    city: Annotated[str | None, Query(max_length=128)] = None,
):
    """TZ §6 home sections. Gift sections are served by the gifts catalog."""
    location = (
        {'latitude': latitude, 'longitude': longitude}
        if latitude is not None and longitude is not None
        else {}
    )
    base = DiscoveryFilters(city=city or viewer.city, **location)
    candidates = await service.public_candidates(session, request, viewer, base)
    if not candidates and base.city:
        # Fall back to every city rather than an empty home screen.
        base = base.model_copy(update={'city': None})
        candidates = await service.public_candidates(session, request, viewer, base)
    sections: list[tuple[str, str, list[service.Candidate]]] = []
    today = (
        utc_now()
        .astimezone(service.ZoneInfo(request.app.state.settings.booking_default_timezone))
        .date()
    )
    available = await service.public_candidates(
        session, request, viewer, base.model_copy(update={'available_on': today})
    )
    sections.append(('available_today', 'Available Today', available))
    if location:
        nearby = sorted(
            (c for c in candidates if c.distance_km is not None), key=lambda c: c.distance_km
        )
        sections.append(('nearby', 'Nearby', nearby))
    rated = [c for c in candidates if c.stats.rating_count > 0]
    rated.sort(key=lambda c: (c.stats.rating_average, c.stats.rating_count), reverse=True)
    sections.append(('top_rated', 'Top Rated', rated))
    newest = sorted(candidates, key=lambda c: service.as_utc(c.profile.created_at), reverse=True)
    sections.append(('new_companions', 'New Companions', newest))
    sections.append(('recommended', 'Recommended', candidates))
    experiences = Counter(
        code for c in candidates for code in {item.service_code for item in c.services}
    )
    return HomeResponse(
        sections=[
            HomeSection(
                key=key,
                title=title,
                items=await service.build_cards(
                    session, request, viewer, items[:HOME_SECTION_SIZE]
                ),
            )
            for key, title, items in sections
        ],
        popular_experiences=[
            ExperienceCount(service_code=code, companions=count)
            for code, count in experiences.most_common()
        ],
    )


@router.get('/companions/{profile_id}', response_model=PublicProfile)
async def companion_profile(
    profile_id: UUID, request: Request, viewer: CurrentUser, session: Session
):
    return await service.public_profile(session, request, viewer, profile_id)


@router.get('/companions/{profile_id}/availability', response_model=list[AvailabilitySlot])
async def companion_availability(
    profile_id: UUID,
    request: Request,
    viewer: CurrentUser,
    session: Session,
    days: Annotated[int, Query(ge=1, le=60)] = 14,
):
    candidate = await service.public_candidate(session, request, viewer, profile_id)
    now = utc_now()
    return await service.free_slots(
        session, profile_id, candidate.user.id, now, now + timedelta(days=days)
    )


@favorites_router.get('/companions', response_model=list[CompanionCard])
async def list_favorites(request: Request, viewer: CurrentUser, session: Session):
    candidates = await service.public_candidates(
        session, request, viewer, DiscoveryFilters(favorites_only=True, sort='newest')
    )
    return await service.build_cards(session, request, viewer, candidates)


@favorites_router.put('/companions/{profile_id}', status_code=204)
async def add_favorite(profile_id: UUID, request: Request, viewer: CurrentUser, session: Session):
    await service.public_candidate(session, request, viewer, profile_id)
    exists = await session.get(FavoriteCompanion, (viewer.id, profile_id))
    if exists is None:
        session.add(FavoriteCompanion(user_id=viewer.id, profile_id=profile_id))
        await commit(session)
    return Response(status_code=204)


@favorites_router.delete('/companions/{profile_id}', status_code=204)
async def remove_favorite(profile_id: UUID, viewer: CurrentUser, session: Session):
    await session.execute(
        delete(FavoriteCompanion).where(
            FavoriteCompanion.user_id == viewer.id, FavoriteCompanion.profile_id == profile_id
        )
    )
    await commit(session)
    return Response(status_code=204)
