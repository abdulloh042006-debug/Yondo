from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import exists, func, or_, select

from yondo_api.api.errors import ApplicationError
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
from yondo_api.discovery.models import CompanionFavorite
from yondo_api.discovery.schemas import (
    CompanionCard,
    DiscoveryPage,
    DiscoveryPhoto,
    DiscoveryService,
    FavoriteResponse,
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
        )
    )


async def _card(session, profile: CompanionProfile, user: User) -> CompanionCard:
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
    rating, review_count = (
        await session.execute(
            select(func.avg(BookingReview.stars), func.count(BookingReview.id)).where(
                BookingReview.reviewee_id == user.id
            )
        )
    ).one()
    return CompanionCard(
        rating=round(float(rating), 2) if rating is not None else None,
        review_count=review_count,
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
    q: str | None = Query(default=None, max_length=128),
    city: str | None = Query(default=None, max_length=128),
    gender: str | None = Query(default=None, max_length=64),
    age_min: int | None = Query(default=None, ge=18, le=120),
    age_max: int | None = Query(default=None, ge=18, le=120),
    rating_min: int | None = Query(default=None, ge=1, le=5),
    service_code: str | None = Query(default=None, pattern=r'^[a-z][a-z0-9_]{0,63}$'),
    language: str | None = Query(default=None, max_length=64),
    interest: str | None = Query(default=None, max_length=64),
    price_min_minor: int | None = Query(default=None, ge=0),
    price_max_minor: int | None = Query(default=None, ge=0),
    available_from: datetime | None = None,
    available_until: datetime | None = None,
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
    if rating_min is not None:
        real_rating = (
            select(func.avg(BookingReview.stars))
            .where(BookingReview.reviewee_id == User.id)
            .scalar_subquery()
        )
        statement = statement.where(real_rating >= rating_min)
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
    selected = rows[offset : offset + limit + 1]
    cards = [await _card(session, profile, user) for profile, user in selected[:limit]]
    return DiscoveryPage(items=cards, limit=limit, offset=offset, has_more=len(selected) > limit)


@router.get('/companions/{profile_id}', response_model=CompanionCard)
async def get_companion(profile_id: UUID, request: Request, session: Session):
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
    return await _card(session, profile, user)


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
    return [
        await _card(session, *by_id[profile_id])
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
