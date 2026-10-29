"""Account deletion: request, cancel, and the erasure job.

Policy (owner decision 2026-10-23, documented in the privacy policy draft):
* the user asks in the app and confirms explicitly; while the request is pending the account stays
  usable only to cancel it — the companion profile is hidden and no new bookings can be made;
* personal data is erased or irreversibly de-identified within 30 days (the job runs daily);
* records that may have to be retained (bookings, payments, payouts, reviews, chat messages of a
  booking, safety reports/alerts, admin audit, consent records, beta feedback) are kept, but they
  then point at a de-identified account with no phone number, profile or contact data.
Which records are legally required, and for how long, must still be confirmed by the operator.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.account.legal import DELETION_DUE_AFTER_DAYS
from yondo_api.account.models import AccountDeletionRequest, SupportRequest
from yondo_api.beta.models import BetaEnrollment
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.cancellations.models import CancellationEvent
from yondo_api.chat.models import ChatAccessTicket, ChatReadCursor
from yondo_api.companions.models import (
    CompanionApplication,
    CompanionAvailability,
    CompanionPhoto,
    CompanionProfile,
    CompanionService,
)
from yondo_api.discovery.models import CompanionFavorite
from yondo_api.gifts.models import GiftCartItem
from yondo_api.models.auth import AuthSession, OtpChallenge
from yondo_api.models.user import AccountStatus, User, UserRole
from yondo_api.notifications.models import UserNotification
from yondo_api.safety.models import TrustedContact, UserBlock
from yondo_api.stories.models import CompanionStory

logger = logging.getLogger(__name__)

OPEN_BOOKING_STATUSES = (
    BookingStatus.PENDING,
    BookingStatus.ACCEPTED,
    BookingStatus.CONFIRMED,
    BookingStatus.ACTIVE,
)


def _profile_ids(user_id: UUID):
    return (
        select(CompanionProfile.id)
        .join(CompanionApplication, CompanionApplication.id == CompanionProfile.application_id)
        .where(CompanionApplication.user_id == user_id)
    )


async def has_open_bookings(session: AsyncSession, user_id: UUID) -> bool:
    found = await session.scalar(
        select(Booking.id)
        .where(
            Booking.status.in_(OPEN_BOOKING_STATUSES),
            or_(Booking.customer_id == user_id, Booking.profile_id.in_(_profile_ids(user_id))),
        )
        .limit(1)
    )
    return found is not None


async def pending_request(session: AsyncSession, user_id: UUID) -> AccountDeletionRequest | None:
    return await session.scalar(
        select(AccountDeletionRequest).where(
            AccountDeletionRequest.user_id == user_id,
            AccountDeletionRequest.status == 'pending',
        )
    )


def pending_deletion_exists(user_id_column):
    """SQL predicate: the account has an open deletion request (used to hide it from discovery)."""
    return (
        select(AccountDeletionRequest.id)
        .where(
            AccountDeletionRequest.user_id == user_id_column,
            AccountDeletionRequest.status == 'pending',
        )
        .exists()
    )


def new_request(user_id: UUID, now: datetime) -> AccountDeletionRequest:
    return AccountDeletionRequest(
        user_id=user_id,
        status='pending',
        requested_at=now,
        due_at=now + timedelta(days=DELETION_DUE_AFTER_DAYS),
    )


async def erase_account(
    session: AsyncSession, user: User, storage, now: datetime
) -> None:
    """De-identify one account in the current transaction (the caller commits)."""
    uid = user.id
    profile_ids = list(await session.scalars(_profile_ids(uid)))
    if profile_ids:
        photos = list(
            await session.scalars(
                select(CompanionPhoto).where(CompanionPhoto.profile_id.in_(profile_ids))
            )
        )
        for photo in photos:
            if storage is not None:
                try:
                    await storage.delete(photo.storage_key)
                except Exception:  # keep the tombstone; storage GC can retry from it
                    logger.exception('Photo object could not be deleted: photo_id=%s', photo.id)
            photo.deleted_at = photo.deleted_at or now
            photo.position = None
            photo.caption = ''
        for story in await session.scalars(
            select(CompanionStory).where(CompanionStory.profile_id.in_(profile_ids))
        ):
            story.removed_at = story.removed_at or now
            story.caption = 'deleted'
            story.photo_id = None
            story.removal_note = None
        for profile in await session.scalars(
            select(CompanionProfile).where(CompanionProfile.id.in_(profile_ids))
        ):
            profile.display_name = 'deleted'
            profile.bio = ''
            profile.languages = []
            profile.interests = []
            profile.activation_requested = False
        for service in await session.scalars(
            select(CompanionService).where(CompanionService.profile_id.in_(profile_ids))
        ):
            service.description = ''
        await session.execute(
            delete(CompanionAvailability).where(CompanionAvailability.profile_id.in_(profile_ids))
        )
        await session.execute(
            delete(CompanionFavorite).where(CompanionFavorite.profile_id.in_(profile_ids))
        )
    for application in await session.scalars(
        select(CompanionApplication).where(CompanionApplication.user_id == uid)
    ):
        application.statement = ''
    # Cancellation records stay (de-identified, counts only); the user's own free text goes.
    for item in await session.scalars(
        select(CancellationEvent).where(CancellationEvent.subject_user_id == uid)
    ):
        item.reason, item.dispute_note = '', None
    for model, column in (
        (CompanionFavorite, CompanionFavorite.customer_id),
        (TrustedContact, TrustedContact.owner_id),
        (UserBlock, UserBlock.blocker_id),
        (GiftCartItem, GiftCartItem.customer_id),
        (UserNotification, UserNotification.recipient_id),
        (ChatReadCursor, ChatReadCursor.user_id),
        (ChatAccessTicket, ChatAccessTicket.user_id),
        (SupportRequest, SupportRequest.user_id),
        (BetaEnrollment, BetaEnrollment.user_id),
        (AuthSession, AuthSession.user_id),
        (UserRole, UserRole.user_id),
    ):
        await session.execute(delete(model).where(column == uid))
    await session.execute(
        delete(OtpChallenge).where(OtpChallenge.phone_number == user.phone_number)
    )
    user.phone_number = f'deleted-{uid.hex[:24]}'
    user.age = None
    user.gender = None
    user.city = None
    user.ui_locale = None
    user.account_status = AccountStatus.DELETED


async def process_due_deletions(
    session: AsyncSession, storage, now: datetime | None = None
) -> tuple[list[UUID], list[UUID]]:
    """Erase every account whose request is due. Returns (erased, skipped-with-open-bookings)."""
    now = now or datetime.now(UTC)
    due = list(
        await session.scalars(
            select(AccountDeletionRequest)
            .where(
                AccountDeletionRequest.status == 'pending',
                AccountDeletionRequest.due_at <= now,
            )
            .order_by(AccountDeletionRequest.due_at)
        )
    )
    erased: list[UUID] = []
    skipped: list[UUID] = []
    for request in due:
        if await has_open_bookings(session, request.user_id):
            # Should not happen (new bookings are refused while pending); never erase a party
            # of an open booking silently: an operator must resolve it first.
            logger.warning('Deletion due but bookings are open: user_id=%s', request.user_id)
            skipped.append(request.user_id)
            continue
        user = await session.get(User, request.user_id)
        if user is not None and user.account_status != AccountStatus.DELETED:
            await erase_account(session, user, storage, now)
        request.status = 'completed'
        request.completed_at = now
        await session.commit()
        erased.append(request.user_id)
    return erased, skipped
