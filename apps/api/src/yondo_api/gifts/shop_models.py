"""Vendor shop profile (product decisions §4; CEO 2026-11-19): mandatory before a vendor sells.

A vendor becomes active only on admin approval; the ID check reuses the identity verification
(ID + selfie, images deleted at the decision). Contact is in-app only: no phone is stored here.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin

SHOP_STATUSES = ('pending', 'approved', 'rejected', 'suspended')


class VendorShop(TimestampMixin, Base):
    __tablename__ = 'vendor_shops'
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'suspended')",
            name='ck_vendor_shop_status',
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(128))
    # Free text: where the shop delivers (no address of any customer is stored here).
    delivery_area: Mapped[str] = mapped_column(String(500))
    logo_key: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default='pending')
    # Shown to the vendor: the reason of a rejection or suspension.
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
