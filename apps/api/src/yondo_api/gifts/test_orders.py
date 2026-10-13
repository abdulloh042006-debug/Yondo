"""Self-fulfilled gift orders for local CLICK test mode; no real checkout."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Admin, Principal, Session
from yondo_api.config import Settings
from yondo_api.gifts.models import GiftCartItem, GiftProduct
from yondo_api.gifts.orders_models import GiftTestOrder, GiftTestOrderItem, GiftTestStatus
from yondo_api.gifts.router import require_role
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType
from yondo_api.notifications.gifts import enqueue_gift_notice

router = APIRouter(tags=['manual gift test orders'])
MAX_MINOR = 9_223_372_036_854_775_807
MAX_STOCK = 2_147_483_647


class TestOrderWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    delivery_method: Literal['pickup', 'manual_delivery']
    delivery_note: str | None = Field(default=None, max_length=512)


class OperatorStatusWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['preparing', 'out_for_delivery', 'delivered', 'cancelled']


class TestOrderItemRead(BaseModel):
    product_id: UUID
    name_snapshot: str
    quantity: int
    unit_price_minor: int
    line_total_minor: int


class TestOrderRead(BaseModel):
    id: UUID
    customer_id: UUID
    status: GiftTestStatus
    subtotal_minor: int
    currency: str
    delivery_method: str
    delivery_note: str | None
    click_test_trans_id: int | None
    created_at: datetime
    items: list[TestOrderItemRead]
    is_test_order: bool = True
    real_money_moved: bool = False
    operator_fulfillment: bool = True
    delivery_fee_minor: None = None
    payable_total_minor: None = None


def ensure_test_enabled(settings: Settings) -> None:
    if (
        settings.environment not in {'development', 'test'}
        or not settings.click_test_enabled
        or settings.click_test_service_id is None
        or len(settings.click_test_secret.get_secret_value()) < 32
    ):
        raise ApplicationError('click_test_disabled', 'Offline payment testing is disabled', 404)


async def locked_order(session: Session, order_id: UUID) -> GiftTestOrder:
    order = await session.scalar(
        select(GiftTestOrder).where(GiftTestOrder.id == order_id)
        .with_for_update().execution_options(populate_existing=True)
    )
    if order is None:
        raise ApplicationError('gift_test_order_not_found', 'Test order not found', 404)
    return order


async def order_payload(session: Session, order: GiftTestOrder) -> dict:
    items = list(
        await session.scalars(
            select(GiftTestOrderItem).where(GiftTestOrderItem.order_id == order.id)
            .order_by(GiftTestOrderItem.product_id)
        )
    )
    return {
        'id': order.id,
        'customer_id': order.customer_id,
        'status': order.status,
        'subtotal_minor': order.subtotal_minor,
        'currency': order.currency,
        'delivery_method': order.delivery_method,
        'delivery_note': order.delivery_note,
        'click_test_trans_id': order.click_trans_id,
        'created_at': order.created_at,
        'items': [
            {
                'product_id': row.product_id,
                'name_snapshot': row.name_snapshot,
                'quantity': row.quantity,
                'unit_price_minor': row.unit_price_minor,
                'line_total_minor': row.line_total_minor,
            }
            for row in items
        ],
        'is_test_order': True,
        'real_money_moved': False,
        'operator_fulfillment': True,
        'delivery_fee_minor': None,
        'payable_total_minor': None,
    }


async def restore_test_stock(session: Session, order: GiftTestOrder) -> None:
    items = list(
        await session.scalars(
            select(GiftTestOrderItem).where(GiftTestOrderItem.order_id == order.id)
            .order_by(GiftTestOrderItem.product_id)
        )
    )
    for item in items:
        product = await session.scalar(
            select(GiftProduct).where(GiftProduct.id == item.product_id).with_for_update()
        )
        if product is None or product.stock + item.quantity > MAX_STOCK:
            raise ApplicationError(
                'gift_test_stock_restore_conflict',
                'Operator must reconcile stock before cancelling', 409,
            )
        product.stock += item.quantity


@router.post('/gifts/test-orders', response_model=TestOrderRead, status_code=201)
async def create_test_order(
    payload: TestOrderWrite, request: Request, principal: Principal, session: Session
):
    ensure_test_enabled(request.app.state.settings)
    await require_role(principal, session, UserRoleType.CUSTOMER)
    if payload.delivery_method == 'manual_delivery' and not (
        payload.delivery_note and payload.delivery_note.strip()
    ):
        raise ApplicationError(
            'gift_delivery_note_required',
            'Provide a private delivery coordination note', 422,
        )
    # Serialize repeated checkout requests from the same customer before loading the cart.
    # PostgreSQL FOR UPDATE prevents two simultaneous orders using the same cart rows.
    locked_customer = await session.scalar(
        select(User).where(User.id == principal.user.id).with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked_customer is None or locked_customer.account_status != AccountStatus.ACTIVE:
        raise ApplicationError('account_unavailable', 'Customer account unavailable', 403)
    cart = list(
        await session.scalars(
            select(GiftCartItem).where(GiftCartItem.customer_id == principal.user.id)
            .order_by(GiftCartItem.product_id)
        )
    )
    if not cart:
        raise ApplicationError('cart_empty', 'Cart has no items', 409)
    lines = []
    subtotal = 0
    for cart_item in cart:
        product = await session.scalar(
            select(GiftProduct).where(GiftProduct.id == cart_item.product_id).with_for_update()
        )
        if product is None or product.stock < cart_item.quantity or not product.published:
            raise ApplicationError('gift_unavailable', 'Cart product unavailable', 409)
        vendor = await session.get(User, product.vendor_id)
        role = await session.get(UserRole, (product.vendor_id, UserRoleType.VENDOR))
        if vendor is None or vendor.account_status != AccountStatus.ACTIVE or role is None:
            raise ApplicationError('gift_unavailable', 'Vendor unavailable', 409)
        if product.currency != 'UZS':
            raise ApplicationError(
                'click_test_currency_unsupported', 'CLICK test orders use UZS only', 409
            )
        line = product.price_minor * cart_item.quantity
        if line > MAX_MINOR or subtotal + line > MAX_MINOR:
            raise ApplicationError('gift_total_overflow', 'Gift subtotal is too large', 422)
        subtotal += line
        lines.append((cart_item, product, line))
    if subtotal <= 0:
        raise ApplicationError('gift_test_amount_invalid', 'Test amount must be positive', 422)
    order = GiftTestOrder(
        customer_id=principal.user.id,
        subtotal_minor=subtotal,
        currency='UZS',
        delivery_method=payload.delivery_method,
        delivery_note=(payload.delivery_note.strip() if payload.delivery_note else None),
        status=GiftTestStatus.AWAITING_TEST_PAYMENT,
    )
    session.add(order)
    await session.flush()
    for cart_item, product, amount in lines:
        product.stock -= cart_item.quantity
        session.add(
            GiftTestOrderItem(
                order_id=order.id,
                product_id=product.id,
                name_snapshot=product.name,
                quantity=cart_item.quantity,
                unit_price_minor=product.price_minor,
                line_total_minor=amount,
            )
        )
        await session.delete(cart_item)
    await enqueue_gift_notice(
        session, order, 'gift_order_created', actor_id=principal.user.id
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError('gift_test_order_conflict', 'Order changed; retry', 409) from exc
    await session.refresh(order)
    return await order_payload(session, order)


@router.get('/gifts/test-orders', response_model=list[TestOrderRead])
async def my_test_orders(
    request: Request, principal: Principal, session: Session,
    limit: int = Query(default=30, ge=1, le=100),
):
    ensure_test_enabled(request.app.state.settings)
    await require_role(principal, session, UserRoleType.CUSTOMER)
    records = list(
        await session.scalars(
            select(GiftTestOrder).where(GiftTestOrder.customer_id == principal.user.id)
            .order_by(GiftTestOrder.created_at.desc(), GiftTestOrder.id).limit(limit)
        )
    )
    return [await order_payload(session, record) for record in records]


@router.get('/gifts/test-orders/{order_id}', response_model=TestOrderRead)
async def my_test_order(
    order_id: UUID, request: Request, principal: Principal, session: Session
):
    ensure_test_enabled(request.app.state.settings)
    await require_role(principal, session, UserRoleType.CUSTOMER)
    order = await session.scalar(
        select(GiftTestOrder).where(
            GiftTestOrder.id == order_id,
            GiftTestOrder.customer_id == principal.user.id,
        )
    )
    if order is None:
        raise ApplicationError('gift_test_order_not_found', 'Test order not found', 404)
    return await order_payload(session, order)


@router.get('/admin/gifts/test-orders', response_model=list[TestOrderRead])
async def operator_test_orders(
    request: Request, admin: Admin, session: Session,
    limit: int = Query(default=50, ge=1, le=100),
):
    ensure_test_enabled(request.app.state.settings)
    records = list(
        await session.scalars(
            select(GiftTestOrder).order_by(
                GiftTestOrder.created_at.desc(), GiftTestOrder.id
            ).limit(limit)
        )
    )
    return [await order_payload(session, record) for record in records]


@router.post('/admin/gifts/test-orders/{order_id}/status', response_model=TestOrderRead)
async def operator_update_test_status(
    order_id: UUID, payload: OperatorStatusWrite,
    request: Request, admin: Admin, session: Session
):
    ensure_test_enabled(request.app.state.settings)
    order = await locked_order(session, order_id)
    transitions = {
        GiftTestStatus.TEST_PAID: {'preparing', 'cancelled'},
        GiftTestStatus.PREPARING: {'out_for_delivery', 'cancelled'},
        GiftTestStatus.OUT_FOR_DELIVERY: {'delivered'},
        GiftTestStatus.AWAITING_TEST_PAYMENT: {'cancelled'},
    }
    if payload.status not in transitions.get(order.status, set()):
        raise ApplicationError('gift_test_transition_invalid', 'Invalid order transition', 409)
    if payload.status == 'cancelled':
        await restore_test_stock(session, order)
    order.status = payload.status
    order.status_changed_by = admin.id
    await enqueue_gift_notice(
        session, order, f'gift_{payload.status}', actor_id=admin.id
    )
    await session.commit()
    await session.refresh(order)
    return await order_payload(session, order)
