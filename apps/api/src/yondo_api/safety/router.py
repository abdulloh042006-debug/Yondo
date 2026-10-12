from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.bookings.router import _participant
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.models.user import User
from yondo_api.safety.models import SafetyAlert, SafetyReport, TrustedContact, UserBlock

router = APIRouter(prefix='/safety', tags=['safety'])


class ReportWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reported_user_id: UUID
    booking_id: UUID | None = None
    category: Literal[
        'harassment',
        'inappropriate_request',
        'fake_profile',
        'fraud',
        'unsafe_behavior',
        'no_show',
        'payment_issue',
        'other',
    ]
    description: str = Field(min_length=1, max_length=4000)


class ReportRead(ReportWrite):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str


class ContactWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=128)
    phone_number: str = Field(pattern=r'^\+?[0-9]{7,15}$')


class ContactRead(ContactWrite):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


@router.post('/reports', response_model=ReportRead, status_code=201)
async def report_user(payload: ReportWrite, principal: Principal, session: Session):
    if payload.reported_user_id == principal.user.id:
        raise ApplicationError('invalid_report', 'Cannot report own account', 422)
    if await session.get(User, payload.reported_user_id) is None:
        raise ApplicationError('reported_user_not_found', 'Account not found', 404)
    if payload.booking_id is not None:
        booking = await session.get(Booking, payload.booking_id)
        if booking is None:
            raise ApplicationError('booking_not_found', 'Booking not found', 404)
        await _participant(session, booking, principal.user.id)
        from yondo_api.companions.models import CompanionApplication, CompanionProfile

        companion_id = await session.scalar(
            select(CompanionApplication.user_id)
            .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
            .where(CompanionProfile.id == booking.profile_id)
        )
        other_id = companion_id if principal.user.id == booking.customer_id else booking.customer_id
        if payload.reported_user_id != other_id:
            raise ApplicationError('invalid_report_target', 'Report target is not participant', 422)
    report = SafetyReport(
        reporter_id=principal.user.id,
        reported_user_id=payload.reported_user_id,
        booking_id=payload.booking_id,
        category=payload.category,
        description=payload.description.strip(),
        status='open',
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


@router.get('/reports', response_model=list[ReportRead])
async def own_reports(principal: Principal, session: Session):
    return list(
        await session.scalars(
            select(SafetyReport).where(SafetyReport.reporter_id == principal.user.id)
        )
    )


@router.put('/blocks/{user_id}', status_code=204)
async def block_user(user_id: UUID, principal: Principal, session: Session):
    if user_id == principal.user.id:
        raise ApplicationError('invalid_block', 'Cannot block own account', 422)
    if await session.get(User, user_id) is None:
        raise ApplicationError('user_not_found', 'Account not found', 404)
    if not await session.scalar(
        select(UserBlock.id).where(
            UserBlock.blocker_id == principal.user.id, UserBlock.blocked_id == user_id
        )
    ):
        session.add(UserBlock(blocker_id=principal.user.id, blocked_id=user_id))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()


@router.delete('/blocks/{user_id}', status_code=204)
async def unblock_user(user_id: UUID, principal: Principal, session: Session):
    item = await session.scalar(
        select(UserBlock).where(
            UserBlock.blocker_id == principal.user.id, UserBlock.blocked_id == user_id
        )
    )
    if item is not None:
        await session.delete(item)
        await session.commit()


@router.get('/blocks', response_model=list[UUID])
async def list_blocks(principal: Principal, session: Session):
    return list(
        await session.scalars(
            select(UserBlock.blocked_id).where(UserBlock.blocker_id == principal.user.id)
        )
    )


@router.post('/trusted-contacts', response_model=ContactRead, status_code=201)
async def add_contact(payload: ContactWrite, principal: Principal, session: Session):
    item = TrustedContact(owner_id=principal.user.id, **payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get('/trusted-contacts', response_model=list[ContactRead])
async def list_contacts(principal: Principal, session: Session):
    return list(
        await session.scalars(
            select(TrustedContact).where(TrustedContact.owner_id == principal.user.id)
        )
    )


@router.delete('/trusted-contacts/{contact_id}', status_code=204)
async def delete_contact(contact_id: UUID, principal: Principal, session: Session):
    item = await session.scalar(
        select(TrustedContact).where(
            TrustedContact.id == contact_id, TrustedContact.owner_id == principal.user.id
        )
    )
    if item is None:
        raise ApplicationError('contact_not_found', 'Contact not found', 404)
    await session.delete(item)
    await session.commit()


@router.post('/bookings/{booking_id}/sos', status_code=201)
async def create_sos_alert(
    booking_id: UUID, principal: Principal, session: Session, confirmed: bool
):
    if not confirmed:
        raise ApplicationError('sos_confirmation_required', 'Confirm SOS before submitting', 422)
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    await _participant(session, booking, principal.user.id)
    if booking.status != BookingStatus.ACTIVE:
        raise ApplicationError('sos_requires_active_booking', 'Booking is not active', 409)
    alert = SafetyAlert(booking_id=booking.id, creator_id=principal.user.id)
    session.add(alert)
    await session.commit()
    # The alert is stored for review; no emergency service has been contacted.
    return {'id': str(alert.id), 'emergency_service_contacted': False}


async def blocked_between(session: Session, user_a: UUID, user_b: UUID) -> bool:
    return bool(
        await session.scalar(
            select(UserBlock.id).where(
                or_(
                    (UserBlock.blocker_id == user_a) & (UserBlock.blocked_id == user_b),
                    (UserBlock.blocker_id == user_b) & (UserBlock.blocked_id == user_a),
                )
            )
        )
    )
