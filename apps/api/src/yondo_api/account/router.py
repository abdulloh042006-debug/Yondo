from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Response
from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from yondo_api.account import deletion
from yondo_api.account.legal import DELETION_WINDOW_DAYS, LEGAL_DOCUMENTS
from yondo_api.account.models import SupportRequest, UserConsent
from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Principal, Session

router = APIRouter(tags=['account'])
legal_router = APIRouter(prefix='/legal', tags=['legal'])

def _utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; every instant in this API is UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(_utc)]
LegalDocument = Literal['terms', 'privacy']
SupportCategory = Literal['account', 'booking', 'payment', 'safety', 'technical', 'other']


class DeletionState(BaseModel):
    pending: bool
    requested_at: UtcDatetime | None = None
    due_at: UtcDatetime | None = Field(
        default=None, description='The erasure job processes the request from this instant.'
    )
    window_days: int = Field(description='Personal data is erased within this many days.')


class DeletionRequestWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    confirm: bool = Field(description='Must be true: the user confirmed in the app.')


class LegalVersions(BaseModel):
    terms: str
    privacy: str


class ConsentWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document: LegalDocument
    version: str = Field(min_length=1, max_length=32)


class ConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document: LegalDocument
    version: str
    accepted_at: UtcDatetime


class ConsentState(BaseModel):
    required: list[ConsentWrite] = Field(
        description='Current document versions this user has not accepted yet.'
    )
    accepted: list[ConsentRead]


class SupportWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: SupportCategory
    message: str = Field(min_length=10, max_length=4000)


class SupportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    category: SupportCategory
    message: str
    status: Literal['open', 'answered', 'closed']
    reply: str | None
    created_at: UtcDatetime
    replied_at: UtcDatetime | None


def _state(request) -> DeletionState:
    if request is None:
        return DeletionState(pending=False, window_days=DELETION_WINDOW_DAYS)
    return DeletionState(
        pending=True,
        requested_at=request.requested_at,
        due_at=request.due_at,
        window_days=DELETION_WINDOW_DAYS,
    )


@router.get('/account/deletion', response_model=DeletionState)
async def deletion_state(principal: Principal, session: Session):
    return _state(await deletion.pending_request(session, principal.user.id))


@router.post('/account/deletion', response_model=DeletionState, status_code=201)
async def request_deletion(payload: DeletionRequestWrite, principal: Principal, session: Session):
    if not payload.confirm:
        raise ApplicationError(
            'deletion_confirmation_required', 'Confirm the deletion request', 422
        )
    user_id = principal.user.id
    if await deletion.pending_request(session, user_id) is not None:
        raise ApplicationError('deletion_already_requested', 'Deletion already requested', 409)
    if await deletion.has_open_bookings(session, user_id):
        raise ApplicationError(
            'deletion_open_bookings', 'Finish or cancel open bookings first', 409
        )
    item = deletion.new_request(user_id, datetime.now(UTC))
    session.add(item)
    try:
        await session.commit()
    except IntegrityError as exc:  # concurrent duplicate request
        await session.rollback()
        raise ApplicationError(
            'deletion_already_requested', 'Deletion already requested', 409
        ) from exc
    return _state(item)


@router.delete('/account/deletion', status_code=204)
async def cancel_deletion(principal: Principal, session: Session):
    item = await deletion.pending_request(session, principal.user.id)
    if item is None:
        raise ApplicationError('deletion_not_found', 'No pending deletion request', 404)
    item.status = 'cancelled'
    item.cancelled_at = datetime.now(UTC)
    await session.commit()
    return Response(status_code=204)


@legal_router.get('/versions', response_model=LegalVersions)
async def legal_versions():
    return LegalVersions(**LEGAL_DOCUMENTS)


@router.get('/account/consents', response_model=ConsentState)
async def consent_state(principal: Principal, session: Session):
    accepted = list(
        await session.scalars(
            select(UserConsent)
            .where(UserConsent.user_id == principal.user.id)
            .order_by(UserConsent.accepted_at)
        )
    )
    have = {(c.document, c.version) for c in accepted}
    required = [
        ConsentWrite(document=doc, version=version)
        for doc, version in LEGAL_DOCUMENTS.items()
        if (doc, version) not in have
    ]
    return ConsentState(required=required, accepted=accepted)


@router.post('/account/consents', response_model=ConsentRead, status_code=201)
async def accept_document(payload: ConsentWrite, principal: Principal, session: Session):
    if LEGAL_DOCUMENTS[payload.document] != payload.version:
        # The client showed a different text than the current one: never record that.
        raise ApplicationError(
            'consent_version_outdated', 'This document version is not current', 409
        )
    existing = await session.scalar(
        select(UserConsent).where(
            UserConsent.user_id == principal.user.id,
            UserConsent.document == payload.document,
            UserConsent.version == payload.version,
        )
    )
    if existing is not None:
        return existing
    item = UserConsent(
        user_id=principal.user.id,
        document=payload.document,
        version=payload.version,
        accepted_at=datetime.now(UTC),
    )
    session.add(item)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        item = await session.scalar(
            select(UserConsent).where(
                UserConsent.user_id == principal.user.id,
                UserConsent.document == payload.document,
                UserConsent.version == payload.version,
            )
        )
    return item


@router.post('/support/requests', response_model=SupportRead, status_code=201)
async def create_support_request(payload: SupportWrite, principal: Principal, session: Session):
    item = SupportRequest(
        user_id=principal.user.id,
        category=payload.category,
        message=payload.message.strip(),
        status='open',
    )
    if len(item.message) < 10:
        raise ApplicationError('support_message_too_short', 'Message is too short', 422)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get('/support/requests', response_model=list[SupportRead])
async def own_support_requests(principal: Principal, session: Session):
    return list(
        await session.scalars(
            select(SupportRequest)
            .where(SupportRequest.user_id == principal.user.id)
            .order_by(SupportRequest.created_at.desc())
            .limit(50)
        )
    )
