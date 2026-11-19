"""Vendor inventory controls; real orders and earnings require order/payment contracts."""
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.gifts.models import GiftCartItem, GiftProduct
from yondo_api.gifts.orders_models import GiftTestOrder, GiftTestOrderItem, GiftTestStatus
from yondo_api.gifts.router import Category, ProductRead, require_role
from yondo_api.gifts.test_orders import locked_order, restore_test_stock
from yondo_api.models.user import UserRoleType
from yondo_api.notifications.gifts import enqueue_gift_notice

router = APIRouter(prefix='/vendor', tags=['vendor'])
MAX_MINOR = 9_223_372_036_854_775_807

class ProductPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: Category | None = None
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    price_minor: int | None = Field(default=None, strict=True, ge=0, le=MAX_MINOR)
    currency: str | None = Field(default=None, pattern=r'^[A-Z]{3}$')
    stock: int | None = Field(default=None, strict=True, ge=0, le=2_147_483_647)

@router.patch('/products/{product_id}', response_model=ProductRead)
async def update_product(
    product_id: UUID, payload: ProductPatch, principal: Principal, session: Session
):
    await require_role(principal, session, UserRoleType.VENDOR)
    fields = payload.model_dump(exclude_unset=True)
    if not fields or any(value is None for value in fields.values()):
        raise ApplicationError('invalid_product_update', 'Non-empty product fields required', 422)
    product = await session.scalar(
        select(GiftProduct).where(
            GiftProduct.id == product_id,
            GiftProduct.vendor_id == principal.user.id,
        ).with_for_update()
    )
    if product is None:
        raise ApplicationError('gift_not_found', 'Gift not found', 404)
    for key, value in fields.items():
        if key != 'stock' and getattr(product, key) != value:
            product.published = False  # Public pricing/content needs admin re-approval.
        setattr(product, key, value)
    await session.commit()
    await session.refresh(product)
    return product

@router.post('/products/{product_id}/unpublish', response_model=ProductRead)
async def vendor_unpublish(product_id: UUID, principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.VENDOR)
    product = await session.scalar(select(GiftProduct).where(
        GiftProduct.id == product_id, GiftProduct.vendor_id == principal.user.id
    ).with_for_update())
    if product is None:
        raise ApplicationError('gift_not_found', 'Gift not found', 404)
    product.published = False
    await session.commit()
    await session.refresh(product)
    return product

@router.delete('/products/{product_id}', status_code=204)
async def delete_product(product_id: UUID, principal: Principal, session: Session):
    """Remove an own product that was never ordered; ordered products can only be unpublished."""
    await require_role(principal, session, UserRoleType.VENDOR)
    product = await session.scalar(select(GiftProduct).where(
        GiftProduct.id == product_id, GiftProduct.vendor_id == principal.user.id
    ).with_for_update())
    if product is None:
        raise ApplicationError('gift_not_found', 'Gift not found', 404)
    ordered = await session.scalar(
        select(GiftTestOrderItem.id).where(GiftTestOrderItem.product_id == product_id).limit(1)
    )
    if ordered is not None:
        raise ApplicationError(
            'gift_product_in_use', 'Ordered products cannot be deleted; unpublish instead', 409
        )
    await session.execute(delete(GiftCartItem).where(GiftCartItem.product_id == product_id))
    await session.delete(product)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(
            'gift_product_in_use', 'Ordered products cannot be deleted; unpublish instead', 409
        ) from exc

@router.get('/summary')
async def summary(principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.VENDOR)
    total = await session.scalar(
        select(func.count()).select_from(GiftProduct).where(
            GiftProduct.vendor_id == principal.user.id
        )
    )
    published = await session.scalar(
        select(func.count()).select_from(GiftProduct).where(
            GiftProduct.vendor_id == principal.user.id, GiftProduct.published.is_(True)
        )
    )
    return {
        'products': total or 0, 'published_products': published or 0,
        'orders_available': True, 'earnings_available': False,
    }

class VendorOrderItem(BaseModel):
    product_id: UUID
    name_snapshot: str
    quantity: int
    unit_price_minor: int
    line_total_minor: int


class VendorOrderRead(BaseModel):
    """What a shop sees (CEO, 2026-11-19): the items, the delivery method and the customer's own
    delivery note; never the customer's phone, user id or name ("Mijoz" + a short number)."""

    id: UUID
    short_code: str
    customer_label: Literal['Mijoz'] = 'Mijoz'
    status: GiftTestStatus
    subtotal_minor: int
    currency: str
    delivery_method: str
    delivery_note: str | None
    cancel_reason: str | None
    created_at: datetime
    items: list[VendorOrderItem]
    is_test_order: bool = True
    real_money_moved: bool = False


class VendorStatusWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['preparing', 'out_for_delivery', 'delivered', 'cancelled']
    reason: str | None = Field(default=None, max_length=500)


# The shop moves its own order: paid -> preparing -> out for delivery -> delivered; it may
# cancel (with a reason) until delivered. Test orders: no money, nothing to refund.
VENDOR_TRANSITIONS = {
    GiftTestStatus.TEST_PAID: {'preparing', 'cancelled'},
    GiftTestStatus.AWAITING_TEST_PAYMENT: {'cancelled'},
    GiftTestStatus.PREPARING: {'out_for_delivery', 'cancelled'},
    GiftTestStatus.OUT_FOR_DELIVERY: {'delivered', 'cancelled'},
}
_NOTICE = {
    'preparing': 'gift_preparing',
    'out_for_delivery': 'gift_out_for_delivery',
    'delivered': 'gift_delivered',
    'cancelled': 'gift_cancelled',
}


async def _vendor_order(session, order: GiftTestOrder) -> VendorOrderRead:
    items = list(
        await session.scalars(
            select(GiftTestOrderItem)
            .where(GiftTestOrderItem.order_id == order.id)
            .order_by(GiftTestOrderItem.product_id)
        )
    )
    return VendorOrderRead(
        id=order.id,
        short_code=order.id.hex[:6].upper(),
        status=order.status,
        subtotal_minor=order.subtotal_minor,
        currency=order.currency,
        delivery_method=order.delivery_method,
        delivery_note=order.delivery_note,
        cancel_reason=order.cancel_reason,
        created_at=order.created_at,
        items=[
            VendorOrderItem(
                product_id=row.product_id,
                name_snapshot=row.name_snapshot,
                quantity=row.quantity,
                unit_price_minor=row.unit_price_minor,
                line_total_minor=row.line_total_minor,
            )
            for row in items
        ],
    )


@router.get('/orders', response_model=list[VendorOrderRead])
async def orders(
    principal: Principal,
    session: Session,
    limit: int = Query(default=50, ge=1, le=200),
):
    """The shop's own orders, newest first (a suspended shop can still finish them)."""
    await require_role(principal, session, UserRoleType.VENDOR)
    rows = list(
        await session.scalars(
            select(GiftTestOrder)
            .where(GiftTestOrder.vendor_id == principal.user.id)
            .order_by(GiftTestOrder.created_at.desc())
            .limit(limit)
        )
    )
    return [await _vendor_order(session, order) for order in rows]


@router.post('/orders/{order_id}/status', response_model=VendorOrderRead)
async def vendor_update_status(
    order_id: UUID, payload: VendorStatusWrite, principal: Principal, session: Session
):
    await require_role(principal, session, UserRoleType.VENDOR)
    order = await locked_order(session, order_id)
    if order.vendor_id != principal.user.id:
        raise ApplicationError('gift_test_order_not_found', 'Test order not found', 404)
    if payload.status not in VENDOR_TRANSITIONS.get(order.status, set()):
        raise ApplicationError('gift_test_transition_invalid', 'Invalid order transition', 409)
    reason = (payload.reason or '').strip()
    if payload.status == 'cancelled':
        if len(reason) < 3:
            raise ApplicationError(
                'gift_cancel_reason_required', 'Give the customer a reason', 422
            )
        await restore_test_stock(session, order)
        order.cancel_reason = reason
    order.status = payload.status
    order.status_changed_by = principal.user.id
    if payload.status == 'preparing':
        order.prepared_at = datetime.now(UTC)
    await enqueue_gift_notice(
        session, order, _NOTICE[payload.status], actor_id=principal.user.id
    )
    await session.commit()
    await session.refresh(order)
    return await _vendor_order(session, order)

@router.get('/earnings', status_code=503)
async def earnings(principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.VENDOR)
    raise ApplicationError('vendor_earnings_unavailable', 'Gift payouts not configured', 503)
