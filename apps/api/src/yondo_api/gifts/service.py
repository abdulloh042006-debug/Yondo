from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.phone import normalize_uzbekistan_phone
from yondo_api.config import Settings
from yondo_api.core.images import signed_url
from yondo_api.core.money import apply_bps
from yondo_api.core.time import as_utc, utc_now
from yondo_api.gifts.models import (
    NEXT_STATUS,
    REFUNDABLE_ON_CANCEL,
    FavoriteProduct,
    GiftOrder,
    GiftOrderItem,
    GiftOrderStatus,
    GiftReview,
    Product,
    ProductImage,
    Vendor,
    VendorStatus,
)
from yondo_api.gifts.schemas import GiftLine, GiftOrderView, ImageView, OrderItemView, ProductCard
from yondo_api.models.user import AccountStatus, User
from yondo_api.notifications.service import notify

IMAGE_URL_SECONDS = 3600


def visible_conditions():
    """Products customers may see and buy."""
    return and_(
        Product.vendor_id == Vendor.id,
        Product.is_active.is_(True),
        Product.hidden_by_admin.is_(False),
        Vendor.status == VendorStatus.APPROVED,
        Vendor.user_id == User.id,
        User.account_status == AccountStatus.ACTIVE,
    )


def visible_query():
    return (
        select(Product, Vendor)
        .join(Vendor, Vendor.id == Product.vendor_id)
        .join(User, User.id == Vendor.user_id)
        .where(visible_conditions())
    )


def delivery_minutes(product: Product, vendor: Vendor) -> int:
    return product.delivery_time_minutes or vendor.delivery_time_minutes


async def image_views(request: Request, session: AsyncSession, product_ids: list[UUID]):
    result: dict[UUID, list[ImageView]] = {}
    if not product_ids:
        return result
    for image in await session.scalars(
        select(ProductImage)
        .where(ProductImage.product_id.in_(product_ids))
        .order_by(ProductImage.product_id, ProductImage.position)
    ):
        result.setdefault(image.product_id, []).append(
            ImageView(
                id=image.id,
                url=await signed_url(request, image.storage_key, IMAGE_URL_SECONDS),
                width=image.width,
                height=image.height,
            )
        )
    return result


async def product_ratings(
    session: AsyncSession, product_ids: list[UUID]
) -> dict[UUID, tuple[float, int]]:
    if not product_ids:
        return {}
    rows = await session.execute(
        select(GiftOrderItem.product_id, func.avg(GiftReview.rating), func.count())
        .join(GiftReview, GiftReview.order_id == GiftOrderItem.order_id)
        .where(GiftOrderItem.product_id.in_(product_ids))
        .group_by(GiftOrderItem.product_id)
    )
    return {pid: (round(float(avg), 2), count) for pid, avg, count in rows}


async def product_cards(
    request: Request,
    session: AsyncSession,
    viewer: User,
    rows: list[tuple[Product, Vendor]],
) -> list[ProductCard]:
    ids = [product.id for product, _ in rows]
    images = await image_views(request, session, ids)
    ratings = await product_ratings(session, ids)
    favorites = set(
        await session.scalars(
            select(FavoriteProduct.product_id).where(FavoriteProduct.user_id == viewer.id)
        )
    )
    return [
        ProductCard(
            id=product.id,
            category=product.category,
            name=product.name,
            price_minor=product.price_minor,
            currency=product.currency,
            vendor_id=vendor.id,
            vendor_name=vendor.name,
            image=(images.get(product.id) or [None])[0],
            rating_average=ratings.get(product.id, (None, 0))[0],
            rating_count=ratings.get(product.id, (None, 0))[1],
            delivery_time_minutes=delivery_minutes(product, vendor),
            in_stock=product.stock > 0,
            is_favorite=product.id in favorites,
        )
        for product, vendor in rows
    ]


async def order_views(session: AsyncSession, orders: list[GiftOrder]) -> list[GiftOrderView]:
    ids = [order.id for order in orders]
    items: dict[UUID, list[OrderItemView]] = {}
    if ids:
        for item in await session.scalars(
            select(GiftOrderItem).where(GiftOrderItem.order_id.in_(ids))
        ):
            items.setdefault(item.order_id, []).append(OrderItemView.model_validate(item))
    vendors = (
        dict(
            (
                await session.execute(
                    select(Vendor.id, Vendor.name).where(
                        Vendor.id.in_({order.vendor_id for order in orders})
                    )
                )
            ).all()
        )
        if orders
        else {}
    )
    views = []
    for order in orders:
        view = GiftOrderView.model_validate(order)
        view.items = items.get(order.id, [])
        view.vendor_name = vendors.get(order.vendor_id)
        views.append(view)
    return views


async def build_orders(
    session: AsyncSession,
    settings: Settings,
    customer: User,
    lines: list[GiftLine],
    *,
    recipient_name: str,
    recipient_phone: str,
    address: str,
    latitude: float | None,
    longitude: float | None,
    delivery_at: datetime,
    note: str,
    booking_id: UUID | None = None,
    currency: str | None = None,
) -> list[GiftOrder]:
    """Validate lines, reserve stock and create one pending order per vendor."""
    merged: dict[UUID, GiftLine] = {}
    for line in lines:
        if line.product_id in merged:
            raise ApplicationError('duplicate_product', 'Each product may appear once', 422)
        merged[line.product_id] = line
    rows = list(
        await session.execute(
            visible_query()
            .where(Product.id.in_(list(merged)))
            .with_for_update(of=Product)
            .execution_options(populate_existing=True)
        )
    )
    if len(rows) != len(merged):
        raise ApplicationError('product_unavailable', 'A product is no longer available', 409)
    by_vendor: dict[UUID, list[tuple[Product, Vendor, GiftLine]]] = {}
    for product, vendor in rows:
        line = merged[product.id]
        if product.stock < line.quantity:
            raise ApplicationError(
                'insufficient_stock', f'Not enough stock for {product.name}', 409
            )
        if currency is not None and product.currency != currency:
            raise ApplicationError('currency_mismatch', 'All items must share one currency', 422)
        currency = product.currency
        if as_utc(delivery_at) < utc_now() + timedelta(minutes=delivery_minutes(product, vendor)):
            raise ApplicationError(
                'delivery_too_soon', f'{product.name} cannot be delivered that soon', 422
            )
        by_vendor.setdefault(vendor.id, []).append((product, vendor, line))
    phone = normalize_uzbekistan_phone(recipient_phone)
    orders = []
    for vendor_lines in by_vendor.values():
        vendor = vendor_lines[0][1]
        subtotal = sum(product.price_minor * line.quantity for product, _, line in vendor_lines)
        fee = apply_bps(subtotal, settings.gift_platform_fee_bps)
        order = GiftOrder(
            customer_id=customer.id,
            vendor_id=vendor.id,
            booking_id=booking_id,
            status=GiftOrderStatus.PENDING_PAYMENT,
            recipient_name=recipient_name,
            recipient_phone=phone,
            delivery_address=address,
            delivery_latitude=latitude,
            delivery_longitude=longitude,
            delivery_at=as_utc(delivery_at),
            note=note,
            currency=currency,
            subtotal_minor=subtotal,
            delivery_fee_minor=vendor.delivery_fee_minor,
            platform_fee_minor=fee,
            total_minor=subtotal + vendor.delivery_fee_minor + fee,
        )
        session.add(order)
        await session.flush()
        for product, _, line in vendor_lines:
            product.stock -= line.quantity
            session.add(
                GiftOrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    unit_price_minor=product.price_minor,
                    quantity=line.quantity,
                    note=line.note,
                )
            )
        orders.append(order)
    return orders


def gift_breakdown(orders: Iterable[GiftOrder], breakdown: dict[str, Any]) -> int:
    orders = list(orders)
    breakdown['gifts_subtotal_minor'] = sum(o.subtotal_minor for o in orders)
    breakdown['delivery_fee_minor'] = sum(o.delivery_fee_minor for o in orders)
    breakdown['gift_platform_fee_minor'] = sum(o.platform_fee_minor for o in orders)
    breakdown['gift_order_ids'] = [str(o.id) for o in orders]
    return sum(o.total_minor for o in orders)


async def orders_for_payment(session: AsyncSession, payment_id: UUID) -> list[GiftOrder]:
    return list(
        await session.scalars(
            select(GiftOrder)
            .where(GiftOrder.payment_id == payment_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )


async def restore_stock(session: AsyncSession, order: GiftOrder) -> None:
    for item in await session.scalars(
        select(GiftOrderItem).where(GiftOrderItem.order_id == order.id)
    ):
        if item.product_id is None:
            continue
        product = await session.scalar(
            select(Product).where(Product.id == item.product_id).with_for_update()
        )
        if product is not None:
            product.stock += item.quantity


def vendor_payout_amount(order: GiftOrder, settings_bps: int) -> int:
    return (
        order.subtotal_minor
        + order.delivery_fee_minor
        - apply_bps(order.subtotal_minor, settings_bps)
    )


async def _activate(session: AsyncSession, order: GiftOrder, settings_bps: int) -> None:
    from yondo_api.payments.models import Payout, PayoutStatus

    order.status = GiftOrderStatus.NEW
    vendor = await session.get(Vendor, order.vendor_id)
    session.add(
        Payout(
            beneficiary_id=vendor.user_id,
            gift_order_id=order.id,
            amount_minor=vendor_payout_amount(order, settings_bps),
            currency=order.currency,
            status=PayoutStatus.HELD,
        )
    )
    notify(
        session,
        vendor.user_id,
        'gift_order_new',
        'Yangi buyurtma',
        f'Yangi buyurtma: {order.total_minor} {order.currency}.',
        {'gift_order_id': order.id},
    )


async def confirm_payment_orders(session: AsyncSession, payment, settings_bps: int) -> bool:
    """Activate pending orders paid by ``payment``. Returns False if any was released."""
    orders = await orders_for_payment(session, payment.id)
    if any(order.status != GiftOrderStatus.PENDING_PAYMENT for order in orders):
        return False
    for order in orders:
        await _activate(session, order, settings_bps)
    return True


async def release_unpaid_orders(session: AsyncSession, payment, reason: str) -> None:
    for order in await orders_for_payment(session, payment.id):
        if order.status == GiftOrderStatus.PENDING_PAYMENT:
            order.status = GiftOrderStatus.CANCELLED
            order.cancelled_reason = reason
            await restore_stock(session, order)


async def cancel_order(
    session: AsyncSession, order: GiftOrder, reason: str, *, refund: bool
) -> None:
    from yondo_api.payments.models import Payment, Payout, PayoutStatus
    from yondo_api.payments.service import queue_refund

    if order.status in {GiftOrderStatus.CANCELLED, GiftOrderStatus.DELIVERED}:
        raise ApplicationError('gift_order_closed', 'This order can no longer be cancelled', 409)
    was_paid = order.status != GiftOrderStatus.PENDING_PAYMENT
    order.status = GiftOrderStatus.CANCELLED
    order.cancelled_reason = reason
    await restore_stock(session, order)
    payout = await session.scalar(
        select(Payout).where(Payout.gift_order_id == order.id).with_for_update()
    )
    if payout is not None and payout.status != PayoutStatus.PAID:
        payout.status = PayoutStatus.CANCELLED
        payout.amount_minor = 0
    if refund and was_paid and order.payment_id is not None:
        payment = await session.scalar(
            select(Payment).where(Payment.id == order.payment_id).with_for_update()
        )
        queue_refund(session, payment, order.total_minor, f'gift_{reason}')
    notify(
        session,
        order.customer_id,
        'gift_order_cancelled',
        'Buyurtma bekor qilindi',
        "Sovg'a buyurtmasi bekor qilindi.",
        {'gift_order_id': order.id},
    )


async def cancel_booking_orders(session: AsyncSession, booking_id: UUID) -> None:
    """Booking cancelled: refund gift orders vendors have not started preparing."""
    orders = await session.scalars(
        select(GiftOrder).where(
            GiftOrder.booking_id == booking_id, GiftOrder.status.in_(REFUNDABLE_ON_CANCEL)
        )
    )
    for order in list(orders):
        await cancel_order(session, order, 'booking_cancelled', refund=True)


async def advance(
    session: AsyncSession, settings: Settings, vendor: Vendor, order_id: UUID, target: str
) -> GiftOrder:
    from yondo_api.payments.models import Payout, PayoutStatus

    order = await session.scalar(
        select(GiftOrder)
        .where(GiftOrder.id == order_id, GiftOrder.vendor_id == vendor.id)
        .with_for_update()
    )
    if order is None or order.status == GiftOrderStatus.PENDING_PAYMENT:
        raise ApplicationError('gift_order_not_found', 'Order not found', 404)
    if target == GiftOrderStatus.CANCELLED:
        if order.status not in REFUNDABLE_ON_CANCEL:
            raise ApplicationError('gift_order_in_progress', 'Order is already in progress', 409)
        await cancel_order(session, order, 'vendor_cancelled', refund=True)
        return order
    if NEXT_STATUS.get(GiftOrderStatus(order.status)) != target:
        raise ApplicationError(
            'invalid_gift_transition', f'Cannot move from {order.status} to {target}', 409
        )
    order.status = target
    titles = {
        GiftOrderStatus.ACCEPTED: 'Buyurtma qabul qilindi',
        GiftOrderStatus.PREPARING: 'Buyurtma tayyorlanmoqda',
        GiftOrderStatus.COURIER_ASSIGNED: 'Kuryer tayinlandi',
        GiftOrderStatus.DELIVERING: 'Buyurtma yo‘lda',
        GiftOrderStatus.DELIVERED: 'Buyurtma yetkazildi',
    }
    if target == GiftOrderStatus.DELIVERED:
        order.delivered_at = utc_now()
        payout = await session.scalar(
            select(Payout).where(Payout.gift_order_id == order.id).with_for_update()
        )
        if payout is not None and payout.status == PayoutStatus.HELD:
            payout.status = PayoutStatus.SCHEDULED
            payout.available_at = utc_now() + timedelta(hours=settings.payout_release_delay_hours)
    notify(
        session,
        order.customer_id,
        'gift_order_status',
        titles[GiftOrderStatus(target)],
        '',
        {'gift_order_id': order.id, 'status': target},
    )
    return order
