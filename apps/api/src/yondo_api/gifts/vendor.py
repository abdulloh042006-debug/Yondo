"""Phase 17 vendor panel API: profile, products, images, stock, orders and ratings (TZ §30)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import object_storage
from yondo_api.core.db import commit, lock_users
from yondo_api.core.deps import CurrentUser, Session, has_role
from yondo_api.core.images import (
    IMAGE_REQUEST_BODY,
    discard_image,
    read_image,
    signed_url,
    store_image,
)
from yondo_api.core.schemas import Page, PageParams, page_of
from yondo_api.gifts import service
from yondo_api.gifts.models import (
    GiftOrder,
    GiftOrderStatus,
    GiftReview,
    Product,
    ProductImage,
    Vendor,
    VendorStatus,
)
from yondo_api.gifts.schemas import (
    GiftOrderView,
    GiftReviewView,
    ImageView,
    OrderStatusUpdate,
    ProductWrite,
    StockUpdate,
    VendorProduct,
    VendorRatings,
    VendorResponse,
    VendorWrite,
)
from yondo_api.models.user import AccountStatus, User, UserRoleType

router = APIRouter(prefix='/vendors/me', tags=['vendor panel'])


async def vendor_user(user: CurrentUser, session: Session) -> User:
    if user.account_status not in {AccountStatus.ACTIVE, AccountStatus.VERIFICATION_PENDING}:
        raise ApplicationError('vendor_forbidden', 'This operation is not permitted', 403)
    if not await has_role(session, user, UserRoleType.VENDOR):
        raise ApplicationError('vendor_role_required', 'Select the vendor role first', 403)
    return user


VendorUser = Annotated[User, Depends(vendor_user)]


async def my_vendor(session, user: User, *, approved: bool = False) -> Vendor:
    vendor = await session.scalar(select(Vendor).where(Vendor.user_id == user.id))
    if vendor is None:
        raise ApplicationError('vendor_not_found', 'Create your vendor profile first', 404)
    if approved and vendor.status != VendorStatus.APPROVED:
        raise ApplicationError('vendor_not_approved', 'The vendor is not approved yet', 403)
    return vendor


async def my_product(session, vendor: Vendor, product_id: UUID, *, lock=False) -> Product:
    query = select(Product).where(Product.id == product_id, Product.vendor_id == vendor.id)
    if lock:
        query = query.with_for_update()
    product = await session.scalar(query)
    if product is None:
        raise ApplicationError('product_not_found', 'Product not found', 404)
    return product


async def product_view(request: Request, session, product: Product) -> VendorProduct:
    view = VendorProduct.model_validate(product)
    view.images = (await service.image_views(request, session, [product.id])).get(product.id, [])
    return view


@router.get('', response_model=VendorResponse)
async def get_vendor(user: VendorUser, session: Session):
    return await my_vendor(session, user)


@router.post('', response_model=VendorResponse, status_code=201)
async def apply(payload: VendorWrite, user: VendorUser, session: Session):
    """Vendor application; an administrator approves it before products are listed."""
    vendor = Vendor(user_id=user.id, status=VendorStatus.PENDING, **payload.model_dump())
    session.add(vendor)
    await commit(session, 'vendor_exists', 'A vendor profile already exists')
    return vendor


@router.put('', response_model=VendorResponse)
async def update_vendor(payload: VendorWrite, user: VendorUser, session: Session):
    vendor = await my_vendor(session, user)
    if payload.currency != vendor.currency and await session.scalar(
        select(Product.id).where(Product.vendor_id == vendor.id).limit(1)
    ):
        raise ApplicationError('currency_locked', 'Currency cannot change once products exist', 409)
    for key, value in payload.model_dump().items():
        setattr(vendor, key, value)
    if vendor.status == VendorStatus.REJECTED:
        vendor.status = VendorStatus.PENDING  # resubmission after rejection
    await commit(session)
    return vendor


@router.get('/products', response_model=list[VendorProduct])
async def list_products(request: Request, user: VendorUser, session: Session):
    vendor = await my_vendor(session, user)
    products = list(
        await session.scalars(
            select(Product).where(Product.vendor_id == vendor.id).order_by(Product.created_at)
        )
    )
    images = await service.image_views(request, session, [p.id for p in products])
    views = []
    for product in products:
        view = VendorProduct.model_validate(product)
        view.images = images.get(product.id, [])
        views.append(view)
    return views


@router.post('/products', response_model=VendorProduct, status_code=201)
async def create_product(
    payload: ProductWrite, request: Request, user: VendorUser, session: Session
):
    vendor = await my_vendor(session, user, approved=True)
    product = Product(vendor_id=vendor.id, currency=vendor.currency, **payload.model_dump())
    session.add(product)
    await commit(session)
    return await product_view(request, session, product)


@router.put('/products/{product_id}', response_model=VendorProduct)
async def update_product(
    product_id: UUID, payload: ProductWrite, request: Request, user: VendorUser, session: Session
):
    vendor = await my_vendor(session, user, approved=True)
    product = await my_product(session, vendor, product_id, lock=True)
    for key, value in payload.model_dump().items():
        setattr(product, key, value)
    await commit(session)
    return await product_view(request, session, product)


@router.put('/products/{product_id}/stock', response_model=VendorProduct)
async def set_stock(
    product_id: UUID, payload: StockUpdate, request: Request, user: VendorUser, session: Session
):
    vendor = await my_vendor(session, user)
    product = await my_product(session, vendor, product_id, lock=True)
    product.stock = payload.stock
    await commit(session)
    return await product_view(request, session, product)


@router.delete('/products/{product_id}', status_code=204)
async def deactivate_product(product_id: UUID, user: VendorUser, session: Session):
    """Products referenced by orders are deactivated, never hard-deleted."""
    vendor = await my_vendor(session, user)
    product = await my_product(session, vendor, product_id, lock=True)
    product.is_active = False
    await commit(session)
    return Response(status_code=204)


@router.post(
    '/products/{product_id}/images',
    response_model=ImageView,
    status_code=201,
    openapi_extra=IMAGE_REQUEST_BODY,
)
async def upload_image(product_id: UUID, request: Request, user: VendorUser, session: Session):
    settings = request.app.state.settings
    object_storage(request)
    vendor = await my_vendor(session, user, approved=True)
    product = await my_product(session, vendor, product_id)
    count = await session.scalar(
        select(func.count()).select_from(ProductImage).where(ProductImage.product_id == product.id)
    )
    if count >= settings.gift_max_product_images:
        raise ApplicationError('image_limit', 'Configured image limit reached', 422)
    content, width, height = await read_image(request)
    key = f'products/{product.id}/{uuid4()}.jpg'
    await store_image(request, key, content)
    try:
        await lock_users(session, [user.id])
        position = await session.scalar(
            select(func.coalesce(func.max(ProductImage.position) + 1, 0)).where(
                ProductImage.product_id == product_id
            )
        )
        image = ProductImage(
            product_id=product_id, storage_key=key, position=position, width=width, height=height
        )
        session.add(image)
        await commit(session)
    except BaseException:
        await discard_image(request, key)
        raise
    return ImageView(id=image.id, url=await signed_url(request, key), width=width, height=height)


@router.delete('/products/{product_id}/images/{image_id}', status_code=204)
async def delete_image(
    product_id: UUID, image_id: UUID, request: Request, user: VendorUser, session: Session
):
    vendor = await my_vendor(session, user)
    await my_product(session, vendor, product_id)
    image = await session.scalar(
        select(ProductImage).where(
            ProductImage.id == image_id, ProductImage.product_id == product_id
        )
    )
    if image is None:
        raise ApplicationError('image_not_found', 'Image not found', 404)
    key = image.storage_key
    await session.delete(image)
    await commit(session)
    await discard_image(request, key)
    return Response(status_code=204)


@router.get('/orders', response_model=Page[GiftOrderView])
async def vendor_orders(
    user: VendorUser,
    session: Session,
    params: Annotated[PageParams, Depends()],
    status: GiftOrderStatus | None = None,
):
    vendor = await my_vendor(session, user)
    query = select(GiftOrder).where(
        GiftOrder.vendor_id == vendor.id, GiftOrder.status != GiftOrderStatus.PENDING_PAYMENT
    )
    if status:
        query = query.where(GiftOrder.status == status)
    rows = list(
        await session.scalars(
            query.order_by(GiftOrder.delivery_at, GiftOrder.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    page = page_of(rows, params)
    return Page[GiftOrderView](
        items=await service.order_views(session, page.items), next_offset=page.next_offset
    )


@router.post('/orders/{order_id}/status', response_model=GiftOrderView)
async def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    request: Request,
    user: VendorUser,
    session: Session,
):
    from yondo_api.payments.service import process_refunds

    vendor = await my_vendor(session, user)
    order = await service.advance(
        session, request.app.state.settings, vendor, order_id, payload.status
    )
    await commit(session)
    await process_refunds(session, request.app.state)
    return (await service.order_views(session, [order]))[0]


@router.get('/ratings', response_model=VendorRatings)
async def ratings(user: VendorUser, session: Session):
    vendor = await my_vendor(session, user)
    reviews = list(
        await session.scalars(
            select(GiftReview)
            .where(GiftReview.vendor_id == vendor.id)
            .order_by(GiftReview.created_at.desc())
            .limit(100)
        )
    )
    count = len(reviews)
    return VendorRatings(
        rating_average=round(sum(r.rating for r in reviews) / count, 2) if count else None,
        rating_count=count,
        reviews=[GiftReviewView.model_validate(r) for r in reviews],
    )
