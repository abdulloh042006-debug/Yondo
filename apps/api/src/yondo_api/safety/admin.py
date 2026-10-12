"""Admin-only queues for recorded safety incidents; no external emergency dispatch."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Admin, Session
from yondo_api.safety.models import SafetyAcknowledgement, SafetyAlert, SafetyReport

router = APIRouter(prefix='/admin/safety', tags=['admin safety'])


class AcknowledgeWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    note: str = Field(min_length=8, max_length=2000)


class AcknowledgementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    report_id: UUID | None
    alert_id: UUID | None
    admin_id: UUID
    note: str
    created_at: datetime


class AdminReportRead(BaseModel):
    id: UUID
    reporter_id: UUID
    reported_user_id: UUID
    booking_id: UUID | None
    category: str
    description: str
    status: str
    created_at: datetime
    acknowledged: bool


class AdminAlertRead(BaseModel):
    id: UUID
    booking_id: UUID
    creator_id: UUID
    created_at: datetime
    acknowledged: bool
    emergency_service_contacted: bool = False


@router.get('/summary')
async def safety_summary(admin: Admin, session: Session):
    open_reports = await session.scalar(
        select(func.count()).select_from(SafetyReport).where(SafetyReport.status == 'open')
    )
    unacknowledged_alerts = await session.scalar(
        select(func.count()).select_from(SafetyAlert).where(
            ~exists(
                select(SafetyAcknowledgement.id).where(
                    SafetyAcknowledgement.alert_id == SafetyAlert.id
                )
            )
        )
    )
    return {
        'open_reports': open_reports or 0,
        'unacknowledged_sos': unacknowledged_alerts or 0,
        'emergency_dispatch_configured': False,
    }


@router.get('/reports', response_model=list[AdminReportRead])
async def list_admin_reports(
    admin: Admin,
    session: Session,
    status: Literal['open', 'in_review'] | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = (
        select(SafetyReport, SafetyAcknowledgement.id)
        .outerjoin(
            SafetyAcknowledgement,
            SafetyAcknowledgement.report_id == SafetyReport.id,
        )
    )
    if status is not None:
        query = query.where(SafetyReport.status == status)
    rows = (
        await session.execute(
            query.order_by(SafetyReport.created_at.desc(), SafetyReport.id.desc())
            .offset(offset).limit(limit)
        )
    ).all()
    return [
        AdminReportRead(
            id=report.id,
            reporter_id=report.reporter_id,
            reported_user_id=report.reported_user_id,
            booking_id=report.booking_id,
            category=report.category,
            description=report.description,
            status=report.status,
            created_at=report.created_at,
            acknowledged=acknowledgement_id is not None,
        )
        for report, acknowledgement_id in rows
    ]


@router.get('/alerts', response_model=list[AdminAlertRead])
async def list_admin_alerts(
    admin: Admin,
    session: Session,
    unacknowledged_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(SafetyAlert, SafetyAcknowledgement.id).outerjoin(
        SafetyAcknowledgement,
        SafetyAcknowledgement.alert_id == SafetyAlert.id,
    )
    if unacknowledged_only:
        query = query.where(SafetyAcknowledgement.id.is_(None))
    rows = (
        await session.execute(
            query.order_by(SafetyAlert.created_at.desc(), SafetyAlert.id.desc())
            .offset(offset).limit(limit)
        )
    ).all()
    return [
        AdminAlertRead(
            id=alert.id,
            booking_id=alert.booking_id,
            creator_id=alert.creator_id,
            created_at=alert.created_at,
            acknowledged=acknowledgement_id is not None,
        )
        for alert, acknowledgement_id in rows
    ]


async def acknowledge(
    session: Session, admin_id: UUID, kind: Literal['report', 'sos'],
    target_id: UUID, note: str
) -> SafetyAcknowledgement:
    if kind == 'report':
        target = await session.scalar(
            select(SafetyReport).where(SafetyReport.id == target_id)
            .with_for_update().execution_options(populate_existing=True)
        )
        column = SafetyAcknowledgement.report_id
    else:
        target = await session.scalar(
            select(SafetyAlert).where(SafetyAlert.id == target_id)
            .with_for_update().execution_options(populate_existing=True)
        )
        column = SafetyAcknowledgement.alert_id
    if target is None:
        raise ApplicationError('safety_item_not_found', 'Safety item not found', 404)
    previous = await session.scalar(
        select(SafetyAcknowledgement).where(column == target_id)
    )
    if previous is not None:
        return previous  # Acknowledgements are immutable, including on retries.
    clean_note = note.strip()
    if len(clean_note) < 8:
        raise ApplicationError('invalid_safety_note', 'Review note is too short', 422)
    if kind == 'report':
        if target.status != 'open':
            raise ApplicationError('report_not_open', 'Report is already under review', 409)
        target.status = 'in_review'
    entry = SafetyAcknowledgement(
        report_id=target_id if kind == 'report' else None,
        alert_id=target_id if kind == 'sos' else None,
        admin_id=admin_id,
        note=clean_note,
    )
    session.add(entry)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(
            'safety_review_conflict', 'Review state changed; retry', 409
        ) from exc
    await session.refresh(entry)
    return entry


@router.post('/reports/{report_id}/acknowledge', response_model=AcknowledgementRead)
async def acknowledge_report(
    report_id: UUID, payload: AcknowledgeWrite, admin: Admin, session: Session
):
    return await acknowledge(session, admin.id, 'report', report_id, payload.note)


@router.post('/alerts/{alert_id}/acknowledge', response_model=AcknowledgementRead)
async def acknowledge_alert(
    alert_id: UUID, payload: AcknowledgeWrite, admin: Admin, session: Session
):
    return await acknowledge(session, admin.id, 'sos', alert_id, payload.note)
