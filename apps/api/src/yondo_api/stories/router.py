"""Stories: companions post (and delete) their own cards; everyone reads; customers report.

Reading is public like the discovery cards. No viewer is ever recorded, and a customer reports a
story by its id only: the server finds the account, the client never receives a user id.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import func, select

from yondo_api.api.errors import ApplicationError
from yondo_api.companions import service as companion_service
from yondo_api.companions.dependencies import Owner, Principal, Session
from yondo_api.companions.models import (
    CompanionApplication,
    CompanionPhoto,
    CompanionProfile,
    CompanionService,
)
from yondo_api.discovery.router import _public_candidates, _visible_rows
from yondo_api.discovery.schemas import DiscoveryPhoto
from yondo_api.safety.models import SafetyReport
from yondo_api.stories import service
from yondo_api.stories.models import CompanionStory, StoryKind
from yondo_api.stories.schemas import (
    OwnStory,
    StoryReportResponse,
    StoryReportWrite,
    StoryRing,
    StorySlide,
    StoryWrite,
)

owner_router = APIRouter(prefix='/companions/me/stories', tags=['companion stories'])
public_router = APIRouter(prefix='/discovery', tags=['stories'])
DAY = timedelta(hours=24)


def report_marker(story_id: UUID) -> str:
    return f'[story {story_id}]'


@owner_router.get('', response_model=list[OwnStory])
async def list_own_stories(owner: Owner, session: Session):
    """Active cards plus the last three days, so the owner sees why a card disappeared."""
    profile = await companion_service.profile_for(session, owner.id)
    now = datetime.now(UTC)
    stories = await session.scalars(
        select(CompanionStory)
        .where(
            CompanionStory.profile_id == profile.id,
            CompanionStory.created_at > now - timedelta(days=3),
        )
        .order_by(CompanionStory.created_at.desc(), CompanionStory.id)
    )
    return [await service.own_view(session, story, now) for story in stories]


@owner_router.post('', response_model=OwnStory, status_code=201)
async def create_story(payload: StoryWrite, request: Request, owner: Owner, session: Session):
    profile = await companion_service.profile_for(session, owner.id)  # row lock: serialises quotas
    status = await companion_service.companion_status(
        session, owner, profile, request.app.state.identity_eligibility
    )
    if not status.publicly_active:
        raise ApplicationError(
            'story_profile_not_active', 'Stories need an active public profile', 409
        )
    caption = service.clean_caption(payload.caption)
    if payload.kind == StoryKind.NOTE and not caption:
        raise ApplicationError('story_caption_required', 'A note needs a caption', 422)
    if payload.photo_id is not None:
        await companion_service.owned_resource(
            session, CompanionPhoto, payload.photo_id, profile.id
        )
    if payload.service_id is not None:
        await companion_service.owned_resource(
            session, CompanionService, payload.service_id, profile.id
        )
    settings = request.app.state.settings
    now = datetime.now(UTC)
    active = await session.scalar(
        select(func.count())
        .select_from(CompanionStory)
        .where(
            CompanionStory.profile_id == profile.id,
            CompanionStory.removed_at.is_(None),
            CompanionStory.expires_at > now,
        )
    )
    if active >= settings.stories_max_active:
        raise ApplicationError('story_limit_reached', 'Too many active stories', 409)
    recent = await session.scalar(
        select(func.count())
        .select_from(CompanionStory)
        .where(CompanionStory.profile_id == profile.id, CompanionStory.created_at > now - DAY)
    )
    if recent >= settings.stories_max_per_day:
        raise ApplicationError('story_rate_limited', 'Too many stories posted today', 429)
    expires_at = now + timedelta(hours=settings.stories_ttl_hours)
    if payload.kind == StoryKind.AVAILABILITY and not await service.free_windows(
        session, profile.id, now, expires_at
    ):
        raise ApplicationError(
            'story_no_free_windows', 'There is no free time to show in the next 24 hours', 409
        )
    story = CompanionStory(
        profile_id=profile.id,
        kind=payload.kind,
        caption=caption,
        photo_id=payload.photo_id,
        service_id=payload.service_id,
        expires_at=expires_at,
    )
    session.add(story)
    await session.commit()
    await session.refresh(story)
    return await service.own_view(session, story, now)


@owner_router.delete('/{story_id}', status_code=204)
async def delete_own_story(story_id: UUID, owner: Owner, session: Session):
    profile = await companion_service.profile_for(session, owner.id)
    story = await companion_service.owned_resource(session, CompanionStory, story_id, profile.id)
    if story.removed_at is None:
        story.removed_at = datetime.now(UTC)
        story.removed_by = owner.id
        await session.commit()
    return Response(status_code=204)


@public_router.get('/stories', response_model=list[StoryRing])
async def story_rings(
    request: Request, session: Session, limit: int = Query(default=30, ge=1, le=50)
):
    """Companions with at least one card that still shows something true, newest first."""
    now = datetime.now(UTC)
    with_cards = (
        select(CompanionStory.profile_id)
        .where(CompanionStory.removed_at.is_(None), CompanionStory.expires_at > now)
        .group_by(CompanionStory.profile_id)
        .order_by(func.max(CompanionStory.created_at).desc())
        .limit(limit * 2)
    )
    rows = await _visible_rows(
        request, session, _public_candidates().where(CompanionProfile.id.in_(with_cards))
    )
    rings = []
    for profile, _user in rows:
        slides = await service.public_slides(session, profile, now)
        if not slides:
            continue
        photo = await session.scalar(
            select(CompanionPhoto)
            .where(CompanionPhoto.profile_id == profile.id, CompanionPhoto.deleted_at.is_(None))
            .order_by(CompanionPhoto.position)
            .limit(1)
        )
        rings.append(
            StoryRing(
                profile_id=profile.id,
                display_name=profile.display_name,
                photo=DiscoveryPhoto.model_validate(photo) if photo else None,
                count=len(slides),
                latest_at=max(slide.created_at for slide in slides),
                has_availability=any(slide.kind == StoryKind.AVAILABILITY for slide in slides),
            )
        )
    rings.sort(key=lambda ring: ring.latest_at, reverse=True)
    return rings[:limit]


@public_router.get('/companions/{profile_id}/stories', response_model=list[StorySlide])
async def companion_stories(profile_id: UUID, request: Request, session: Session):
    rows = await _visible_rows(
        request, session, _public_candidates().where(CompanionProfile.id == profile_id)
    )
    if not rows:
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    return await service.public_slides(session, rows[0][0], datetime.now(UTC))


@public_router.post(
    '/stories/{story_id}/report', response_model=StoryReportResponse, status_code=201
)
async def report_story(
    story_id: UUID, payload: StoryReportWrite, principal: Principal, session: Session
):
    now = datetime.now(UTC)
    story = await session.get(CompanionStory, story_id)
    if story is None or not service.is_active(story, now):
        raise ApplicationError('story_not_found', 'Story not found', 404)
    author_id = await session.scalar(
        select(CompanionApplication.user_id)
        .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
        .where(CompanionProfile.id == story.profile_id)
    )
    if author_id is None:
        raise ApplicationError('story_not_found', 'Story not found', 404)
    if author_id == principal.user.id:
        raise ApplicationError('invalid_report', 'Cannot report own story', 422)
    marker = report_marker(story.id)
    already = await session.scalar(
        select(SafetyReport.id).where(
            SafetyReport.reporter_id == principal.user.id,
            SafetyReport.description.startswith(marker),
        )
    )
    if already is not None:
        raise ApplicationError('story_already_reported', 'You already reported this story', 409)
    report = SafetyReport(
        reporter_id=principal.user.id,
        reported_user_id=author_id,
        booking_id=None,
        category=payload.category,
        description=f'{marker} {payload.description.strip()}'.strip(),
        status='open',
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return StoryReportResponse(id=report.id, status=report.status)
