from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from sqlalchemy import select

from yondo_api.api.errors import ApplicationError
from yondo_api.companions import service
from yondo_api.companions.dependencies import Admin, Session
from yondo_api.companions.models import (
    CompanionApplication,
    CompanionPhoto,
    CompanionProfile,
    CompanionService,
)
from yondo_api.companions.photos import download_url, visible_photos
from yondo_api.companions.schemas import (
    ApplicationResponse,
    ApprovalDecision,
    ContentReview,
    PhotoDownload,
    PhotoResponse,
    ProfileResponse,
    ServiceResponse,
)

router = APIRouter(prefix='/companions/admin', tags=['companion approval'])


class AdminApplicationSummary(BaseModel):
    """Queue row: lifecycle state only, no private profile content."""

    id: UUID
    user_id: UUID
    status: str
    revision: int
    submitted_at: datetime | None
    reviewed_at: datetime | None
    reviewed_by: UUID | None
    review_note: str | None
    created_at: datetime
    profile_id: UUID | None
    display_name: str | None
    content_status: str | None
    content_revision: int | None


@router.get('/applications', response_model=list[AdminApplicationSummary])
async def list_applications(
    admin: Admin,
    session: Session,
    status: Literal['draft', 'submitted', 'approved', 'rejected', 'withdrawn'] | None = None,
    content_status: Literal['draft', 'pending', 'approved', 'rejected'] | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(CompanionApplication, CompanionProfile).outerjoin(
        CompanionProfile, CompanionProfile.application_id == CompanionApplication.id
    )
    if status is not None:
        query = query.where(CompanionApplication.status == status)
    if content_status is not None:
        query = query.where(CompanionProfile.content_status == content_status)
    rows = (
        await session.execute(
            query.order_by(
                CompanionApplication.created_at.desc(), CompanionApplication.id.desc()
            )
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return [
        AdminApplicationSummary(
            id=application.id,
            user_id=application.user_id,
            status=application.status,
            revision=application.revision,
            submitted_at=application.submitted_at,
            reviewed_at=application.reviewed_at,
            reviewed_by=application.reviewed_by,
            review_note=application.review_note,
            created_at=application.created_at,
            profile_id=profile.id if profile else None,
            display_name=profile.display_name if profile else None,
            content_status=profile.content_status if profile else None,
            content_revision=profile.revision if profile else None,
        )
        for application, profile in rows
    ]


@router.get('/applications/{application_id}', response_model=ApplicationResponse)
async def read_application(application_id: UUID, admin: Admin, session: Session):
    item = await session.get(CompanionApplication, application_id)
    if item is None:
        raise ApplicationError('application_not_found', 'Companion application not found', 404)
    return item


@router.post('/applications/{application_id}/decision', response_model=ApplicationResponse)
async def decide_application(
    application_id: UUID,
    payload: ApprovalDecision,
    admin: Admin,
    session: Session,
):
    return await service.review_application(
        session,
        application_id,
        admin,
        payload.decision,
        payload.note,
        payload.expected_revision,
    )


@router.get('/users/{user_id}/profile', response_model=ProfileResponse)
async def read_profile(user_id: UUID, admin: Admin, session: Session):
    return await service.profile_for(session, user_id)


@router.get('/users/{user_id}/services', response_model=list[ServiceResponse])
async def read_services(user_id: UUID, admin: Admin, session: Session):
    profile = await service.profile_for(session, user_id)
    return list(
        await session.scalars(
            select(CompanionService)
            .where(CompanionService.profile_id == profile.id)
            .order_by(CompanionService.service_code)
        )
    )


@router.get('/users/{user_id}/photos', response_model=list[PhotoResponse])
async def read_photos(user_id: UUID, admin: Admin, session: Session):
    profile = await service.profile_for(session, user_id)
    return await visible_photos(session, profile.id)


@router.get('/users/{user_id}/photos/{photo_id}/download', response_model=PhotoDownload)
async def read_photo(
    user_id: UUID,
    photo_id: UUID,
    request: Request,
    admin: Admin,
    session: Session,
):
    profile = await service.profile_for(session, user_id)
    item = await service.owned_resource(session, CompanionPhoto, photo_id, profile.id)
    return await download_url(request, item)


@router.post('/profiles/{profile_id}/decision', response_model=ProfileResponse)
async def decide_profile(
    profile_id: UUID, payload: ApprovalDecision, admin: Admin, session: Session
):
    return await service.review_content(
        session, profile_id, admin, payload.decision, payload.note, payload.expected_revision
    )


@router.get('/users/{user_id}/content-review', response_model=ContentReview)
async def read_content_review(user_id: UUID, admin: Admin, session: Session):
    # Serialize the entire review snapshot with all owner aggregate mutations.
    await service.locked_user(session, user_id)
    profile = await service.profile_for(session, user_id)
    return ContentReview(
        profile=ProfileResponse.model_validate(profile),
        services=[
            ServiceResponse.model_validate(item)
            for item in await read_services(user_id, admin, session)
        ],
        photos=[
            PhotoResponse.model_validate(item) for item in await visible_photos(session, profile.id)
        ],
    )
