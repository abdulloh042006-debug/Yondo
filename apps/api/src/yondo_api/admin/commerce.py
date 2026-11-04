"""Admin views of bookings, payments, refunds and payouts (TZ §38)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy import or_, select

from yondo_api.admin.audit import audit
from yondo_api.api.errors import ApplicationError
from yondo_api.bookings import service as bookings
from yondo_api.bookings.models import Booking, BookingEvent, BookingStatus, CancellationReason
from yondo_api.bookings.schemas import BookingEventResponse, BookingResponse
from yondo_api.core.db import commit
from yondo_api.core.deps import AdminUser, Session
from yondo_api.core.schemas import Input, Output, Page, PageParams, UtcDatetime, page_of
from yondo_api.core.time import utc_now
from yondo_api.notifications.service import notify
from yondo_api.payments.models import Payment, Payout, PayoutStatus, Refund
from yondo_api.payments.schemas import PaymentResponse, PayoutResponse
from yondo_api.payments.service import is_due, process_refunds

router = APIRouter(prefix='/admin', tags=['admin: bookings & payments'])
Params = Annotated[PageParams, Depends()]


class AdminBookingDetail(Output):
    booking: BookingResponse
    events: list[BookingEventResponse]
    payments: list[PaymentResponse]


class AdminCancel(Input):
    reason: str = Field(min_length=1, max_length=2000)
    refund_bps: int = Field(default=10_000, ge=0, le=10_000)


class RefundView(Output):
    id: UUID
    payment_id: UUID
    amount_minor: int
    status: str
    reason: str
    attempts: int
    created_at: UtcDatetime
    completed_at: UtcDatetime | None


class AdminPayout(PayoutResponse):
    beneficiary_id: UUID
    note: str | None
    due: bool = False


class MarkPaid(Input):
    reference: str = Field(min_length=1, max_length=200)


@router.get('/bookings', response_model=Page[BookingResponse])
async def booking_list(
    request: Request,
    admin: AdminUser,
    session: Session,
    params: Params,
    status: BookingStatus | None = None,
    user_id: UUID | None = None,
):
    query = select(Booking)
    if status:
        query = query.where(Booking.status == status)
    if user_id:
        query = query.where(or_(Booking.customer_id == user_id, Booking.companion_id == user_id))
    rows = list(
        await session.scalars(
            query.order_by(Booking.created_at.desc(), Booking.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    page = page_of(rows, params)
    return Page[BookingResponse](
        items=await bookings.build_responses(session, request, page.items, admin),
        next_offset=page.next_offset,
    )


@router.get('/bookings/{booking_id}', response_model=AdminBookingDetail)
async def booking_detail(booking_id: UUID, request: Request, admin: AdminUser, session: Session):
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise bookings.not_found()
    events = await session.scalars(
        select(BookingEvent)
        .where(BookingEvent.booking_id == booking_id)
        .order_by(BookingEvent.created_at)
    )
    payments = await session.scalars(
        select(Payment).where(Payment.booking_id == booking_id).order_by(Payment.created_at)
    )
    return AdminBookingDetail(
        booking=(await bookings.build_responses(session, request, [booking], admin))[0],
        events=[BookingEventResponse.model_validate(e) for e in events],
        payments=[PaymentResponse.model_validate(p) for p in payments],
    )


@router.post('/bookings/{booking_id}/cancel', response_model=BookingResponse)
async def cancel_booking(
    booking_id: UUID, payload: AdminCancel, request: Request, admin: AdminUser, session: Session
):
    booking = await bookings.lock_booking(session, booking_id)
    if booking.status not in {
        BookingStatus.PENDING,
        BookingStatus.ACCEPTED,
        BookingStatus.CONFIRMED,
        BookingStatus.ACTIVE,
    }:
        raise bookings.invalid_transition('This booking can no longer be cancelled')
    await bookings.cancel_and_settle(
        session, booking, CancellationReason.ADMIN, admin.id, payload.reason, payload.refund_bps
    )
    audit(
        session,
        admin,
        'booking.cancel',
        'booking',
        booking.id,
        payload.reason,
        {'refund_bps': payload.refund_bps},
    )
    await bookings.save(session)
    await process_refunds(session, request.app.state)
    return (await bookings.build_responses(session, request, [booking], admin))[0]


@router.get('/payments', response_model=Page[PaymentResponse])
async def payment_list(
    admin: AdminUser, session: Session, params: Params, status: str | None = None
):
    query = select(Payment)
    if status:
        query = query.where(Payment.status == status)
    rows = list(
        await session.scalars(
            query.order_by(Payment.created_at.desc(), Payment.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    return page_of([PaymentResponse.model_validate(p) for p in rows], params)


@router.get('/refunds', response_model=Page[RefundView])
async def refund_list(
    admin: AdminUser, session: Session, params: Params, status: str | None = None
):
    query = select(Refund)
    if status:
        query = query.where(Refund.status == status)
    rows = list(
        await session.scalars(
            query.order_by(Refund.created_at.desc(), Refund.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    return page_of([RefundView.model_validate(r) for r in rows], params)


@router.post('/refunds/process', response_model=dict)
async def run_refunds(request: Request, admin: AdminUser, session: Session):
    return {'processed': await process_refunds(session, request.app.state)}


@router.get('/payouts', response_model=Page[AdminPayout])
async def payout_list(
    admin: AdminUser,
    session: Session,
    params: Params,
    status: PayoutStatus | None = None,
    due_only: bool = False,
):
    query = select(Payout)
    if status:
        query = query.where(Payout.status == status)
    if due_only:
        query = query.where(
            Payout.status == PayoutStatus.SCHEDULED, Payout.available_at <= utc_now()
        )
    rows = list(
        await session.scalars(
            query.order_by(Payout.created_at.desc(), Payout.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    now = utc_now()
    items = []
    for payout in rows:
        view = AdminPayout.model_validate(payout)
        view.due = is_due(payout, now)
        items.append(view)
    return page_of(items, params)


@router.post('/payouts/{payout_id}/mark-paid', response_model=AdminPayout)
async def mark_paid(payout_id: UUID, payload: MarkPaid, admin: AdminUser, session: Session):
    """Record a completed manual transfer until a payout provider is integrated."""
    payout = await session.scalar(select(Payout).where(Payout.id == payout_id).with_for_update())
    if payout is None:
        raise ApplicationError('payout_not_found', 'Payout not found', 404)
    if not is_due(payout, utc_now()):
        raise ApplicationError('payout_not_due', 'Only due scheduled payouts can be paid', 409)
    payout.status = PayoutStatus.PAID
    payout.paid_at = utc_now()
    payout.paid_by = admin.id
    payout.reference = payload.reference
    notify(
        session,
        payout.beneficiary_id,
        'payout_paid',
        "To'lov o'tkazildi",
        f"{payout.amount_minor} {payout.currency} hisobingizga o'tkazildi.",
        {'payout_id': payout.id},
    )
    audit(session, admin, 'payout.paid', 'payout', payout.id, payload.reference)
    await commit(session)
    return AdminPayout.model_validate(payout)
