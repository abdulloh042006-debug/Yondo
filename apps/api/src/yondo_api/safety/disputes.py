"""Dispute Center (TZ §23): Booking -> Issue -> Description -> Evidence -> Submit."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Literal
from uuid import UUID, uuid4

from anyio import to_thread
from fastapi import APIRouter, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings import service as bookings
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.companions.dependencies import object_storage
from yondo_api.companions.photos import IMAGE_TYPES, compensate_upload, process_image
from yondo_api.config import Settings
from yondo_api.core.db import commit
from yondo_api.core.deps import CurrentUser, Session
from yondo_api.core.schemas import Input, Output, UtcDatetime
from yondo_api.core.time import as_utc, utc_now
from yondo_api.models.user import User
from yondo_api.safety.models import Dispute, DisputeEvidence, DisputeStatus

# TZ §24 report categories, shared by disputes.
CATEGORIES = (
    'harassment',
    'inappropriate_request',
    'fake_profile',
    'fraud',
    'unsafe_behavior',
    'no_show',
    'payment_issue',
    'other',
)
Category = Literal[
    'harassment',
    'inappropriate_request',
    'fake_profile',
    'fraud',
    'unsafe_behavior',
    'no_show',
    'payment_issue',
    'other',
]
DISPUTABLE = {BookingStatus.ACTIVE, BookingStatus.COMPLETED, BookingStatus.NO_SHOW}
EVIDENCE_URL_SECONDS = 600

router = APIRouter(tags=['disputes'])


class DisputeCreate(Input):
    category: Category
    description: str = Field(min_length=1, max_length=4000)


class EvidenceNote(Input):
    note: str = Field(min_length=1, max_length=4000)


class EvidenceResponse(Output):
    id: UUID
    uploaded_by: UUID
    kind: str
    note: str
    url: str | None = None
    created_at: UtcDatetime


class DisputeResponse(Output):
    id: UUID
    booking_id: UUID
    opened_by: UUID
    category: str
    description: str
    status: str
    previous_booking_status: str
    booking_outcome: str | None
    refund_minor: int | None
    payout_minor: int | None
    resolution_note: str | None
    resolved_at: UtcDatetime | None
    created_at: UtcDatetime
    evidence: list[EvidenceResponse] = []


async def open_dispute(
    session: AsyncSession,
    booking: Booking,
    user_id: UUID,
    category: str,
    description: str,
    *,
    from_no_show: bool = False,
    settings: Settings | None = None,
) -> Dispute:
    from yondo_api.payments.service import hold_payout

    if booking.status not in DISPUTABLE:
        raise bookings.invalid_transition('This booking cannot be disputed')
    if (
        not from_no_show
        and settings is not None
        and booking.status == BookingStatus.COMPLETED
        and booking.ended_at is not None
        and utc_now() > as_utc(booking.ended_at) + timedelta(days=settings.dispute_window_days)
    ):
        raise ApplicationError('dispute_window_closed', 'The dispute window has closed', 409)
    if await session.scalar(select(Dispute.id).where(Dispute.booking_id == booking.id)):
        raise ApplicationError('dispute_exists', 'A dispute already exists for this booking', 409)
    dispute = Dispute(
        booking_id=booking.id,
        opened_by=user_id,
        category=category,
        description=description,
        status=DisputeStatus.OPEN,
        previous_booking_status=booking.status,
    )
    session.add(dispute)
    bookings.transition(
        session,
        booking,
        BookingStatus.DISPUTED,
        'dispute_opened',
        actor_id=user_id,
        data={'category': category},
    )
    await hold_payout(session, booking.id, 'dispute')
    other = booking.companion_id if user_id == booking.customer_id else booking.customer_id
    bookings.booking_notice(
        session,
        booking,
        other,
        'dispute_opened',
        'Nizo ochildi',
        'Bron bo‘yicha nizo ochildi. Administrator ko‘rib chiqadi.',
    )
    await session.flush()
    return dispute


async def resolve_dispute(
    session: AsyncSession,
    dispute_id: UUID,
    admin: User,
    *,
    outcome: Literal['completed', 'no_show', 'cancelled'],
    refund_minor: int,
    payout_minor: int,
    note: str,
) -> Dispute:
    """Administrator decision: final booking state, customer refund and companion payout."""
    from yondo_api.payments.models import PayoutStatus
    from yondo_api.payments.service import booking_payment, booking_payout, queue_refund

    dispute = await session.scalar(
        select(Dispute).where(Dispute.id == dispute_id).with_for_update()
    )
    if dispute is None:
        raise ApplicationError('dispute_not_found', 'Dispute not found', 404)
    if dispute.status == DisputeStatus.RESOLVED:
        raise ApplicationError('dispute_resolved', 'The dispute is already resolved', 409)
    booking = await bookings.lock_booking(session, dispute.booking_id)
    if admin.id in {booking.customer_id, booking.companion_id}:
        raise ApplicationError('self_review_forbidden', 'Parties cannot resolve their dispute', 403)
    payment = await booking_payment(session, booking.id)
    refundable = payment.amount_minor - payment.refunded_minor if payment else 0
    if refund_minor > refundable:
        raise ApplicationError('invalid_refund', 'Refund exceeds the refundable amount', 422)
    if payout_minor > booking.companion_payout_minor:
        raise ApplicationError('invalid_payout', 'Payout exceeds the companion amount', 422)
    if refund_minor and payment is not None:
        queue_refund(session, payment, refund_minor, 'dispute_resolution')
        booking.refund_minor += refund_minor
    payout = await booking_payout(session, booking.id)
    if payout is not None and payout.status != PayoutStatus.PAID:
        payout.amount_minor = payout_minor
        payout.status = PayoutStatus.SCHEDULED if payout_minor else PayoutStatus.CANCELLED
        payout.available_at = utc_now() if payout_minor else None
        payout.note = 'dispute_resolution'
    now = utc_now()
    if outcome == 'cancelled':
        booking.cancelled_at = now
        booking.cancellation_reason = 'admin_cancelled'
    dispute.status = DisputeStatus.RESOLVED
    dispute.booking_outcome = outcome
    dispute.refund_minor = refund_minor
    dispute.payout_minor = payout_minor
    dispute.resolution_note = note
    dispute.resolved_by = admin.id
    dispute.resolved_at = now
    bookings.transition(
        session,
        booking,
        BookingStatus(outcome),
        'dispute_resolved',
        actor_id=admin.id,
        data={'refund_minor': refund_minor, 'payout_minor': payout_minor},
    )
    for party in (booking.customer_id, booking.companion_id):
        bookings.booking_notice(
            session, booking, party, 'dispute_resolved', 'Nizo hal qilindi', note[:200]
        )
    await commit(session)
    return dispute


async def dispute_view(request: Request, session: AsyncSession, dispute: Dispute):
    view = DisputeResponse.model_validate(dispute)
    storage = request.app.state.object_storage
    items = []
    for evidence in await session.scalars(
        select(DisputeEvidence)
        .where(DisputeEvidence.dispute_id == dispute.id)
        .order_by(DisputeEvidence.created_at)
    ):
        item = EvidenceResponse.model_validate(evidence)
        if evidence.storage_key and storage is not None:
            try:
                item.url = await storage.create_download_url(
                    evidence.storage_key, EVIDENCE_URL_SECONDS
                )
            except Exception:
                item.url = None
        items.append(item)
    view.evidence = items
    return view


async def participant_dispute(session: AsyncSession, dispute_id: UUID, user: User) -> Dispute:
    dispute = await session.get(Dispute, dispute_id)
    booking = await session.get(Booking, dispute.booking_id) if dispute else None
    if booking is None or bookings.role_of(booking, user) is None:
        raise ApplicationError('dispute_not_found', 'Dispute not found', 404)
    if dispute.status == DisputeStatus.RESOLVED:
        raise ApplicationError('dispute_resolved', 'The dispute is already resolved', 409)
    return dispute


@router.post('/bookings/{booking_id}/dispute', response_model=DisputeResponse, status_code=201)
async def create_dispute(
    booking_id: UUID, payload: DisputeCreate, request: Request, user: CurrentUser, session: Session
):
    booking, _ = await bookings.participant_booking(session, booking_id, user, lock=True)
    dispute = await open_dispute(
        session,
        booking,
        user.id,
        payload.category,
        payload.description,
        settings=request.app.state.settings,
    )
    await commit(session, 'dispute_exists', 'A dispute already exists for this booking')
    return await dispute_view(request, session, dispute)


@router.get('/bookings/{booking_id}/dispute', response_model=DisputeResponse)
async def get_dispute(booking_id: UUID, request: Request, user: CurrentUser, session: Session):
    await bookings.participant_booking(session, booking_id, user)
    dispute = await session.scalar(select(Dispute).where(Dispute.booking_id == booking_id))
    if dispute is None:
        raise ApplicationError('dispute_not_found', 'Dispute not found', 404)
    return await dispute_view(request, session, dispute)


@router.post('/disputes/{dispute_id}/evidence', response_model=EvidenceResponse, status_code=201)
async def add_note(dispute_id: UUID, payload: EvidenceNote, user: CurrentUser, session: Session):
    dispute = await participant_dispute(session, dispute_id, user)
    evidence = DisputeEvidence(
        dispute_id=dispute.id,
        uploaded_by=user.id,
        kind='text',
        note=payload.note,
        created_at=utc_now(),
    )
    session.add(evidence)
    await commit(session)
    return evidence


@router.post(
    '/disputes/{dispute_id}/evidence/image',
    response_model=EvidenceResponse,
    status_code=201,
    openapi_extra={
        'requestBody': {
            'required': True,
            'content': {
                mime: {'schema': {'type': 'string', 'format': 'binary'}}
                for mime in IMAGE_TYPES.values()
            },
        }
    },
)
async def add_image(dispute_id: UUID, request: Request, user: CurrentUser, session: Session):
    dispute = await participant_dispute(session, dispute_id, user)
    storage = object_storage(request)
    settings = request.app.state.settings
    content_type = request.headers.get('content-type', '').split(';')[0].strip()
    if content_type not in IMAGE_TYPES.values():
        raise ApplicationError('invalid_photo_type', 'A JPEG, PNG or WebP image is required', 415)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > settings.companion_photo_max_bytes:
            raise ApplicationError('photo_too_large', 'Image exceeds the byte limit', 413)
        data.extend(chunk)
    content, _, _ = await to_thread.run_sync(
        process_image,
        data,
        content_type,
        settings,
        limiter=request.app.state.companion_image_limiter,
    )
    key = f'disputes/{dispute.id}/{uuid4()}.jpg'

    async def chunks():
        yield content

    try:
        await storage.upload(key, chunks(), 'image/jpeg')
    except asyncio.CancelledError:
        await compensate_upload(storage, key)
        raise
    except Exception as exc:
        await compensate_upload(storage, key)
        raise ApplicationError('storage_unavailable', 'Image upload failed', 503) from exc
    evidence = DisputeEvidence(
        dispute_id=dispute.id,
        uploaded_by=user.id,
        kind='image',
        note='',
        storage_key=key,
        created_at=utc_now(),
    )
    session.add(evidence)
    try:
        await commit(session)
    except BaseException:
        await compensate_upload(storage, key)
        raise
    return EvidenceResponse.model_validate(evidence)
