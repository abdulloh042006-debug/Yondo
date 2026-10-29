"""Admin moderation of stories: list (with report counts) and remove with a written reason."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from yondo_api.admin.models import AdminAuditEvent
from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Admin, Session
from yondo_api.companions.models import CompanionApplication, CompanionProfile
from yondo_api.safety.models import SafetyReport
from yondo_api.stories import service
from yondo_api.stories.models import CompanionStory
from yondo_api.stories.router import report_marker
from yondo_api.stories.schemas import AdminStory, StoryRemove

router = APIRouter(prefix='/stories/admin', tags=['stories admin'])


async def _admin_view(session, story: CompanionStory, name: str, now: datetime) -> AdminStory:
    reports = await session.scalar(
        select(func.count())
        .select_from(SafetyReport)
        .where(SafetyReport.description.startswith(report_marker(story.id)))
    )
    active = service.is_active(story, now)
    state = 'removed' if story.removed_at else 'active' if active else 'expired'
    return AdminStory(
        id=story.id,
        profile_id=story.profile_id,
        display_name=name,
        kind=story.kind,
        caption=story.caption,
        created_at=story.created_at,
        expires_at=story.expires_at,
        state=state,
        removed_at=story.removed_at,
        removal_note=story.removal_note,
        report_count=reports,
    )


@router.get('', response_model=list[AdminStory])
async def list_stories(
    admin: Admin,
    session: Session,
    state: Literal['active', 'removed', 'all'] = 'active',
    limit: int = Query(default=50, ge=1, le=200),
):
    now = datetime.now(UTC)
    query = select(CompanionStory, CompanionProfile.display_name).join(
        CompanionProfile, CompanionProfile.id == CompanionStory.profile_id
    )
    if state == 'active':
        query = query.where(CompanionStory.removed_at.is_(None), CompanionStory.expires_at > now)
    elif state == 'removed':
        query = query.where(CompanionStory.removed_at.is_not(None))
    rows = (
        await session.execute(
            query.order_by(CompanionStory.created_at.desc(), CompanionStory.id).limit(limit)
        )
    ).all()
    return [await _admin_view(session, story, name, now) for story, name in rows]


@router.post('/{story_id}/remove', response_model=AdminStory)
async def remove_story(story_id: UUID, payload: StoryRemove, admin: Admin, session: Session):
    story = await session.get(CompanionStory, story_id, with_for_update=True)
    if story is None:
        raise ApplicationError('story_not_found', 'Story not found', 404)
    if story.removed_at is not None:
        raise ApplicationError('story_already_removed', 'Story is already removed', 409)
    profile = await session.get(CompanionProfile, story.profile_id)
    author_id = await session.scalar(
        select(CompanionApplication.user_id).where(
            CompanionApplication.id == profile.application_id
        )
    )
    now = datetime.now(UTC)
    story.removed_at = now
    story.removed_by = admin.id
    story.removal_note = payload.note
    session.add(
        AdminAuditEvent(
            admin_id=admin.id, target_id=author_id, action='story:remove', reason=payload.note
        )
    )
    await session.commit()
    await session.refresh(story)
    return await _admin_view(session, story, profile.display_name, now)
