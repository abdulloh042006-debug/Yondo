from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class GiftProduct(TimestampMixin, Base):
    __tablename__ = 'gift_products'
    __table_args__ = (
        CheckConstraint('price_minor >= 0', name='ck_gift_price'),
        CheckConstraint('stock >= 0', name='ck_gift_stock'),
        CheckConstraint(
            "category IN ('flowers','chocolate','gift_box','toys','birthday','romantic','custom')",
            name='ck_gift_category',
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vendor_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    category: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    price_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    stock: Mapped[int] = mapped_column(default=0)
    published: Mapped[bool] = mapped_column(default=False, server_default='false')


class GiftCartItem(TimestampMixin, Base):
    __tablename__ = 'gift_cart_items'
    __table_args__ = (
        UniqueConstraint('customer_id', 'product_id', name='uq_gift_cart_item'),
        CheckConstraint('quantity BETWEEN 1 AND 100', name='ck_gift_cart_quantity'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    product_id: Mapped[UUID] = mapped_column(ForeignKey('gift_products.id', ondelete='RESTRICT'))
    quantity: Mapped[int] = mapped_column()
