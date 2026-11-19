"""Vendor shops: application with a mandatory shop profile, admin review, suspension.

Product decisions §4 and the CEO's answers of 2026-11-19 (docs/gifts.md):
- a vendor becomes active only on approval, which needs the identity verification (ID + selfie,
  images deleted at the decision) to be `verified`; the Vendor role is granted then;
- the catalogue shows a product only while its vendor's shop is approved (not suspended);
- decisions and suspensions are audited and the vendor is notified in-app.
"""

import asyncio
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from anyio import to_thread
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.admin.models import AdminAuditEvent
from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Admin, Principal, Session, object_storage
from yondo_api.companions.photos import IMAGE_TYPES, compensate_upload, process_image
from yondo_api.gifts.shop_models import VendorShop
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType
from yondo_api.notifications.models import UserNotification
from yondo_api.verification.models import IdentityVerification, VerificationStatus

router = APIRouter(tags=['gift vendors'])
ShopStatus = Literal['pending', 'approved', 'rejected', 'suspended']


def _now() -> datetime:
    return datetime.now(UTC)


def shop_approved_clause(vendor_column):
    """SQL: the vendor (a users.id column) has an approved, unsuspended shop."""
    return exists(
        select(VendorShop.id).where(
            VendorShop.user_id == vendor_column, VendorShop.status == 'approved'
        )
    )


async def vendor_is_active(session: AsyncSession, vendor_id: UUID) -> bool:
    user = await session.get(User, vendor_id)
    role = await session.get(UserRole, (vendor_id, UserRoleType.VENDOR))
    shop = await session.scalar(select(VendorShop).where(VendorShop.user_id == vendor_id))
    return (
        user is not None
        and user.account_status == AccountStatus.ACTIVE
        and role is not None
        and shop is not None
        and shop.status == 'approved'
    )


async def vendor_role_allowed(session: AsyncSession, user_id: UUID) -> bool:
    """PUT /auth/roles may keep the Vendor role only for an approved (or suspended) shop."""
    shop = await session.scalar(select(VendorShop).where(VendorShop.user_id == user_id))
    return shop is not None and shop.status in ('approved', 'suspended')


async def require_vendor(principal, session: AsyncSession) -> VendorShop:
    """An active account with the Vendor role and an approved shop."""
    if principal.user.account_status != AccountStatus.ACTIVE or not await session.get(
        UserRole, (principal.user.id, UserRoleType.VENDOR)
    ):
        raise ApplicationError('role_required', 'Active account and role required', 403)
    shop = await session.scalar(select(VendorShop).where(VendorShop.user_id == principal.user.id))
    if shop is None or shop.status != 'approved':
        raise ApplicationError('vendor_shop_not_approved', 'The shop is not approved', 403)
    return shop


def shop_notice(shop: VendorShop, kind: str, actor_id: UUID, details: dict) -> UserNotification:
    return UserNotification(
        recipient_id=shop.user_id,
        actor_id=actor_id,
        vendor_shop_id=shop.id,
        kind=kind,
        source_key=f'{kind}:{shop.id}:{uuid4().hex[:12]}',
        details=details,
        created_at=_now(),
    )


class ShopWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=10, max_length=2000)
    city: str = Field(min_length=2, max_length=128)
    delivery_area: str = Field(min_length=2, max_length=500)


class ShopRead(BaseModel):
    id: UUID
    name: str
    description: str
    city: str
    delivery_area: str
    status: ShopStatus
    review_note: str | None
    logo_url: str | None
    identity_verified: bool


class AdminShopRead(ShopRead):
    user_id: UUID
    created_at: datetime
    reviewed_at: datetime | None


class ShopDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['approve', 'reject']
    note: str = Field(min_length=3, max_length=1000)


class ShopSuspension(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reason: str = Field(min_length=3, max_length=1000)


async def _identity_verified(session: AsyncSession, user_id: UUID) -> bool:
    return (
        await session.scalar(
            select(IdentityVerification.id).where(
                IdentityVerification.user_id == user_id,
                IdentityVerification.status == VerificationStatus.VERIFIED,
            )
        )
    ) is not None


async def _logo_url(request: Request, shop: VendorShop) -> str | None:
    if not shop.logo_key:
        return None
    try:
        return await object_storage(request).create_download_url(shop.logo_key)
    except Exception:  # a missing logo never breaks the shop page
        return None


async def shop_read(request: Request, session: AsyncSession, shop: VendorShop, admin=False):
    data = {
        'id': shop.id,
        'name': shop.name,
        'description': shop.description,
        'city': shop.city,
        'delivery_area': shop.delivery_area,
        'status': shop.status,
        'review_note': shop.review_note,
        'logo_url': await _logo_url(request, shop),
        'identity_verified': await _identity_verified(session, shop.user_id),
    }
    if admin:
        return AdminShopRead(
            **data, user_id=shop.user_id, created_at=shop.created_at, reviewed_at=shop.reviewed_at
        )
    return ShopRead(**data)


async def _my_shop(session: AsyncSession, user_id: UUID, *, lock=False) -> VendorShop | None:
    query = select(VendorShop).where(VendorShop.user_id == user_id)
    if lock:
        query = query.with_for_update()
    return await session.scalar(query)


@router.get('/gifts/vendor/shop', response_model=ShopRead)
async def my_shop(request: Request, principal: Principal, session: Session):
    shop = await _my_shop(session, principal.user.id)
    if shop is None:
        raise ApplicationError('vendor_shop_not_found', 'No shop application yet', 404)
    return await shop_read(request, session, shop)


@router.put('/gifts/vendor/shop', response_model=ShopRead)
async def save_shop(payload: ShopWrite, request: Request, principal: Principal, session: Session):
    """Apply (first save) or edit the shop profile. A rejected application goes back to review;
    an approved shop stays approved (an admin can suspend it); a suspended one stays suspended."""
    if principal.user.account_status != AccountStatus.ACTIVE:
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)
    shop = await _my_shop(session, principal.user.id, lock=True)
    fields = {k: v.strip() for k, v in payload.model_dump().items()}
    if shop is None:
        shop = VendorShop(user_id=principal.user.id, status='pending', **fields)
        session.add(shop)
    else:
        for key, value in fields.items():
            setattr(shop, key, value)
        if shop.status == 'rejected':
            shop.status, shop.review_note = 'pending', None
    await session.commit()
    await session.refresh(shop)
    return await shop_read(request, session, shop)


@router.post('/gifts/vendor/shop/logo', response_model=ShopRead)
async def upload_logo(request: Request, principal: Principal, session: Session):
    """Raw JPEG/PNG/WebP bytes, re-encoded to JPEG without EXIF (the photo pipeline)."""
    if principal.user.account_status != AccountStatus.ACTIVE:
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)
    shop = await _my_shop(session, principal.user.id, lock=True)
    if shop is None:
        raise ApplicationError('vendor_shop_not_found', 'No shop application yet', 404)
    settings = request.app.state.settings
    content_type = request.headers.get('content-type', '').split(';')[0].strip()
    if content_type not in IMAGE_TYPES.values():
        raise ApplicationError('invalid_photo_type', 'A JPEG, PNG or WebP image is required', 415)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > settings.companion_photo_max_bytes:
            raise ApplicationError('photo_too_large', 'Photo exceeds the byte limit', 413)
        data.extend(chunk)
    content, _w, _h = await to_thread.run_sync(
        process_image,
        data,
        content_type,
        settings,
        limiter=request.app.state.companion_image_limiter,
    )
    storage = object_storage(request)
    key = f'shops/{shop.id}/{uuid4()}.jpg'

    async def chunks():
        yield content

    try:
        await storage.upload(key, chunks(), 'image/jpeg')
    except asyncio.CancelledError:
        await compensate_upload(storage, key)
        raise
    except Exception as exc:
        await compensate_upload(storage, key)
        raise ApplicationError('storage_unavailable', 'Logo upload failed', 503) from exc
    old, shop.logo_key = shop.logo_key, key
    await session.commit()
    if old:
        await compensate_upload(storage, old)  # best-effort delete of the replaced logo
    await session.refresh(shop)
    return await shop_read(request, session, shop)


@router.get('/admin/vendors', response_model=list[AdminShopRead])
async def admin_shops(
    request: Request,
    admin: Admin,
    session: Session,
    status: ShopStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    query = select(VendorShop).order_by(VendorShop.created_at)
    if status is not None:
        query = query.where(VendorShop.status == status)
    shops = list(await session.scalars(query.limit(limit)))
    return [await shop_read(request, session, shop, admin=True) for shop in shops]


async def _locked_shop(session: AsyncSession, shop_id: UUID) -> VendorShop:
    shop = await session.scalar(
        select(VendorShop).where(VendorShop.id == shop_id).with_for_update()
    )
    if shop is None:
        raise ApplicationError('vendor_shop_not_found', 'Shop not found', 404)
    return shop


@router.post('/admin/vendors/{shop_id}/decision', response_model=AdminShopRead)
async def decide_shop(
    shop_id: UUID, payload: ShopDecision, request: Request, admin: Admin, session: Session
):
    """Approve (also reinstates a suspended shop) or reject, with a note. Approval needs the
    identity verification to be verified and grants the Vendor role."""
    shop = await _locked_shop(session, shop_id)
    if shop.user_id == admin.id:
        raise ApplicationError('self_approval_forbidden', 'Self approval is not permitted', 403)
    approve = payload.decision == 'approve'
    allowed_from = ('pending', 'suspended', 'rejected') if approve else ('pending',)
    if shop.status not in allowed_from:
        raise ApplicationError(
            'vendor_shop_not_pending', 'The shop is not awaiting a decision', 409
        )
    owner = await session.get(User, shop.user_id)
    if approve:
        if owner is None or owner.account_status != AccountStatus.ACTIVE:
            raise ApplicationError('account_unavailable', 'The account is unavailable', 409)
        if not await _identity_verified(session, shop.user_id):
            raise ApplicationError(
                'identity_not_verified', 'The ID and selfie must be verified first', 409
            )
        if await session.get(UserRole, (shop.user_id, UserRoleType.VENDOR)) is None:
            session.add(UserRole(user_id=shop.user_id, role=UserRoleType.VENDOR))
    shop.status = 'approved' if approve else 'rejected'
    shop.review_note = None if approve else payload.note.strip()
    shop.reviewed_by, shop.reviewed_at = admin.id, _now()
    session.add(
        AdminAuditEvent(
            admin_id=admin.id,
            target_id=shop.user_id,
            action='vendor_shop_approved' if approve else 'vendor_shop_rejected',
            reason=payload.note.strip(),
        )
    )
    kind = 'vendor_approved' if approve else 'vendor_rejected'
    session.add(shop_notice(shop, kind, admin.id, {'shop_id': str(shop.id)}))
    await session.commit()
    await session.refresh(shop)
    return await shop_read(request, session, shop, admin=True)


@router.post('/admin/vendors/{shop_id}/suspend', response_model=AdminShopRead)
async def suspend_shop(
    shop_id: UUID, payload: ShopSuspension, request: Request, admin: Admin, session: Session
):
    """Hide the shop's products and stop new orders; existing orders can still be completed."""
    shop = await _locked_shop(session, shop_id)
    if shop.status != 'approved':
        raise ApplicationError(
            'vendor_shop_not_approved', 'Only an approved shop can be suspended', 409
        )
    shop.status, shop.review_note = 'suspended', payload.reason.strip()
    shop.reviewed_by, shop.reviewed_at = admin.id, _now()
    session.add(
        AdminAuditEvent(
            admin_id=admin.id,
            target_id=shop.user_id,
            action='vendor_shop_suspended',
            reason=payload.reason.strip(),
        )
    )
    session.add(shop_notice(shop, 'vendor_suspended', admin.id, {'shop_id': str(shop.id)}))
    await session.commit()
    await session.refresh(shop)
    return await shop_read(request, session, shop, admin=True)
