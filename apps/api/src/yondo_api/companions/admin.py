from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import select

from yondo_api.api.errors import ApplicationError
from yondo_api.companions import service
from yondo_api.companions.dependencies import Admin, Session
from yondo_api.companions.models import CompanionApplication, CompanionPhoto, CompanionService
from yondo_api.companions.photos import download_url, visible_photos
from yondo_api.companions.schemas import (
    ApplicationResponse,
    ApprovalDecision,
    PhotoDownload,
    PhotoResponse,
    ProfileResponse,
    ServiceResponse,
)

router = APIRouter(prefix='/companions/admin', tags=['companion approval'])


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
    return await service.review_content(session, profile_id, admin, payload.decision, payload.note)
