from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.integrations import IdentityEligibility, IdentityStatus
from yondo_api.companions.models import (
    ApplicationStatus,
    CompanionApplication,
    CompanionAvailability,
    CompanionProfile,
    ContentStatus,
)
from yondo_api.companions.schemas import AvailabilityWrite, CompanionStatus, ServiceWrite
from yondo_api.config import Settings
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType


def conflict(message: str) -> ApplicationError:
    return ApplicationError('invalid_companion_transition', message, 409)


async def save(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(
            'companion_record_conflict',
            'Duplicate or conflicting companion record',
            409,
        ) from exc


async def locked_user(session: AsyncSession, user_id: UUID) -> User:
    user = await session.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None:
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    return user


async def require_role(session: AsyncSession, user: User, role: UserRoleType) -> None:
    exists = await session.get(UserRole, (user.id, role))
    allowed = {AccountStatus.ACTIVE, AccountStatus.VERIFICATION_PENDING}
    if role == UserRoleType.ADMIN:
        allowed = {AccountStatus.ACTIVE}
    if exists is None or user.account_status not in allowed:
        raise ApplicationError('companion_forbidden', 'This operation is not permitted', 403)


async def application_for(session: AsyncSession, user_id: UUID) -> CompanionApplication:
    application = await session.scalar(
        select(CompanionApplication).where(CompanionApplication.user_id == user_id)
    )
    if application is None:
        raise ApplicationError('application_not_found', 'Companion application not found', 404)
    return application


async def profile_for(session: AsyncSession, user_id: UUID) -> CompanionProfile:
    profile = await session.scalar(
        select(CompanionProfile)
        .join(CompanionApplication)
        .where(CompanionApplication.user_id == user_id)
        .with_for_update(of=CompanionProfile)
        .execution_options(populate_existing=True)
    )
    if profile is None:
        raise ApplicationError('profile_not_found', 'Companion profile not found', 404)
    return profile


async def owned_resource(session: AsyncSession, model, resource_id: UUID, profile_id: UUID):
    resource = await session.scalar(
        select(model).where(model.id == resource_id, model.profile_id == profile_id)
    )
    if resource is None or getattr(resource, 'deleted_at', None) is not None:
        raise ApplicationError('companion_resource_not_found', 'Companion resource not found', 404)
    return resource


def invalidate_content(profile: CompanionProfile) -> None:
    profile.revision += 1
    profile.content_status = ContentStatus.DRAFT
    profile.activation_requested = False
    profile.reviewed_at = None
    profile.reviewed_by = None
    profile.review_note = None


def validate_service(payload: ServiceWrite, settings: Settings) -> None:
    if payload.price_minor < settings.companion_price_min_minor:
        raise ApplicationError('invalid_price', 'Price is below the configured limit', 422)
    if payload.service_code not in settings.companion_service_codes:
        raise ApplicationError('invalid_service', 'Service is not in the configured catalog', 422)
    if (
        settings.companion_allowed_currencies
        and payload.currency not in settings.companion_allowed_currencies
    ):
        raise ApplicationError('invalid_currency', 'Currency is not enabled', 422)
    if (
        settings.companion_price_max_minor is not None
        and payload.price_minor > settings.companion_price_max_minor
    ):
        raise ApplicationError('invalid_price', 'Price exceeds the configured limit', 422)
    if (
        settings.companion_allowed_unit_minutes
        and payload.unit_minutes not in settings.companion_allowed_unit_minutes
    ):
        raise ApplicationError('invalid_price_unit', 'Pricing duration is not enabled', 422)


async def ensure_no_overlap(
    session: AsyncSession,
    profile_id: UUID,
    payload: AvailabilityWrite,
    exclude_id: UUID | None = None,
) -> None:
    query = select(CompanionAvailability.id).where(
        CompanionAvailability.profile_id == profile_id,
        CompanionAvailability.starts_at < payload.ends_at,
        CompanionAvailability.ends_at > payload.starts_at,
    )
    if exclude_id is not None:
        query = query.where(CompanionAvailability.id != exclude_id)
    if await session.scalar(query) is not None:
        raise ApplicationError('availability_overlap', 'Availability windows cannot overlap', 409)


async def companion_status(
    session: AsyncSession,
    user: User,
    profile: CompanionProfile,
    identity: IdentityEligibility,
) -> CompanionStatus:
    """Canonical eligibility gate; future discovery must use this, not the stored intent flag.

    Adapter reads must reflect current Trust & Safety state. Unknown/unavailable is never verified.
    """
    application = await application_for(session, user.id)
    try:
        identity_status = IdentityStatus(await identity.get_status(session, user.id))
    except Exception as exc:
        raise ApplicationError(
            'identity_status_unavailable',
            'Identity eligibility is currently unavailable',
            503,
        ) from exc
    blockers = []
    if application.status != ApplicationStatus.APPROVED:
        blockers.append('application_not_approved')
    if profile.content_status != ContentStatus.APPROVED:
        blockers.append('content_not_approved')
    if user.account_status != AccountStatus.ACTIVE:
        blockers.append('account_not_active')
    if await session.get(UserRole, (user.id, UserRoleType.COMPANION)) is None:
        blockers.append('companion_role_required')
    if identity_status != IdentityStatus.VERIFIED:
        blockers.append('identity_not_verified')
    return CompanionStatus(
        application_status=application.status,
        content_status=profile.content_status,
        account_status=user.account_status,
        identity_status=identity_status,
        activation_requested=profile.activation_requested,
        publicly_active=profile.activation_requested and not blockers,
        blockers=blockers,
    )


async def review_application(
    session: AsyncSession,
    application_id: UUID,
    reviewer: User,
    decision: str,
    note: str,
    expected_revision: int,
) -> CompanionApplication:
    existing = await session.get(CompanionApplication, application_id)
    if existing is None:
        raise ApplicationError('application_not_found', 'Companion application not found', 404)
    if existing.user_id == reviewer.id:
        raise ApplicationError('self_approval_forbidden', 'Self approval is not permitted', 403)
    await locked_user(session, existing.user_id)
    await session.refresh(existing)
    if existing.status != ApplicationStatus.SUBMITTED:
        raise conflict('Only a submitted application can be reviewed')
    if existing.revision != expected_revision:
        raise ApplicationError('stale_companion_revision', 'Application changed; review again', 409)
    existing.status = (
        ApplicationStatus.APPROVED if decision == 'approve' else ApplicationStatus.REJECTED
    )
    existing.reviewed_by = reviewer.id
    existing.reviewed_at = datetime.now(UTC)
    existing.review_note = note
    await save(session)
    return existing


async def review_content(
    session: AsyncSession,
    profile_id: UUID,
    reviewer: User,
    decision: str,
    note: str,
    expected_revision: int,
) -> CompanionProfile:
    existing = await session.get(CompanionProfile, profile_id)
    if existing is None:
        raise ApplicationError('profile_not_found', 'Companion profile not found', 404)
    application = await session.get(CompanionApplication, existing.application_id)
    if application.user_id == reviewer.id:
        raise ApplicationError('self_approval_forbidden', 'Self approval is not permitted', 403)
    await locked_user(session, application.user_id)
    profile = await profile_for(session, application.user_id)
    if profile.content_status != ContentStatus.PENDING:
        raise conflict('Only submitted content can be reviewed')
    if profile.revision != expected_revision:
        raise ApplicationError('stale_companion_revision', 'Content changed; review again', 409)
    profile.content_status = (
        ContentStatus.APPROVED if decision == 'approve' else ContentStatus.REJECTED
    )
    profile.activation_requested = False
    profile.reviewed_by = reviewer.id
    profile.reviewed_at = datetime.now(UTC)
    profile.review_note = note
    await save(session)
    return profile
