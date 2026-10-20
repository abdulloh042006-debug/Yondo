from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from yondo_api.companions import service
from yondo_api.companions.dependencies import Owner, Session
from yondo_api.companions.models import (
    ApplicationStatus,
    CompanionApplication,
    CompanionProfile,
    ContentStatus,
)
from yondo_api.companions.schemas import (
    ApplicationResponse,
    ApplicationWrite,
    CompanionStatus,
    ProfileResponse,
    ProfileWrite,
)

router = APIRouter(prefix='/companions/me', tags=['companions'])


@router.post('/application', response_model=ApplicationResponse, status_code=201)
async def create_application(payload: ApplicationWrite, owner: Owner, session: Session):
    application = CompanionApplication(user_id=owner.id, **payload.model_dump())
    session.add(application)
    await service.save(session)
    return application


@router.get('/application', response_model=ApplicationResponse)
async def get_application(owner: Owner, session: Session):
    return await service.application_for(session, owner.id)


@router.put('/application', response_model=ApplicationResponse)
async def edit_application(payload: ApplicationWrite, owner: Owner, session: Session):
    application = await service.application_for(session, owner.id)
    if application.status not in {
        ApplicationStatus.DRAFT,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }:
        raise service.conflict('Only a draft, rejected or withdrawn application can be edited')
    application.revision += 1
    application.statement = payload.statement
    application.status = ApplicationStatus.DRAFT
    application.review_note = application.reviewed_at = application.reviewed_by = None
    await service.save(session)
    return application


@router.post('/application/submit', response_model=ApplicationResponse)
async def submit_application(owner: Owner, session: Session):
    application = await service.application_for(session, owner.id)
    if application.status != ApplicationStatus.DRAFT:
        raise service.conflict('Only a draft application can be submitted')
    application.revision += 1
    application.status = ApplicationStatus.SUBMITTED
    application.submitted_at = datetime.now(UTC)
    await service.save(session)
    return application


@router.post('/application/withdraw', response_model=ApplicationResponse)
async def withdraw_application(owner: Owner, session: Session):
    application = await service.application_for(session, owner.id)
    if application.status == ApplicationStatus.WITHDRAWN:
        raise service.conflict('Application is already withdrawn')
    application.revision += 1
    application.status = ApplicationStatus.WITHDRAWN
    profile = await session.scalar(
        select(CompanionProfile).where(CompanionProfile.application_id == application.id)
    )
    if profile is not None:
        profile.activation_requested = False
    await service.save(session)
    return application


@router.post('/profile', response_model=ProfileResponse, status_code=201)
async def create_profile(payload: ProfileWrite, owner: Owner, session: Session):
    application = await service.application_for(session, owner.id)
    profile = CompanionProfile(application_id=application.id, **payload.model_dump())
    session.add(profile)
    await service.save(session)
    return profile


@router.get('/profile', response_model=ProfileResponse)
async def get_profile(owner: Owner, session: Session):
    return await service.profile_for(session, owner.id)


@router.put('/profile', response_model=ProfileResponse)
async def update_profile(payload: ProfileWrite, owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    service.invalidate_content(profile)
    await service.save(session)
    return profile


@router.post('/profile/submit', response_model=ProfileResponse)
async def submit_profile(owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    if profile.content_status not in {ContentStatus.DRAFT, ContentStatus.REJECTED}:
        raise service.conflict('Only draft or rejected content can be submitted')
    profile.revision += 1
    profile.content_status = ContentStatus.PENDING
    profile.activation_requested = False
    await service.save(session)
    return profile


@router.get('/status', response_model=CompanionStatus)
async def get_status(request: Request, owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    return await service.companion_status(
        session,
        owner,
        profile,
        request.app.state.identity_eligibility,
    )


@router.post('/activate', response_model=CompanionStatus)
async def activate(request: Request, owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    eligibility = await service.companion_status(
        session,
        owner,
        profile,
        request.app.state.identity_eligibility,
    )
    if eligibility.blockers or profile.activation_requested:
        raise service.conflict('Activation requires all approval gates and an inactive profile')
    profile.activation_requested = True
    await service.save(session)
    return eligibility.model_copy(update={'activation_requested': True, 'publicly_active': True})


@router.post('/deactivate', status_code=204)
async def deactivate(owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    if not profile.activation_requested:
        raise service.conflict('Profile is already inactive')
    profile.activation_requested = False
    await service.save(session)
    return Response(status_code=204)
