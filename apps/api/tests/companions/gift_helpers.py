"""Test helper: vendors need an approved shop (product decisions §4, 2026-11-19)."""

from uuid import UUID

from yondo_api.gifts.shop_models import VendorShop


def approved_shop(user_id: UUID) -> VendorShop:
    return VendorShop(
        user_id=user_id,
        name='Test shop',
        description='A shop used by the automated tests.',
        city='Toshkent',
        delivery_area='Toshkent',
        status='approved',
    )
