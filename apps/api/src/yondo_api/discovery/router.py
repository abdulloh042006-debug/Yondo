from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError

from yondo_api.account.deletion import pending_deletion_exists
from yondo_api.api.errors import ApplicationError
from yondo_api.auth.dependencies import _bearer, get_authenticated_user
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.companions import service as companion_service
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.companions.integrations import IdentityEligibility
from yondo_api.companions.models import (
    ApplicationStatus,
    CompanionApplication,
    CompanionAvailability,
    CompanionPhoto,
    CompanionProfile,
    CompanionService,
    ContentStatus,
)
from yondo_api.companions.photos import download_url
from yondo_api.companions.schemas import PhotoDownload
from yondo_api.discovery.models import CompanionFavorite, CompanionLike
from yondo_api.discovery.schemas import (
    CompanionCard,
    DiscoveryPage,
    DiscoveryPhoto,
    DiscoveryService,
    FavoriteResponse,
    LikeState,
)
from yondo_api.discovery.textfold import fold_uz, fold_uz_sql
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType
from yondo_api.reviews.models import BookingReview

router = APIRouter(prefix='/discovery', tags=['discovery'])


def _public_candidates():
    return (
        select(CompanionProfile, User)
        .join(CompanionApplication, CompanionApplication.id == CompanionProfile.application_id)
        .join(User, User.id == CompanionApplication.user_id)
        .join(UserRole, UserRole.user_id == User.id)
        .where(
            CompanionApplication.status == ApplicationStatus.APPROVED,
            CompanionProfile.content_status == ContentStatus.APPROVED,
            CompanionProfile.activation_requested.is_(True),
            User.account_status == AccountStatus.ACTIVE,
            UserRole.role == UserRoleType.COMPANION,
            ~pending_deletion_exists(User.id),  # hidden as soon as deletion is requested
        )
    )


async def _optional_viewer(
    request: Request,
    session: Session,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User | None:
    """Signed-in caller if a valid token is sent; discovery stays public otherwise."""
    if credentials is None:
        return None
    try:
        return (await get_authenticated_user(credentials, session)).user
    except ApplicationError:
        return None


Viewer = Annotated[User | None, Depends(_optional_viewer)]


async def _stats(session, rows, viewer_id: UUID | None) -> dict[UUID, dict]:
    """Rating, review/meeting/like counts per profile, in four grouped queries."""
    profile_ids = [profile.id for profile, _ in rows]
    stats = {
        pid: {'rating': None, 'review_count': 0, 'meeting_count': 0, 'like_count': 0,
              'liked_by_me': None if viewer_id is None else False}
        for pid in profile_ids
    }
    if not profile_ids:
        return stats
    owner_by_profile = {profile.id: user.id for profile, user in rows}
    # Stars only from reviews of a completed booking of this profile, written about its owner.
    reviews = await session.execute(
        select(
            Booking.profile_id,
            BookingReview.reviewee_id,
            func.avg(BookingReview.stars),
            func.count(BookingReview.id),
        )
        .join(Booking, Booking.id == BookingReview.booking_id)
        .where(Booking.profile_id.in_(profile_ids), Booking.status == BookingStatus.COMPLETED)
        .group_by(Booking.profile_id, BookingReview.reviewee_id)
    )
    for profile_id, reviewee_id, average, count in reviews:
        if owner_by_profile.get(profile_id) == reviewee_id and average is not None:
            stats[profile_id]['rating'] = round(float(average), 2)
            stats[profile_id]['review_count'] = count
    meetings = await session.execute(
        select(Booking.profile_id, func.count(Booking.id))
        .where(Booking.profile_id.in_(profile_ids), Booking.status == BookingStatus.COMPLETED)
        .group_by(Booking.profile_id)
    )
    for profile_id, count in meetings:
        stats[profile_id]['meeting_count'] = count
    likes = await session.execute(
        select(CompanionLike.profile_id, func.count(CompanionLike.id))
        .where(CompanionLike.profile_id.in_(profile_ids))
        .group_by(CompanionLike.profile_id)
    )
    for profile_id, count in likes:
        stats[profile_id]['like_count'] = count
    if viewer_id is not None:
        for profile_id in await session.scalars(
            select(CompanionLike.profile_id).where(
                CompanionLike.user_id == viewer_id, CompanionLike.profile_id.in_(profile_ids)
            )
        ):
            stats[profile_id]['liked_by_me'] = True
    return stats


async def _card(session, profile: CompanionProfile, user: User, stats: dict) -> CompanionCard:
    services = list(
        await session.scalars(
            select(CompanionService)
            .where(CompanionService.profile_id == profile.id)
            .order_by(CompanionService.service_code)
        )
    )
    photos = list(
        await session.scalars(
            select(CompanionPhoto)
            .where(CompanionPhoto.profile_id == profile.id, CompanionPhoto.deleted_at.is_(None))
            .order_by(CompanionPhoto.position)
        )
    )
    return CompanionCard(
        **stats,
        id=profile.id,
        display_name=profile.display_name,
        bio=profile.bio,
        age=user.age,
        gender=user.gender,
        city=user.city,
        languages=profile.languages,
        interests=profile.interests,
        services=[DiscoveryService.model_validate(item) for item in services],
        photos=[DiscoveryPhoto.model_validate(item) for item in photos],
    )


async def _visible_rows(request: Request, session, statement):
    rows = (await session.execute(statement)).all()
    identity: IdentityEligibility = request.app.state.identity_eligibility
    visible = []
    for profile, user in rows:
        status = await companion_service.companion_status(session, user, profile, identity)
        if status.publicly_active:
            visible.append((profile, user))
    return visible


@router.get('/companions', response_model=DiscoveryPage)
async def search_companions(
    request: Request,
    session: Session,
    viewer: Viewer,
    q: str | None = Query(default=None, max_length=128),
    city: str | None = Query(default=None, max_length=128),
    gender: str | None = Query(default=None, max_length=64),
    age_min: int | None = Query(default=None, ge=18, le=120),
    age_max: int | None = Query(default=None, ge=18, le=120),
    rating_min: float | None = Query(default=None, ge=1, le=5),
    service_code: str | None = Query(default=None, pattern=r'^[a-z][a-z0-9_]{0,63}$'),
    language: str | None = Query(default=None, max_length=64),
    interest: str | None = Query(default=None, max_length=64),
    price_min_minor: int | None = Query(default=None, ge=0),
    price_max_minor: int | None = Query(default=None, ge=0),
    available_from: datetime | None = None,
    available_until: datetime | None = None,
    sort: Literal['default', 'rating', 'meetings', 'likes'] = Query(
        default='default',
        description='Descending by rating, completed meetings or likes; ties by profile id.',
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    if age_min is not None and age_max is not None and age_min > age_max:
        raise ApplicationError('invalid_discovery_filter', 'age_min must not exceed age_max', 422)
    if price_min_minor is not None and price_max_minor is not None:
        if price_min_minor > price_max_minor:
            raise ApplicationError(
                'invalid_discovery_filter', 'price_min_minor must not exceed price_max_minor', 422
            )
    if (available_from is None) != (available_until is None):
        raise ApplicationError(
            'invalid_discovery_filter',
            'available_from and available_until must be supplied together',
            422,
        )
    if available_from is not None:
        if (
            available_from.tzinfo is None
            or available_from.utcoffset() is None
            or available_until.tzinfo is None
            or available_until.utcoffset() is None
        ):
            raise ApplicationError(
                'invalid_discovery_filter', 'Availability filters must include a timezone', 422
            )
        available_from = available_from.astimezone(UTC)
        available_until = available_until.astimezone(UTC)
    statement = _public_candidates()
    if q:
        # Both Uzbek Latin alphabets (1995 and 2026) match each other; see discovery/textfold.py.
        needle = f'%{fold_uz(q.strip())}%'
        statement = statement.where(
            or_(
                fold_uz_sql(CompanionProfile.display_name).like(needle),
                fold_uz_sql(CompanionProfile.bio).like(needle),
            )
        )
    if city:
        statement = statement.where(fold_uz_sql(User.city) == fold_uz(city.strip()))
    if gender:
        statement = statement.where(User.gender.ilike(gender.strip()))
    if age_min is not None:
        statement = statement.where(User.age >= age_min)
    if age_max is not None:
        statement = statement.where(User.age <= age_max)
    if service_code or price_min_minor is not None or price_max_minor is not None:
        service_query = select(CompanionService.id).where(
            CompanionService.profile_id == CompanionProfile.id
        )
        if service_code:
            service_query = service_query.where(CompanionService.service_code == service_code)
        if price_min_minor is not None:
            service_query = service_query.where(CompanionService.price_minor >= price_min_minor)
        if price_max_minor is not None:
            service_query = service_query.where(CompanionService.price_minor <= price_max_minor)
        statement = statement.where(exists(service_query))
    # JSON arrays are compared after retrieval so filtering is exact on SQLite and PostgreSQL.
    if available_from is not None:
        if available_until <= available_from:
            raise ApplicationError(
                'invalid_discovery_filter', 'available_until must be after available_from', 422
            )
        availability = select(CompanionAvailability.id).where(
            CompanionAvailability.profile_id == CompanionProfile.id,
            CompanionAvailability.starts_at <= available_from,
            CompanionAvailability.ends_at >= available_until,
        )
        reservations = select(Booking.id).where(
            Booking.profile_id == CompanionProfile.id,
            Booking.status.in_(
                (
                    BookingStatus.PENDING,
                    BookingStatus.ACCEPTED,
                    BookingStatus.CONFIRMED,
                    BookingStatus.ACTIVE,
                )
            ),
            Booking.starts_at < available_until,
            Booking.ends_at > available_from,
        )
        statement = statement.where(exists(availability), ~exists(reservations))
    statement = statement.order_by(CompanionProfile.id)
    rows = await _visible_rows(request, session, statement)
    if language:
        expected = language.strip().casefold()
        rows = [(p, u) for p, u in rows if any(x.casefold() == expected for x in p.languages)]
    if interest:
        expected = interest.strip().casefold()
        rows = [(p, u) for p, u in rows if any(x.casefold() == expected for x in p.interests)]
    stats = await _stats(session, rows, viewer.id if viewer else None)
    if rating_min is not None:
        rows = [
            (p, u) for p, u in rows
            if stats[p.id]['rating'] is not None and stats[p.id]['rating'] >= rating_min
        ]
    if sort != 'default':
        # Python's sort is stable: rows are already ordered by profile id (the final tie-breaker).
        def key(row):
            item = stats[row[0].id]
            rating = item['rating'] if item['rating'] is not None else -1.0
            if sort == 'rating':
                return (-rating, -item['review_count'])
            if sort == 'meetings':
                return (-item['meeting_count'], -rating)
            return (-item['like_count'], -rating)

        rows = sorted(rows, key=key)
    selected = rows[offset : offset + limit + 1]
    cards = [
        await _card(session, profile, user, stats[profile.id])
        for profile, user in selected[:limit]
    ]
    return DiscoveryPage(items=cards, limit=limit, offset=offset, has_more=len(selected) > limit)


@router.get('/companions/{profile_id}', response_model=CompanionCard)
async def get_companion(profile_id: UUID, request: Request, session: Session, viewer: Viewer):
    row = (
        await session.execute(_public_candidates().where(CompanionProfile.id == profile_id))
    ).first()
    if row is None:
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    profile, user = row
    status = await companion_service.companion_status(
        session, user, profile, request.app.state.identity_eligibility
    )
    if not status.publicly_active:
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    stats = await _stats(session, [(profile, user)], viewer.id if viewer else None)
    return await _card(session, profile, user, stats[profile.id])


@router.get('/companions/{profile_id}/photos/{photo_id}/download', response_model=PhotoDownload)
async def download_public_photo(
    profile_id: UUID, photo_id: UUID, request: Request, session: Session
):
    row = (
        await session.execute(_public_candidates().where(CompanionProfile.id == profile_id))
    ).first()
    if row is None:
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    profile, user = row
    status = await companion_service.companion_status(
        session, user, profile, request.app.state.identity_eligibility
    )
    if not status.publicly_active:
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    photo = await session.scalar(
        select(CompanionPhoto).where(
            CompanionPhoto.id == photo_id,
            CompanionPhoto.profile_id == profile.id,
            CompanionPhoto.deleted_at.is_(None),
        )
    )
    if photo is None:
        raise ApplicationError('companion_photo_not_found', 'Photo not found', 404)
    return await download_url(request, photo)


async def _customer(principal: Principal, session: Session) -> User:
    user = await session.get(User, principal.user.id)
    if user is None or user.account_status != AccountStatus.ACTIVE:
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)
    if await session.get(UserRole, (user.id, UserRoleType.CUSTOMER)) is None:
        raise ApplicationError('customer_role_required', 'Customer role is required', 403)
    return user


@router.get('/favorites', response_model=list[CompanionCard])
async def list_favorites(request: Request, principal: Principal, session: Session):
    customer = await _customer(principal, session)
    favorites = list(
        await session.scalars(
            select(CompanionFavorite)
            .where(CompanionFavorite.customer_id == customer.id)
            .order_by(CompanionFavorite.created_at.desc(), CompanionFavorite.profile_id)
        )
    )
    profile_ids = [favorite.profile_id for favorite in favorites]
    if not profile_ids:
        return []
    rows = await _visible_rows(
        request, session, _public_candidates().where(CompanionProfile.id.in_(profile_ids))
    )
    by_id = {profile.id: (profile, user) for profile, user in rows}
    stats = await _stats(session, rows, customer.id)
    return [
        await _card(session, *by_id[profile_id], stats[profile_id])
        for profile_id in profile_ids
        if profile_id in by_id
    ]


@router.put('/favorites/{profile_id}', response_model=FavoriteResponse, status_code=201)
async def add_favorite(profile_id: UUID, request: Request, principal: Principal, session: Session):
    customer = await _customer(principal, session)
    row = (
        await session.execute(_public_candidates().where(CompanionProfile.id == profile_id))
    ).first()
    if row is None:
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    profile, user = row
    status = await companion_service.companion_status(
        session, user, profile, request.app.state.identity_eligibility
    )
    if not status.publicly_active:
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    favorite = await session.scalar(
        select(CompanionFavorite).where(
            CompanionFavorite.customer_id == customer.id,
            CompanionFavorite.profile_id == profile_id,
        )
    )
    if favorite is None:
        favorite = CompanionFavorite(customer_id=customer.id, profile_id=profile_id)
        session.add(favorite)
        await session.commit()
        await session.refresh(favorite)
    return FavoriteResponse(profile_id=favorite.profile_id, created_at=favorite.created_at)


@router.delete('/favorites/{profile_id}', status_code=204)
async def remove_favorite(
    profile_id: UUID, request: Request, principal: Principal, session: Session
):
    customer = await _customer(principal, session)
    favorite = await session.scalar(
        select(CompanionFavorite).where(
            CompanionFavorite.customer_id == customer.id,
            CompanionFavorite.profile_id == profile_id,
        )
    )
    if favorite is not None:
        await session.delete(favorite)
        await session.commit()
    return Response(status_code=204)


async def _liker(principal: Principal, session: Session) -> User:
    user = await session.get(User, principal.user.id)
    if user is None or user.account_status != AccountStatus.ACTIVE:
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)
    return user


async def _like_state(session, profile_id: UUID, user_id: UUID) -> LikeState:
    count = await session.scalar(
        select(func.count(CompanionLike.id)).where(CompanionLike.profile_id == profile_id)
    )
    mine = await session.scalar(
        select(CompanionLike.id).where(
            CompanionLike.profile_id == profile_id, CompanionLike.user_id == user_id
        )
    )
    return LikeState(profile_id=profile_id, like_count=count, liked_by_me=mine is not None)


@router.put('/companions/{profile_id}/like', response_model=LikeState)
async def like_companion(
    profile_id: UUID, request: Request, principal: Principal, session: Session
):
    """Like a visible companion profile. Idempotent; separate from private favourites."""
    user = await _liker(principal, session)
    row = (
        await session.execute(_public_candidates().where(CompanionProfile.id == profile_id))
    ).first()
    if row is None:
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    profile, owner = row
    status = await companion_service.companion_status(
        session, owner, profile, request.app.state.identity_eligibility
    )
    if not status.publicly_active:
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    if owner.id == user.id:
        raise ApplicationError('like_own_profile', 'You cannot like your own profile', 409)
    existing = await session.scalar(
        select(CompanionLike.id).where(
            CompanionLike.profile_id == profile_id, CompanionLike.user_id == user.id
        )
    )
    if existing is None:
        session.add(CompanionLike(user_id=user.id, profile_id=profile_id))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()  # a concurrent identical like won: same end state
    return await _like_state(session, profile_id, user.id)


@router.delete('/companions/{profile_id}/like', response_model=LikeState)
async def unlike_companion(profile_id: UUID, principal: Principal, session: Session):
    user = await _liker(principal, session)
    like = await session.scalar(
        select(CompanionLike).where(
            CompanionLike.profile_id == profile_id, CompanionLike.user_id == user.id
        )
    )
    if like is not None:
        await session.delete(like)
        await session.commit()
    return await _like_state(session, profile_id, user.id)
