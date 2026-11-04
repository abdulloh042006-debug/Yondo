"""Admin management of vendors, products and gift orders (TZ §38: vendors, gifts, orders)."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy import select

from yondo_api.admin.audit import audit
from yondo_api.api.errors import ApplicationError
from yondo_api.core.db import commit
from yondo_api.core.deps import AdminUser, Session
from yondo_api.core.schemas import Input, Page, PageParams, page_of
from yondo_api.core.time import utc_now
from yondo_api.gifts import service
from yondo_api.gifts.models import GiftOrder, GiftOrderStatus, Product, Vendor, VendorStatus
from yondo_api.gifts.schemas import GiftOrderView, VendorProduct, VendorResponse
from yondo_api.notifications.service import notify

router = APIRouter(prefix='/admin', tags=['admin: gifts'])
Params = Annotated[PageParams, Depends()]


class VendorDecision(Input):
    decision: Literal['approve', 'reject', 'suspend']
    note: str = Field(min_length=1, max_length=2000)


class ProductModeration(Input):
    action: Literal['hide', 'unhide']
    reason: str = Field(default='', max_length=2000)


class OrderCancel(Input):
    reason: str = Field(min_length=1, max_length=500)
    refund: bool = True


@router.get('/vendors', response_model=Page[VendorResponse])
async def vendors(
    admin: AdminUser, session: Session, params: Params, status: VendorStatus | None = None
):
    query = select(Vendor)
    if status:
        query = query.where(Vendor.status == status)
    rows = list(
        await session.scalars(
            query.order_by(Vendor.created_at, Vendor.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    return page_of([VendorResponse.model_validate(v) for v in rows], params)


@router.post('/vendors/{vendor_id}/decision', response_model=VendorResponse)
async def decide_vendor(
    vendor_id: UUID, payload: VendorDecision, admin: AdminUser, session: Session
):
    vendor = await session.scalar(select(Vendor).where(Vendor.id == vendor_id).with_for_update())
    if vendor is None:
        raise ApplicationError('vendor_not_found', 'Vendor not found', 404)
    if vendor.user_id == admin.id:
        raise ApplicationError('self_approval_forbidden', 'Self approval is not permitted', 403)
    vendor.status = {
        'approve': VendorStatus.APPROVED,
        'reject': VendorStatus.REJECTED,
        'suspend': VendorStatus.SUSPENDED,
    }[payload.decision]
    vendor.review_note = payload.note
    vendor.reviewed_by = admin.id
    vendor.reviewed_at = utc_now()
    notify(
        session,
        vendor.user_id,
        'vendor_decision',
        'Do‘koningiz tasdiqlandi' if payload.decision == 'approve' else 'Vendor holati o‘zgardi',
        payload.note[:200],
    )
    audit(session, admin, f'vendor.{payload.decision}', 'vendor', vendor.id, payload.note)
    await commit(session)
    return vendor


@router.get('/products', response_model=Page[VendorProduct])
async def products(
    request: Request,
    admin: AdminUser,
    session: Session,
    params: Params,
    vendor_id: UUID | None = None,
    hidden: bool | None = None,
):
    query = select(Product)
    if vendor_id:
        query = query.where(Product.vendor_id == vendor_id)
    if hidden is not None:
        query = query.where(Product.hidden_by_admin.is_(hidden))
    rows = list(
        await session.scalars(
            query.order_by(Product.created_at.desc(), Product.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    images = await service.image_views(request, session, [p.id for p in rows])
    views = []
    for product in rows:
        view = VendorProduct.model_validate(product)
        view.images = images.get(product.id, [])
        views.append(view)
    return page_of(views, params)


@router.post('/products/{product_id}/moderation', response_model=VendorProduct)
async def moderate_product(
    product_id: UUID, payload: ProductModeration, admin: AdminUser, session: Session
):
    product = await session.get(Product, product_id)
    if product is None:
        raise ApplicationError('product_not_found', 'Product not found', 404)
    product.hidden_by_admin = payload.action == 'hide'
    product.hidden_reason = payload.reason if payload.action == 'hide' else None
    audit(session, admin, f'product.{payload.action}', 'product', product.id, payload.reason)
    await commit(session)
    return VendorProduct.model_validate(product)


@router.get('/gift-orders', response_model=Page[GiftOrderView])
async def gift_orders(
    admin: AdminUser, session: Session, params: Params, status: GiftOrderStatus | None = None
):
    query = select(GiftOrder)
    if status:
        query = query.where(GiftOrder.status == status)
    rows = list(
        await session.scalars(
            query.order_by(GiftOrder.created_at.desc(), GiftOrder.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    page = page_of(rows, params)
    return Page[GiftOrderView](
        items=await service.order_views(session, page.items), next_offset=page.next_offset
    )


@router.post('/gift-orders/{order_id}/cancel', response_model=GiftOrderView)
async def cancel_gift_order(
    order_id: UUID, payload: OrderCancel, request: Request, admin: AdminUser, session: Session
):
    from yondo_api.payments.service import process_refunds

    order = await session.scalar(
        select(GiftOrder).where(GiftOrder.id == order_id).with_for_update()
    )
    if order is None:
        raise ApplicationError('gift_order_not_found', 'Order not found', 404)
    await service.cancel_order(session, order, 'admin_cancelled', refund=payload.refund)
    audit(
        session,
        admin,
        'gift_order.cancel',
        'gift_order',
        order.id,
        payload.reason,
        {'refund': payload.refund},
    )
    await commit(session)
    await process_refunds(session, request.app.state)
    return (await service.order_views(session, [order]))[0]
