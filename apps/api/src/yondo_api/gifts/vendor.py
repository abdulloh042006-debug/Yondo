"""Vendor inventory controls; real orders and earnings require order/payment contracts."""
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.gifts.models import GiftProduct
from yondo_api.gifts.router import Category, ProductRead, require_role
from yondo_api.models.user import UserRoleType

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
        'orders_available': False, 'earnings_available': False,
    }

@router.get('/orders', status_code=503)
async def orders(principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.VENDOR)
    raise ApplicationError('gift_orders_unavailable', 'Gift orders are not configured', 503)

@router.get('/earnings', status_code=503)
async def earnings(principal: Principal, session: Session):
    await require_role(principal, session, UserRoleType.VENDOR)
    raise ApplicationError('vendor_earnings_unavailable', 'Gift payouts not configured', 503)
