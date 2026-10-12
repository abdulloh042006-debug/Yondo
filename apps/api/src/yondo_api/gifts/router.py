from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.gifts.models import GiftCartItem, GiftProduct
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType

router = APIRouter(prefix='/gifts', tags=['gifts'])
Category = Literal['flowers', 'chocolate', 'gift_box', 'toys', 'birthday', 'romantic', 'custom']


class ProductWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: Category
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=1, max_length=4000)
    price_minor: int = Field(strict=True, ge=0, le=9_223_372_036_854_775_807)
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    stock: int = Field(strict=True, ge=0, le=2_147_483_647)


class ProductRead(ProductWrite):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    vendor_id: UUID
    published: bool


class CartWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    quantity: int = Field(strict=True, ge=1, le=100)


class CartRead(CartWrite):
    model_config = ConfigDict(from_attributes=True)
    product_id: UUID


async def require_role(principal: Principal, session: Session, role: UserRoleType):
    if principal.user.account_status != AccountStatus.ACTIVE or not await session.get(
        UserRole, (principal.user.id, role)
    ):
        raise ApplicationError('role_required', 'Active account and role required', 403)


@router.get('/products', response_model=list[ProductRead])
async def list_products(
    session: Session,
    category: Category | None = None,
    limit: int = Query(default=30, ge=1, le=100),
):
    q = (
        select(GiftProduct)
        .join(User, User.id == GiftProduct.vendor_id)
        .where(
            GiftProduct.published.is_(True),
            GiftProduct.stock > 0,
            User.account_status == AccountStatus.ACTIVE,
            exists(
                select(UserRole.user_id).where(
                    UserRole.user_id == GiftProduct.vendor_id,
                    UserRole.role == UserRoleType.VENDOR,
                )
            ),
        )
    )
    if category is not None:
        q = q.where(GiftProduct.category == category)
    return list(await session.scalars(q.order_by(GiftProduct.created_at.desc()).limit(limit)))


@router.get('/products/{product_id}', response_model=ProductRead)
async def product_detail(product_id: UUID, session: Session):
    item = await session.get(GiftProduct, product_id)
    if item is None or not item.published:
        raise ApplicationError('gift_not_found', 'Gift not found', 404)
    vendor = await session.get(User, item.vendor_id)
    role = await session.get(UserRole, (item.vendor_id, UserRoleType.VENDOR))
    if vendor is None or vendor.account_status != AccountStatus.ACTIVE or role is None:
        raise ApplicationError('gift_not_found', 'Gift not found', 404)
    return item


@router.post('/vendor/products', response_model=ProductRead, status_code=201)
async def create_product(payload: ProductWrite, principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.VENDOR)
    item = GiftProduct(vendor_id=principal.user.id, published=False, **payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get('/vendor/products', response_model=list[ProductRead])
async def vendor_products(principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.VENDOR)
    return list(
        await session.scalars(select(GiftProduct).where(GiftProduct.vendor_id == principal.user.id))
    )


@router.put('/cart/{product_id}', response_model=CartRead)
async def add_to_cart(product_id: UUID, payload: CartWrite, principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.CUSTOMER)
    item = await session.get(GiftProduct, product_id)
    if item is None or not item.published or item.stock < payload.quantity:
        raise ApplicationError('gift_unavailable', 'Gift is unavailable', 409)
    vendor = await session.get(User, item.vendor_id)
    role = await session.get(UserRole, (item.vendor_id, UserRoleType.VENDOR))
    if vendor is None or vendor.account_status != AccountStatus.ACTIVE or role is None:
        raise ApplicationError('gift_unavailable', 'Gift is unavailable', 409)
    existing = await session.scalar(
        select(GiftCartItem).where(
            GiftCartItem.customer_id == principal.user.id,
            GiftCartItem.product_id == product_id,
        )
    )
    if existing is None:
        existing = GiftCartItem(
            customer_id=principal.user.id, product_id=product_id, quantity=payload.quantity
        )
        session.add(existing)
    else:
        existing.quantity = payload.quantity
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError('cart_conflict', 'Cart changed; retry request', 409) from exc
    return existing


@router.get('/cart', response_model=list[CartRead])
async def cart(principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.CUSTOMER)
    return list(
        await session.scalars(
            select(GiftCartItem).where(GiftCartItem.customer_id == principal.user.id)
        )
    )


@router.delete('/cart/{product_id}', status_code=204)
async def remove_from_cart(product_id: UUID, principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.CUSTOMER)
    existing = await session.scalar(
        select(GiftCartItem).where(
            GiftCartItem.customer_id == principal.user.id, GiftCartItem.product_id == product_id
        )
    )
    if existing is not None:
        await session.delete(existing)
        await session.commit()


@router.get('/checkout/preview')
async def preview_checkout(principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.CUSTOMER)
    rows = (
        await session.execute(
            select(GiftCartItem, GiftProduct)
            .join(GiftProduct, GiftProduct.id == GiftCartItem.product_id)
            .where(GiftCartItem.customer_id == principal.user.id)
        )
    ).all()
    if not rows:
        raise ApplicationError('cart_empty', 'Cart has no items', 409)
    currency = rows[0][1].currency
    subtotal = 0
    items = []
    for entry, product in rows:
        vendor = await session.get(User, product.vendor_id)
        role = await session.get(UserRole, (product.vendor_id, UserRoleType.VENDOR))
        if (
            role is None
            or product.currency != currency
            or not product.published
            or product.stock < entry.quantity
            or vendor is None
            or vendor.account_status != AccountStatus.ACTIVE
        ):
            raise ApplicationError('gift_unavailable', 'Cart contains unavailable items', 409)
        line_total = product.price_minor * entry.quantity
        subtotal += line_total
        if subtotal > 9_223_372_036_854_775_807:
            raise ApplicationError('gift_total_overflow', 'Cart subtotal too large', 422)
        items.append(
            {
                'product_id': str(product.id),
                'quantity': entry.quantity,
                'price_minor': product.price_minor,
                'line_subtotal_minor': line_total,
            }
        )
    return {
        'items': items,
        'currency': currency,
        'subtotal_minor': subtotal,
        'delivery_fee_minor': None,
        'checkout_available': False,
    }


@router.post('/checkout', status_code=503)
async def checkout(principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.CUSTOMER)
    # No gift-specific provider/order/fulfilment contract has been approved.
    raise ApplicationError(
        'gift_checkout_unavailable',
        'Gift payment and fulfilment are not configured',
        503,
    )


@router.post('/admin/products/{product_id}/publish', response_model=ProductRead)
async def publish_product(product_id: UUID, principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.ADMIN)
    product = await session.scalar(
        select(GiftProduct).where(GiftProduct.id == product_id).with_for_update()
    )
    if product is None:
        raise ApplicationError('gift_not_found', 'Gift not found', 404)
    vendor = await session.get(User, product.vendor_id)
    role = await session.get(UserRole, (product.vendor_id, UserRoleType.VENDOR))
    if vendor is None or vendor.account_status != AccountStatus.ACTIVE or role is None:
        raise ApplicationError('gift_vendor_unavailable', 'Vendor is unavailable', 409)
    if product.stock < 1:
        raise ApplicationError('gift_unavailable', 'Product is out of stock', 409)
    product.published = True
    await session.commit()
    await session.refresh(product)
    return product


@router.post('/admin/products/{product_id}/unpublish', response_model=ProductRead)
async def unpublish_product(product_id: UUID, principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.ADMIN)
    product = await session.scalar(
        select(GiftProduct).where(GiftProduct.id == product_id).with_for_update()
    )
    if product is None:
        raise ApplicationError('gift_not_found', 'Gift not found', 404)
    product.published = False
    await session.commit()
    await session.refresh(product)
    return product
