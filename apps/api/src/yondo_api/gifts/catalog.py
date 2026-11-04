"""Customer side of the gifts marketplace: catalog, product page, favorites, cart, orders."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import delete, func, or_, select

from yondo_api.api.errors import ApplicationError
from yondo_api.core.db import commit
from yondo_api.core.deps import CurrentUser, Session
from yondo_api.core.schemas import Page, PageParams, page_of
from yondo_api.gifts import service
from yondo_api.gifts.models import (
    CATEGORIES,
    CartItem,
    FavoriteProduct,
    GiftOrder,
    GiftOrderStatus,
    GiftReview,
    Product,
    Vendor,
)
from yondo_api.gifts.schemas import (
    CartItemView,
    CartLine,
    CartView,
    CatalogPage,
    Category,
    CategoryCount,
    GiftOrderView,
    GiftReviewCreate,
    GiftReviewView,
    ProductCard,
    ProductPage,
)
from yondo_api.notifications.service import notify

router = APIRouter(prefix='/gifts', tags=['gifts'])
favorites_router = APIRouter(prefix='/favorites', tags=['favorites'])


async def visible_product(session, product_id: UUID) -> tuple[Product, Vendor]:
    row = (await session.execute(service.visible_query().where(Product.id == product_id))).first()
    if row is None:
        raise ApplicationError('product_not_found', 'Product not found', 404)
    return row[0], row[1]


@router.get('/categories', response_model=list[CategoryCount])
async def categories(user: CurrentUser, session: Session):
    counts = dict(
        (
            await session.execute(
                service.visible_query()
                .with_only_columns(Product.category, func.count())
                .group_by(Product.category)
            )
        ).all()
    )
    return [CategoryCount(category=c, products=counts.get(c, 0)) for c in CATEGORIES]


@router.get('/products', response_model=CatalogPage)
async def products(
    request: Request,
    user: CurrentUser,
    session: Session,
    category: Category | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    vendor_id: UUID | None = None,
    price_min: Annotated[int | None, Query(ge=0)] = None,
    price_max: Annotated[int | None, Query(ge=0)] = None,
    city: Annotated[str | None, Query(max_length=128)] = None,
    in_stock: bool = True,
    favorites_only: bool = False,
    sort: Literal['newest', 'price_asc', 'price_desc'] = 'newest',
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
):
    query = service.visible_query()
    if category:
        query = query.where(Product.category == category)
    if q:
        escaped = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        pattern = f'%{escaped}%'
        query = query.where(
            or_(
                Product.name.ilike(pattern, escape='\\'),
                Product.description.ilike(pattern, escape='\\'),
            )
        )
    if vendor_id:
        query = query.where(Vendor.id == vendor_id)
    if price_min is not None:
        query = query.where(Product.price_minor >= price_min)
    if price_max is not None:
        query = query.where(Product.price_minor <= price_max)
    if city:
        query = query.where(func.lower(Vendor.city) == city.lower())
    if in_stock:
        query = query.where(Product.stock > 0)
    if favorites_only:
        query = query.where(
            Product.id.in_(
                select(FavoriteProduct.product_id).where(FavoriteProduct.user_id == user.id)
            )
        )
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    order = {
        'newest': (Product.created_at.desc(), Product.id),
        'price_asc': (Product.price_minor, Product.id),
        'price_desc': (Product.price_minor.desc(), Product.id),
    }[sort]
    rows = list(await session.execute(query.order_by(*order).offset(offset).limit(limit)))
    return CatalogPage(
        items=await service.product_cards(request, session, user, [tuple(r) for r in rows]),
        total=total,
        next_offset=offset + limit if offset + limit < total else None,
    )


@router.get('/products/{product_id}', response_model=ProductPage)
async def product_page(product_id: UUID, request: Request, user: CurrentUser, session: Session):
    product, vendor = await visible_product(session, product_id)
    card = (await service.product_cards(request, session, user, [(product, vendor)]))[0]
    images = await service.image_views(request, session, [product.id])
    return ProductPage(
        **card.model_dump(),
        description=product.description,
        images=images.get(product.id, []),
        stock=product.stock,
        vendor_city=vendor.city,
        delivery_fee_minor=vendor.delivery_fee_minor,
    )


# --- Favorites -----------------------------------------------------------------------------


@favorites_router.get('/products', response_model=list[ProductCard])
async def favorite_products(request: Request, user: CurrentUser, session: Session):
    rows = list(
        await session.execute(
            service.visible_query().where(
                Product.id.in_(
                    select(FavoriteProduct.product_id).where(FavoriteProduct.user_id == user.id)
                )
            )
        )
    )
    return await service.product_cards(request, session, user, [tuple(r) for r in rows])


@favorites_router.put('/products/{product_id}', status_code=204)
async def add_favorite(product_id: UUID, user: CurrentUser, session: Session):
    await visible_product(session, product_id)
    if await session.get(FavoriteProduct, (user.id, product_id)) is None:
        session.add(FavoriteProduct(user_id=user.id, product_id=product_id))
        await commit(session)
    return Response(status_code=204)


@favorites_router.delete('/products/{product_id}', status_code=204)
async def remove_favorite(product_id: UUID, user: CurrentUser, session: Session):
    await session.execute(
        delete(FavoriteProduct).where(
            FavoriteProduct.user_id == user.id, FavoriteProduct.product_id == product_id
        )
    )
    await commit(session)
    return Response(status_code=204)


# --- Cart ----------------------------------------------------------------------------------


async def cart_view(request: Request, session, user) -> CartView:
    items = list(await session.scalars(select(CartItem).where(CartItem.user_id == user.id)))
    rows = (
        {
            product.id: (product, vendor)
            for product, vendor in await session.execute(
                service.visible_query().where(Product.id.in_([i.product_id for i in items]))
            )
        }
        if items
        else {}
    )
    visible = [item for item in items if item.product_id in rows]
    cards = {
        card.id: card
        for card in await service.product_cards(
            request, session, user, [rows[item.product_id] for item in visible]
        )
    }
    lines = [
        CartItemView(
            product=cards[item.product_id],
            quantity=item.quantity,
            note=item.note,
            line_total_minor=rows[item.product_id][0].price_minor * item.quantity,
        )
        for item in visible
    ]
    currencies = {line.product.currency for line in lines}
    return CartView(
        items=lines,
        currency=currencies.pop() if len(currencies) == 1 else None,
        subtotal_minor=sum(line.line_total_minor for line in lines),
    )


@router.get('/cart', response_model=CartView)
async def get_cart(request: Request, user: CurrentUser, session: Session):
    return await cart_view(request, session, user)


@router.put('/cart/items/{product_id}', response_model=CartView)
async def set_cart_item(
    product_id: UUID, payload: CartLine, request: Request, user: CurrentUser, session: Session
):
    product, _ = await visible_product(session, product_id)
    if payload.quantity > product.stock:
        raise ApplicationError('insufficient_stock', 'Not enough stock', 409)
    other_currency = await session.scalar(
        select(Product.currency)
        .join(CartItem, CartItem.product_id == Product.id)
        .where(CartItem.user_id == user.id, Product.currency != product.currency)
        .limit(1)
    )
    if other_currency is not None:
        raise ApplicationError('currency_mismatch', 'The cart holds another currency', 422)
    item = await session.get(CartItem, (user.id, product_id))
    if item is None:
        session.add(
            CartItem(
                user_id=user.id,
                product_id=product_id,
                quantity=payload.quantity,
                note=payload.note,
            )
        )
    else:
        item.quantity = payload.quantity
        item.note = payload.note
    await commit(session)
    return await cart_view(request, session, user)


@router.delete('/cart/items/{product_id}', response_model=CartView)
async def remove_cart_item(product_id: UUID, request: Request, user: CurrentUser, session: Session):
    await session.execute(
        delete(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id)
    )
    await commit(session)
    return await cart_view(request, session, user)


@router.delete('/cart', status_code=204)
async def clear_cart(user: CurrentUser, session: Session):
    await session.execute(delete(CartItem).where(CartItem.user_id == user.id))
    await commit(session)
    return Response(status_code=204)


# --- Orders --------------------------------------------------------------------------------


async def own_order(session, order_id: UUID, user, *, lock: bool = False) -> GiftOrder:
    query = select(GiftOrder).where(GiftOrder.id == order_id, GiftOrder.customer_id == user.id)
    if lock:
        query = query.with_for_update()
    order = await session.scalar(query)
    if order is None:
        raise ApplicationError('gift_order_not_found', 'Order not found', 404)
    return order


@router.get('/orders', response_model=Page[GiftOrderView])
async def my_orders(user: CurrentUser, session: Session, params: Annotated[PageParams, Depends()]):
    rows = list(
        await session.scalars(
            select(GiftOrder)
            .where(GiftOrder.customer_id == user.id)
            .order_by(GiftOrder.created_at.desc(), GiftOrder.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    page = page_of(rows, params)
    return Page[GiftOrderView](
        items=await service.order_views(session, page.items), next_offset=page.next_offset
    )


@router.get('/orders/{order_id}', response_model=GiftOrderView)
async def order_detail(order_id: UUID, user: CurrentUser, session: Session):
    return (await service.order_views(session, [await own_order(session, order_id, user)]))[0]


@router.post('/orders/{order_id}/cancel', response_model=GiftOrderView)
async def cancel_order(order_id: UUID, request: Request, user: CurrentUser, session: Session):
    from yondo_api.payments.service import process_refunds

    order = await own_order(session, order_id, user, lock=True)
    if order.status != GiftOrderStatus.NEW:
        raise ApplicationError(
            'gift_order_in_progress',
            'Only orders the vendor has not accepted can be cancelled',
            409,
        )
    await service.cancel_order(session, order, 'customer_cancelled', refund=True)
    vendor = await session.get(Vendor, order.vendor_id)
    notify(
        session,
        vendor.user_id,
        'gift_order_cancelled',
        'Buyurtma bekor qilindi',
        'Mijoz buyurtmani bekor qildi.',
        {'gift_order_id': order.id},
    )
    await commit(session)
    await process_refunds(session, request.app.state)
    return (await service.order_views(session, [order]))[0]


@router.post('/orders/{order_id}/review', response_model=GiftReviewView, status_code=201)
async def review_order(
    order_id: UUID, payload: GiftReviewCreate, user: CurrentUser, session: Session
):
    order = await own_order(session, order_id, user)
    if order.status != GiftOrderStatus.DELIVERED:
        raise ApplicationError('review_not_allowed', 'Only delivered orders can be reviewed', 409)
    review = GiftReview(
        order_id=order.id,
        customer_id=user.id,
        vendor_id=order.vendor_id,
        rating=payload.rating,
        text=payload.text,
    )
    session.add(review)
    await commit(session, 'review_exists', 'You already reviewed this order')
    return review
