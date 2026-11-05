from uuid import UUID

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from yondo_api.companions import service
from yondo_api.companions.dependencies import Owner, Session
from yondo_api.companions.models import CompanionAvailability, CompanionService
from yondo_api.companions.schemas import (
    AvailabilityResponse,
    AvailabilityWrite,
    ServiceResponse,
    ServiceWrite,
)

router = APIRouter(prefix='/companions/me', tags=['companion resources'])


async def ensure_availability_edit_safe(session: Session, item: CompanionAvailability) -> None:
    from yondo_api.bookings.models import Booking, BookingStatus

    booked = await session.scalar(
        select(Booking.id).where(
            Booking.profile_id == item.profile_id,
            Booking.status.in_(
                (
                    BookingStatus.PENDING,
                    BookingStatus.ACCEPTED,
                    BookingStatus.CONFIRMED,
                    BookingStatus.ACTIVE,
                )
            ),
            Booking.starts_at < item.ends_at,
            Booking.ends_at > item.starts_at,
        )
    )
    if booked is not None:
        from yondo_api.api.errors import ApplicationError

        raise ApplicationError('availability_reserved', 'Availability has active reservations', 409)


@router.get('/services', response_model=list[ServiceResponse])
async def list_services(owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    return list(
        await session.scalars(
            select(CompanionService)
            .where(CompanionService.profile_id == profile.id)
            .order_by(CompanionService.service_code)
        )
    )


@router.post('/services', response_model=ServiceResponse, status_code=201)
async def create_service(payload: ServiceWrite, request: Request, owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    service.validate_service(payload, request.app.state.settings)
    item = CompanionService(profile_id=profile.id, **payload.model_dump())
    session.add(item)
    service.invalidate_content(profile)
    await service.save(session)
    return item


@router.put('/services/{service_id}', response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    payload: ServiceWrite,
    request: Request,
    owner: Owner,
    session: Session,
):
    profile = await service.profile_for(session, owner.id)
    item = await service.owned_resource(session, CompanionService, service_id, profile.id)
    service.validate_service(payload, request.app.state.settings)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    service.invalidate_content(profile)
    await service.save(session)
    return item


@router.delete('/services/{service_id}', status_code=204)
async def delete_service(service_id: UUID, owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    item = await service.owned_resource(session, CompanionService, service_id, profile.id)
    await session.delete(item)
    service.invalidate_content(profile)
    await service.save(session)
    return Response(status_code=204)


@router.get('/availability', response_model=list[AvailabilityResponse])
async def list_availability(owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    return list(
        await session.scalars(
            select(CompanionAvailability)
            .where(CompanionAvailability.profile_id == profile.id)
            .order_by(CompanionAvailability.starts_at)
        )
    )


@router.post('/availability', response_model=AvailabilityResponse, status_code=201)
async def create_availability(payload: AvailabilityWrite, owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    await service.ensure_no_overlap(session, profile.id, payload)
    item = CompanionAvailability(profile_id=profile.id, **payload.model_dump())
    session.add(item)
    await service.save(session)
    return item


@router.put('/availability/{availability_id}', response_model=AvailabilityResponse)
async def update_availability(
    availability_id: UUID,
    payload: AvailabilityWrite,
    owner: Owner,
    session: Session,
):
    profile = await service.profile_for(session, owner.id)
    item = await service.owned_resource(session, CompanionAvailability, availability_id, profile.id)
    await ensure_availability_edit_safe(session, item)
    await service.ensure_no_overlap(session, profile.id, payload, exclude_id=item.id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    await service.save(session)
    return item


@router.delete('/availability/{availability_id}', status_code=204)
async def delete_availability(availability_id: UUID, owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    item = await service.owned_resource(session, CompanionAvailability, availability_id, profile.id)
    await ensure_availability_edit_safe(session, item)
    await session.delete(item)
    await service.save(session)
    return Response(status_code=204)
