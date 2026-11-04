"""Admin queues for approvals and Trust & Safety: companions, verification, reports,
disputes, reviews and SOS alerts."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy import select

from yondo_api.admin.audit import audit
from yondo_api.api.errors import ApplicationError
from yondo_api.companions.models import (
    ApplicationStatus,
    CompanionApplication,
    CompanionProfile,
    ContentStatus,
)
from yondo_api.core.db import commit
from yondo_api.core.deps import AdminUser, Session
from yondo_api.core.schemas import Input, Output, Page, PageParams, UtcDatetime, page_of
from yondo_api.core.time import utc_now
from yondo_api.models.user import User
from yondo_api.notifications.service import notify
from yondo_api.reviews.models import Review
from yondo_api.safety import disputes, identity
from yondo_api.safety.models import (
    AdminAuditLog,
    Dispute,
    DisputeStatus,
    IdentityVerification,
    Report,
    ReportStatus,
    SosAlert,
    SosStatus,
    VerificationStatus,
)

router = APIRouter(prefix='/admin', tags=['admin: trust & safety'])
Params = Annotated[PageParams, Depends()]


async def _page(session, query, params: PageParams, order):
    rows = list(
        await session.scalars(query.order_by(*order).offset(params.offset).limit(params.limit + 1))
    )
    return page_of(rows, params)


# --- Companion approval queues -------------------------------------------------------------


class ApplicationQueueItem(Output):
    id: UUID
    user_id: UUID
    display_name: str | None
    status: str
    revision: int
    statement: str
    submitted_at: UtcDatetime | None


class ProfileQueueItem(Output):
    id: UUID
    user_id: UUID
    display_name: str
    content_status: str
    revision: int
    updated_at: UtcDatetime


@router.get('/companions/applications', response_model=Page[ApplicationQueueItem])
async def application_queue(
    admin: AdminUser,
    session: Session,
    params: Params,
    status: ApplicationStatus = ApplicationStatus.SUBMITTED,
):
    rows = list(
        await session.execute(
            select(CompanionApplication, User.display_name)
            .join(User, User.id == CompanionApplication.user_id)
            .where(CompanionApplication.status == status)
            .order_by(CompanionApplication.submitted_at, CompanionApplication.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    page = page_of(rows, params)
    return Page[ApplicationQueueItem](
        items=[
            ApplicationQueueItem(
                id=app.id,
                user_id=app.user_id,
                display_name=name,
                status=app.status,
                revision=app.revision,
                statement=app.statement,
                submitted_at=app.submitted_at,
            )
            for app, name in page.items
        ],
        next_offset=page.next_offset,
    )


@router.get('/companions/profiles', response_model=Page[ProfileQueueItem])
async def content_queue(
    admin: AdminUser,
    session: Session,
    params: Params,
    content_status: ContentStatus = ContentStatus.PENDING,
):
    rows = list(
        await session.execute(
            select(CompanionProfile, CompanionApplication.user_id)
            .join(CompanionApplication, CompanionApplication.id == CompanionProfile.application_id)
            .where(CompanionProfile.content_status == content_status)
            .order_by(CompanionProfile.updated_at, CompanionProfile.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    page = page_of(rows, params)
    return Page[ProfileQueueItem](
        items=[
            ProfileQueueItem(
                id=profile.id,
                user_id=user_id,
                display_name=profile.display_name,
                content_status=profile.content_status,
                revision=profile.revision,
                updated_at=profile.updated_at,
            )
            for profile, user_id in page.items
        ],
        next_offset=page.next_offset,
    )


# --- Identity verification -----------------------------------------------------------------


@router.get('/verifications', response_model=Page[identity.AdminVerificationView])
async def verification_queue(
    request: Request,
    admin: AdminUser,
    session: Session,
    params: Params,
    status: VerificationStatus = VerificationStatus.PENDING,
):
    page = await _page(
        session,
        select(IdentityVerification).where(IdentityVerification.status == status),
        params,
        (IdentityVerification.submitted_at, IdentityVerification.id),
    )
    return Page[identity.AdminVerificationView](
        items=[await identity.admin_view(request, item) for item in page.items],
        next_offset=page.next_offset,
    )


@router.get('/verifications/{verification_id}', response_model=identity.AdminVerificationView)
async def verification_detail(
    verification_id: UUID, request: Request, admin: AdminUser, session: Session
):
    item = await session.get(IdentityVerification, verification_id)
    if item is None:
        raise ApplicationError('verification_not_found', 'Verification not found', 404)
    return await identity.admin_view(request, item)


@router.post(
    '/verifications/{verification_id}/decision', response_model=identity.AdminVerificationView
)
async def verification_decision(
    verification_id: UUID,
    payload: identity.VerificationDecision,
    request: Request,
    admin: AdminUser,
    session: Session,
):
    audit(
        session,
        admin,
        f'verification.{payload.decision}',
        'verification',
        verification_id,
        payload.note,
    )
    item = await identity.decide(session, verification_id, admin, payload.decision, payload.note)
    return await identity.admin_view(request, item)


# --- Reports -------------------------------------------------------------------------------


class AdminReport(Output):
    id: UUID
    reporter_id: UUID
    reported_user_id: UUID
    booking_id: UUID | None
    category: str
    description: str
    status: str
    resolution_note: str | None
    created_at: UtcDatetime
    resolved_at: UtcDatetime | None


class ReportUpdate(Input):
    status: Literal['in_review', 'resolved', 'dismissed']
    note: str = Field(default='', max_length=2000)


@router.get('/reports', response_model=Page[AdminReport])
async def reports(
    admin: AdminUser, session: Session, params: Params, status: ReportStatus | None = None
):
    query = select(Report)
    if status:
        query = query.where(Report.status == status)
    page = await _page(session, query, params, (Report.created_at.desc(), Report.id))
    return Page[AdminReport](
        items=[AdminReport.model_validate(r) for r in page.items], next_offset=page.next_offset
    )


@router.post('/reports/{report_id}/status', response_model=AdminReport)
async def update_report(report_id: UUID, payload: ReportUpdate, admin: AdminUser, session: Session):
    report = await session.get(Report, report_id)
    if report is None:
        raise ApplicationError('report_not_found', 'Report not found', 404)
    if report.status in {ReportStatus.RESOLVED, ReportStatus.DISMISSED}:
        raise ApplicationError('report_closed', 'Report is already closed', 409)
    report.status = payload.status
    if payload.status != 'in_review':
        report.resolution_note = payload.note
        report.resolved_by = admin.id
        report.resolved_at = utc_now()
        notify(
            session,
            report.reporter_id,
            'report_closed',
            "Shikoyatingiz ko'rib chiqildi",
            payload.note[:200],
        )
    audit(session, admin, f'report.{payload.status}', 'report', report.id, payload.note)
    await commit(session)
    return report


# --- Disputes ------------------------------------------------------------------------------


class DisputeResolution(Input):
    outcome: Literal['completed', 'no_show', 'cancelled']
    refund_minor: int = Field(strict=True, ge=0)
    payout_minor: int = Field(strict=True, ge=0)
    note: str = Field(min_length=1, max_length=2000)


@router.get('/disputes', response_model=Page[disputes.DisputeResponse])
async def dispute_list(
    request: Request,
    admin: AdminUser,
    session: Session,
    params: Params,
    status: DisputeStatus | None = None,
):
    query = select(Dispute)
    if status:
        query = query.where(Dispute.status == status)
    page = await _page(session, query, params, (Dispute.created_at, Dispute.id))
    return Page[disputes.DisputeResponse](
        items=[await disputes.dispute_view(request, session, d) for d in page.items],
        next_offset=page.next_offset,
    )


@router.get('/disputes/{dispute_id}', response_model=disputes.DisputeResponse)
async def dispute_detail(dispute_id: UUID, request: Request, admin: AdminUser, session: Session):
    dispute = await session.get(Dispute, dispute_id)
    if dispute is None:
        raise ApplicationError('dispute_not_found', 'Dispute not found', 404)
    return await disputes.dispute_view(request, session, dispute)


@router.post('/disputes/{dispute_id}/review', response_model=disputes.DisputeResponse)
async def take_dispute(dispute_id: UUID, request: Request, admin: AdminUser, session: Session):
    dispute = await session.get(Dispute, dispute_id)
    if dispute is None:
        raise ApplicationError('dispute_not_found', 'Dispute not found', 404)
    if dispute.status != DisputeStatus.OPEN:
        raise ApplicationError('dispute_not_open', 'Dispute is not open', 409)
    dispute.status = DisputeStatus.UNDER_REVIEW
    audit(session, admin, 'dispute.review', 'dispute', dispute.id)
    await commit(session)
    return await disputes.dispute_view(request, session, dispute)


@router.post('/disputes/{dispute_id}/resolve', response_model=disputes.DisputeResponse)
async def resolve(
    dispute_id: UUID,
    payload: DisputeResolution,
    request: Request,
    admin: AdminUser,
    session: Session,
):
    from yondo_api.payments.service import process_refunds

    audit(
        session,
        admin,
        'dispute.resolve',
        'dispute',
        dispute_id,
        payload.note,
        payload.model_dump(exclude={'note'}),
    )
    dispute = await disputes.resolve_dispute(
        session,
        dispute_id,
        admin,
        outcome=payload.outcome,
        refund_minor=payload.refund_minor,
        payout_minor=payload.payout_minor,
        note=payload.note,
    )
    await process_refunds(session, request.app.state)
    return await disputes.dispute_view(request, session, dispute)


# --- Reviews -------------------------------------------------------------------------------


class AdminReview(Output):
    id: UUID
    booking_id: UUID
    author_id: UUID
    subject_id: UUID
    direction: str
    rating: int
    tags: list[str]
    text: str
    status: str
    hidden_reason: str | None
    created_at: UtcDatetime


class ReviewModeration(Input):
    action: Literal['hide', 'unhide']
    reason: str = Field(default='', max_length=2000)


@router.get('/reviews', response_model=Page[AdminReview])
async def review_list(
    admin: AdminUser,
    session: Session,
    params: Params,
    status: Literal['published', 'hidden'] | None = None,
):
    query = select(Review)
    if status:
        query = query.where(Review.status == status)
    page = await _page(session, query, params, (Review.created_at.desc(), Review.id))
    return Page[AdminReview](
        items=[AdminReview.model_validate(r) for r in page.items], next_offset=page.next_offset
    )


@router.post('/reviews/{review_id}/moderation', response_model=AdminReview)
async def moderate_review(
    review_id: UUID, payload: ReviewModeration, admin: AdminUser, session: Session
):
    review = await session.get(Review, review_id)
    if review is None:
        raise ApplicationError('review_not_found', 'Review not found', 404)
    hide = payload.action == 'hide'
    review.status = 'hidden' if hide else 'published'
    review.hidden_reason = payload.reason if hide else None
    review.hidden_by = admin.id if hide else None
    audit(session, admin, f'review.{payload.action}', 'review', review.id, payload.reason)
    await commit(session)
    return review


# --- SOS -----------------------------------------------------------------------------------


class AdminSos(Output):
    id: UUID
    user_id: UUID
    booking_id: UUID | None
    latitude: float | None
    longitude: float | None
    message: str
    status: str
    resolution_note: str | None
    created_at: UtcDatetime
    handled_at: UtcDatetime | None


class SosUpdate(Input):
    status: Literal['acknowledged', 'resolved']
    note: str = Field(default='', max_length=2000)


@router.get('/sos', response_model=Page[AdminSos])
async def sos_list(
    admin: AdminUser, session: Session, params: Params, status: SosStatus | None = None
):
    query = select(SosAlert)
    if status:
        query = query.where(SosAlert.status == status)
    page = await _page(session, query, params, (SosAlert.created_at.desc(), SosAlert.id))
    return Page[AdminSos](
        items=[AdminSos.model_validate(a) for a in page.items], next_offset=page.next_offset
    )


@router.post('/sos/{alert_id}/status', response_model=AdminSos)
async def update_sos(alert_id: UUID, payload: SosUpdate, admin: AdminUser, session: Session):
    alert = await session.get(SosAlert, alert_id)
    if alert is None:
        raise ApplicationError('sos_not_found', 'SOS alert not found', 404)
    if alert.status == SosStatus.RESOLVED:
        raise ApplicationError('sos_resolved', 'SOS alert is already resolved', 409)
    alert.status = payload.status
    alert.handled_by = admin.id
    alert.handled_at = utc_now()
    alert.resolution_note = payload.note or alert.resolution_note
    notify(
        session,
        alert.user_id,
        'sos_update',
        'SOS qabul qilindi' if payload.status == 'acknowledged' else 'SOS yopildi',
        payload.note[:200],
    )
    audit(session, admin, f'sos.{payload.status}', 'sos', alert.id, payload.note)
    await commit(session)
    return alert


# --- Audit log -----------------------------------------------------------------------------


class AuditRecord(Output):
    id: UUID
    admin_id: UUID | None
    action: str
    target_type: str
    target_id: UUID
    reason: str
    data: dict[str, str]
    created_at: UtcDatetime


@router.get('/audit', response_model=Page[AuditRecord])
async def audit_log(
    admin: AdminUser,
    session: Session,
    params: Params,
    target_type: str | None = None,
    target_id: UUID | None = None,
):
    query = select(AdminAuditLog)
    if target_type:
        query = query.where(AdminAuditLog.target_type == target_type)
    if target_id:
        query = query.where(AdminAuditLog.target_id == target_id)
    page = await _page(session, query, params, (AdminAuditLog.created_at.desc(), AdminAuditLog.id))
    return Page[AuditRecord](
        items=[AuditRecord.model_validate(a) for a in page.items], next_offset=page.next_offset
    )
