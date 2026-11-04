"""Safety Center (TZ §16-§18, §24-§25): blocks, reports, trusted contacts, sharing and SOS."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request, Response
from pydantic import Field
from sqlalchemy import delete, func, select

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.phone import normalize_uzbekistan_phone
from yondo_api.bookings import service as bookings
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.core.db import commit
from yondo_api.core.deps import CurrentUser, Session
from yondo_api.core.schemas import Input, Output, UtcDatetime
from yondo_api.core.time import as_utc, utc_now
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType
from yondo_api.notifications.service import notify
from yondo_api.safety.disputes import Category
from yondo_api.safety.models import (
    BookingShare,
    Report,
    ReportStatus,
    SosAlert,
    SosStatus,
    TrustedContact,
    UserBlock,
)

router = APIRouter(tags=['safety'])
MAX_TRUSTED_CONTACTS = 5
SHAREABLE = {BookingStatus.ACCEPTED, BookingStatus.CONFIRMED, BookingStatus.ACTIVE}

# Uzbekistan emergency services.
EMERGENCY_NUMBERS = [
    {'service': 'unified_emergency', 'number': '112'},
    {'service': 'fire', 'number': '101'},
    {'service': 'police', 'number': '102'},
    {'service': 'ambulance', 'number': '103'},
    {'service': 'gas', 'number': '104'},
]
SAFETY_GUIDE = [
    {'key': 'public_places', 'text': "Uchrashuvni faqat jamoat joylarida o'tkazing."},
    {'key': 'stay_on_platform', 'text': "Muloqot va to'lovni faqat Yondo ichida qiling."},
    {'key': 'share_booking', 'text': 'Bronni ishonchli kontaktingiz bilan ulashing.'},
    {'key': 'trust_instincts', 'text': "O'zingizni noqulay his qilsangiz, uchrashuvni yakunlang."},
    {'key': 'report', 'text': 'Qoidabuzarlik haqida darhol report yuboring.'},
    {'key': 'prohibited', 'text': "Jinsiy, escort va noqonuniy xizmatlar qat'iyan taqiqlangan."},
]


class BlockResponse(Output):
    user_id: UUID
    display_name: str | None
    created_at: UtcDatetime


class ReportCreate(Input):
    reported_user_id: UUID
    booking_id: UUID | None = None
    category: Category
    description: str = Field(default='', max_length=4000)


class ReportResponse(Output):
    id: UUID
    reported_user_id: UUID
    booking_id: UUID | None
    category: str
    description: str
    status: str
    created_at: UtcDatetime


class ContactWrite(Input):
    name: str = Field(min_length=1, max_length=128)
    phone_number: str = Field(min_length=9, max_length=32)
    relationship: str = Field(default='', max_length=64)


class ContactResponse(Output):
    id: UUID
    name: str
    phone_number: str
    relationship: str


class ShareCreate(Input):
    trusted_contact_id: UUID | None = None


class ShareResponse(Output):
    token: str
    path: str
    expires_at: UtcDatetime
    message: str


class SharedBooking(Output):
    status: str
    companion_name: str | None
    customer_name: str | None
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    timezone: str
    meeting_place: str
    meeting_address: str
    started_at: UtcDatetime | None
    ended_at: UtcDatetime | None
    sos_active: bool


class SosCreate(Input):
    booking_id: UUID | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    message: str = Field(default='', max_length=1000)
    confirm: Literal[True]


class SosResponse(Output):
    id: UUID
    status: str
    booking_id: UUID | None
    emergency_numbers: list[dict[str, str]]
    trusted_contacts: list[ContactResponse]
    created_at: UtcDatetime


class SafetyCenter(Output):
    guide: list[dict[str, str]]
    emergency_numbers: list[dict[str, str]]
    trusted_contacts: list[ContactResponse]
    active_booking_id: UUID | None
    open_reports: int


def _hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


# --- Blocks -------------------------------------------------------------------------------


@router.get('/blocks', response_model=list[BlockResponse])
async def list_blocks(user: CurrentUser, session: Session):
    rows = await session.execute(
        select(UserBlock, User.display_name)
        .join(User, User.id == UserBlock.blocked_id)
        .where(UserBlock.blocker_id == user.id)
        .order_by(UserBlock.created_at.desc())
    )
    return [
        BlockResponse(user_id=block.blocked_id, display_name=name, created_at=block.created_at)
        for block, name in rows
    ]


@router.put('/blocks/{user_id}', status_code=204)
async def block_user(user_id: UUID, user: CurrentUser, session: Session):
    if user_id == user.id:
        raise ApplicationError('invalid_block', 'You cannot block yourself', 422)
    if await session.get(User, user_id) is None:
        raise ApplicationError('user_not_found', 'User not found', 404)
    if await session.get(UserBlock, (user.id, user_id)) is None:
        session.add(UserBlock(blocker_id=user.id, blocked_id=user_id))
        await commit(session)
    return Response(status_code=204)


@router.delete('/blocks/{user_id}', status_code=204)
async def unblock_user(user_id: UUID, user: CurrentUser, session: Session):
    await session.execute(
        delete(UserBlock).where(UserBlock.blocker_id == user.id, UserBlock.blocked_id == user_id)
    )
    await commit(session)
    return Response(status_code=204)


# --- Reports ------------------------------------------------------------------------------


@router.post('/reports', response_model=ReportResponse, status_code=201)
async def create_report(payload: ReportCreate, user: CurrentUser, session: Session):
    if payload.reported_user_id == user.id:
        raise ApplicationError('invalid_report', 'You cannot report yourself', 422)
    if await session.get(User, payload.reported_user_id) is None:
        raise ApplicationError('user_not_found', 'User not found', 404)
    if payload.booking_id is not None:
        booking, _ = await bookings.participant_booking(session, payload.booking_id, user)
        if payload.reported_user_id not in {booking.customer_id, booking.companion_id}:
            raise ApplicationError('invalid_report', 'User is not part of this booking', 422)
    report = Report(
        reporter_id=user.id,
        reported_user_id=payload.reported_user_id,
        booking_id=payload.booking_id,
        category=payload.category,
        description=payload.description,
        status=ReportStatus.OPEN,
    )
    session.add(report)
    await commit(session)
    return report


@router.get('/reports/me', response_model=list[ReportResponse])
async def my_reports(user: CurrentUser, session: Session):
    return list(
        await session.scalars(
            select(Report)
            .where(Report.reporter_id == user.id)
            .order_by(Report.created_at.desc())
            .limit(100)
        )
    )


# --- Trusted contacts ---------------------------------------------------------------------


@router.get('/safety/contacts', response_model=list[ContactResponse])
async def list_contacts(user: CurrentUser, session: Session):
    return await contacts_of(session, user.id)


async def contacts_of(session, user_id: UUID) -> list[TrustedContact]:
    return list(
        await session.scalars(
            select(TrustedContact)
            .where(TrustedContact.user_id == user_id)
            .order_by(TrustedContact.created_at)
        )
    )


@router.post('/safety/contacts', response_model=ContactResponse, status_code=201)
async def add_contact(payload: ContactWrite, user: CurrentUser, session: Session):
    count = await session.scalar(
        select(func.count()).select_from(TrustedContact).where(TrustedContact.user_id == user.id)
    )
    if count >= MAX_TRUSTED_CONTACTS:
        raise ApplicationError('contact_limit', 'Trusted contact limit reached', 422)
    contact = TrustedContact(
        user_id=user.id,
        name=payload.name,
        phone_number=normalize_uzbekistan_phone(payload.phone_number),
        relationship=payload.relationship,
    )
    session.add(contact)
    await commit(session)
    return contact


@router.put('/safety/contacts/{contact_id}', response_model=ContactResponse)
async def update_contact(
    contact_id: UUID, payload: ContactWrite, user: CurrentUser, session: Session
):
    contact = await session.get(TrustedContact, contact_id)
    if contact is None or contact.user_id != user.id:
        raise ApplicationError('contact_not_found', 'Trusted contact not found', 404)
    contact.name = payload.name
    contact.phone_number = normalize_uzbekistan_phone(payload.phone_number)
    contact.relationship = payload.relationship
    await commit(session)
    return contact


@router.delete('/safety/contacts/{contact_id}', status_code=204)
async def delete_contact(contact_id: UUID, user: CurrentUser, session: Session):
    contact = await session.get(TrustedContact, contact_id)
    if contact is None or contact.user_id != user.id:
        raise ApplicationError('contact_not_found', 'Trusted contact not found', 404)
    await session.delete(contact)
    await commit(session)
    return Response(status_code=204)


# --- Booking sharing ----------------------------------------------------------------------


@router.post('/bookings/{booking_id}/share', response_model=ShareResponse, status_code=201)
async def share_booking(
    booking_id: UUID, payload: ShareCreate, request: Request, user: CurrentUser, session: Session
):
    """Create a read-only link; the app hands it to the trusted contact via the share sheet."""
    booking, _ = await bookings.participant_booking(session, booking_id, user)
    if booking.status not in SHAREABLE:
        raise bookings.invalid_transition('Only upcoming or active bookings can be shared')
    if payload.trusted_contact_id is not None:
        contact = await session.get(TrustedContact, payload.trusted_contact_id)
        if contact is None or contact.user_id != user.id:
            raise ApplicationError('contact_not_found', 'Trusted contact not found', 404)
    token = secrets.token_urlsafe(24)
    settings = request.app.state.settings
    expires = max(as_utc(booking.ends_at), utc_now()) + timedelta(
        hours=settings.booking_share_ttl_hours
    )
    session.add(
        BookingShare(
            booking_id=booking.id,
            user_id=user.id,
            trusted_contact_id=payload.trusted_contact_id,
            token_hash=_hash(token),
            expires_at=expires,
        )
    )
    await commit(session)
    path = f'{settings.api_v1_prefix}/safety/shared/{token}'
    when = bookings.fmt_local(booking.starts_at, booking.timezone)
    return ShareResponse(
        token=token,
        path=path,
        expires_at=expires,
        message=f'Men Yondo orqali {when} da {booking.meeting_place_name} da uchrashuvdaman.',
    )


@router.get('/safety/shared/{token}', response_model=SharedBooking)
async def shared_booking(token: str, session: Session):
    """Public, token-protected view without phone numbers or exact private data."""
    share = await session.scalar(
        select(BookingShare).where(BookingShare.token_hash == _hash(token))
    )
    if share is None or share.revoked_at is not None or as_utc(share.expires_at) < utc_now():
        raise ApplicationError('share_not_found', 'This link is invalid or expired', 404)
    booking = await session.get(Booking, share.booking_id)
    names = await bookings._profile_names(session, {booking.profile_id})
    customer = await session.get(User, booking.customer_id)
    sos = await session.scalar(
        select(func.count())
        .select_from(SosAlert)
        .where(SosAlert.booking_id == booking.id, SosAlert.status != SosStatus.RESOLVED)
    )
    return SharedBooking(
        status=booking.status,
        companion_name=names.get(booking.profile_id),
        customer_name=customer.display_name if customer else None,
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        timezone=booking.timezone,
        meeting_place=booking.meeting_place_name,
        meeting_address=booking.meeting_address,
        started_at=booking.started_at,
        ended_at=booking.ended_at,
        sos_active=bool(sos),
    )


# --- SOS and Safety Center ----------------------------------------------------------------


async def active_booking_for(session, user_id: UUID) -> Booking | None:
    return await session.scalar(
        select(Booking)
        .where(
            (Booking.customer_id == user_id) | (Booking.companion_id == user_id),
            Booking.status.in_((BookingStatus.ACTIVE, BookingStatus.CONFIRMED)),
            Booking.starts_at <= utc_now() + timedelta(hours=1),
            Booking.ends_at >= utc_now() - timedelta(hours=1),
        )
        .order_by(Booking.status, Booking.starts_at)
        .limit(1)
    )


@router.post('/safety/sos', response_model=SosResponse, status_code=201)
async def raise_sos(payload: SosCreate, user: CurrentUser, session: Session):
    booking_id = payload.booking_id
    if booking_id is not None:
        await bookings.participant_booking(session, booking_id, user)
    else:
        active = await active_booking_for(session, user.id)
        booking_id = active.id if active else None
    alert = SosAlert(
        user_id=user.id,
        booking_id=booking_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        message=payload.message,
        status=SosStatus.OPEN,
    )
    session.add(alert)
    await session.flush()
    admins = await session.scalars(
        select(User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .where(UserRole.role == UserRoleType.ADMIN, User.account_status == AccountStatus.ACTIVE)
    )
    for admin_id in admins:
        notify(
            session,
            admin_id,
            'sos_alert',
            'SOS signal',
            f'{user.display_name or "Foydalanuvchi"} SOS yubordi.',
            {'sos_id': alert.id, 'booking_id': booking_id or ''},
        )
    await commit(session)
    return SosResponse(
        id=alert.id,
        status=alert.status,
        booking_id=booking_id,
        emergency_numbers=EMERGENCY_NUMBERS,
        trusted_contacts=[
            ContactResponse.model_validate(c) for c in await contacts_of(session, user.id)
        ],
        created_at=alert.created_at,
    )


@router.get('/safety/center', response_model=SafetyCenter)
async def safety_center(user: CurrentUser, session: Session):
    active = await active_booking_for(session, user.id)
    open_reports = await session.scalar(
        select(func.count())
        .select_from(Report)
        .where(
            Report.reporter_id == user.id,
            Report.status.in_((ReportStatus.OPEN, ReportStatus.IN_REVIEW)),
        )
    )
    return SafetyCenter(
        guide=SAFETY_GUIDE,
        emergency_numbers=EMERGENCY_NUMBERS,
        trusted_contacts=[
            ContactResponse.model_validate(c) for c in await contacts_of(session, user.id)
        ],
        active_booking_id=active.id if active else None,
        open_reports=open_reports or 0,
    )
