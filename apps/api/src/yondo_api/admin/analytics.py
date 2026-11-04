"""MVP success metrics (TZ §47, ROADMAP Phase 22)."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy import distinct, func, select

from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.core.deps import AdminUser, Session
from yondo_api.core.schemas import Output
from yondo_api.core.time import utc_now
from yondo_api.gifts.models import GiftOrder, GiftOrderStatus
from yondo_api.models.user import User, UserRole, UserRoleType
from yondo_api.payments.models import PAID_STATUSES, Payment
from yondo_api.reviews.models import Review, ReviewDirection
from yondo_api.safety.models import IdentityVerification, Report, VerificationStatus

router = APIRouter(prefix='/admin', tags=['admin: analytics'])


class Metrics(Output):
    period_days: int
    registrations: int
    registrations_total: int
    verified_users: int
    active_companions: int
    companions_total: int
    booking_requests: int
    accepted_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    no_show_bookings: int
    disputed_bookings: int
    booking_conversion_rate: float | None
    completion_rate: float | None
    cancellation_rate: float | None
    no_show_rate: float | None
    repeat_booking_rate: float | None
    average_rating: float | None
    reports: int
    report_rate: float | None
    gross_volume_minor: int
    refunded_minor: int
    platform_fee_minor: int
    gift_attach_rate: float | None


def _rate(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


@router.get('/analytics', response_model=Metrics)
async def metrics(
    request: Request,
    admin: AdminUser,
    session: Session,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
):
    from yondo_api.discovery.schemas import DiscoveryFilters
    from yondo_api.discovery.service import public_candidates

    since = utc_now() - timedelta(days=days)

    async def count(query) -> int:
        return await session.scalar(select(func.count()).select_from(query.subquery())) or 0

    period = Booking.created_at >= since
    requests = await count(select(Booking.id).where(period))
    by_status = dict(
        (
            await session.execute(
                select(Booking.status, func.count()).where(period).group_by(Booking.status)
            )
        ).all()
    )
    accepted = await count(
        select(Booking.id).where(period, Booking.companion_accepted_at.is_not(None))
    )
    completed = by_status.get(BookingStatus.COMPLETED, 0)
    cancelled = by_status.get(BookingStatus.CANCELLED, 0)
    no_show = by_status.get(BookingStatus.NO_SHOW, 0)
    disputed = by_status.get(BookingStatus.DISPUTED, 0)
    customers_with_completed = await count(
        select(Booking.customer_id)
        .where(period, Booking.status == BookingStatus.COMPLETED)
        .group_by(Booking.customer_id)
    )
    repeat_customers = await count(
        select(Booking.customer_id)
        .where(period, Booking.status == BookingStatus.COMPLETED)
        .group_by(Booking.customer_id)
        .having(func.count() > 1)
    )
    paid = (
        select(Payment.amount_minor, Payment.refunded_minor)
        .where(Payment.created_at >= since, Payment.status.in_(PAID_STATUSES))
        .subquery()
    )
    gross = await session.scalar(select(func.coalesce(func.sum(paid.c.amount_minor), 0)))
    refunded = await session.scalar(select(func.coalesce(func.sum(paid.c.refunded_minor), 0)))
    fees = await session.scalar(
        select(func.coalesce(func.sum(Booking.platform_fee_minor), 0)).where(
            period, Booking.confirmed_at.is_not(None), Booking.status != BookingStatus.CANCELLED
        )
    )
    confirmed = await count(select(Booking.id).where(period, Booking.confirmed_at.is_not(None)))
    with_gifts = await count(
        select(distinct(GiftOrder.booking_id)).where(
            GiftOrder.booking_id.in_(
                select(Booking.id).where(period, Booking.confirmed_at.is_not(None))
            ),
            GiftOrder.status != GiftOrderStatus.PENDING_PAYMENT,
        )
    )
    average = await session.scalar(
        select(func.avg(Review.rating)).where(
            Review.direction == ReviewDirection.FOR_COMPANION, Review.status == 'published'
        )
    )
    reports = await count(select(Report.id).where(Report.created_at >= since))
    public = await public_candidates(session, request, admin, DiscoveryFilters(sort='newest'))
    return Metrics(
        period_days=days,
        registrations=await count(select(User.id).where(User.created_at >= since)),
        registrations_total=await count(select(User.id)),
        verified_users=await count(
            select(distinct(IdentityVerification.user_id)).where(
                IdentityVerification.status == VerificationStatus.VERIFIED
            )
        ),
        active_companions=len(public),
        companions_total=await count(
            select(UserRole.user_id).where(UserRole.role == UserRoleType.COMPANION)
        ),
        booking_requests=requests,
        accepted_bookings=accepted,
        completed_bookings=completed,
        cancelled_bookings=cancelled,
        no_show_bookings=no_show,
        disputed_bookings=disputed,
        booking_conversion_rate=_rate(confirmed, requests),
        completion_rate=_rate(completed, confirmed),
        cancellation_rate=_rate(cancelled, requests),
        no_show_rate=_rate(no_show, confirmed),
        repeat_booking_rate=_rate(repeat_customers, customers_with_completed),
        average_rating=round(float(average), 2) if average is not None else None,
        reports=reports,
        report_rate=_rate(reports, completed + no_show + disputed),
        gross_volume_minor=gross or 0,
        refunded_minor=refunded or 0,
        platform_fee_minor=fees or 0,
        gift_attach_rate=_rate(with_gifts, confirmed),
    )
