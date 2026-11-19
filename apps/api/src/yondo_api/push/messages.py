"""Lock-screen texts for push notifications.

Only the kind of event is shown ("bron qabul qilindi"): no names, places, amounts or chat text,
because a push is visible on a locked screen. Uzbek has the 1995 and 2026 Latin spellings.
"""
from datetime import UTC, date, datetime

UZ_2026_FROM = date(2027, 4, 22)

_EVENTS = {
    # kind: (uz 1995, uz 2026, ru, en)
    'booking_requested': (
        'yangi bron so‘rovi', 'yangi bron sörovi', 'новый запрос на бронь', 'new booking request'
    ),
    'booking_accepted': (
        'bron qabul qilindi', 'bron qabul qilindi', 'бронь принята', 'booking accepted'
    ),
    'booking_declined': (
        'bron rad etildi', 'bron rad etildi', 'бронь отклонена', 'booking declined'
    ),
    'booking_cancelled': (
        'bron bekor qilindi', 'bron bekor qilindi', 'бронь отменена', 'booking cancelled'
    ),
    'payment_confirmed': (
        'to‘lov tasdiqlandi', 'tölov tasdiqlandi', 'оплата подтверждена', 'payment confirmed'
    ),
    'chat_message': ('yangi xabar', 'yangi xabar', 'новое сообщение', 'new message'),
    'review_reminder': (
        'uchrashuvni baholang', 'uçrashuvni baholang', 'оцените встречу', 'rate your meeting'
    ),
}
_GIFT = ('sovg‘a buyurtmasi yangilandi', 'sovğa buyurtmasi yangilandi',
         'заказ подарка обновлён', 'gift order updated')
# Shop decisions and product rejections (gift vendors, 2026-11-19): no reason on the lock screen.
_SHOP = ('do‘kon holati yangilandi', 'dökon holati yangilandi',
         'статус магазина обновлён', 'shop status updated')
_SHOP_KINDS = frozenset({'vendor_approved', 'vendor_rejected', 'vendor_suspended',
                         'gift_product_rejected'})
_PREFIX = ('Yangi bildirishnoma', 'Yangi bildirişnoma', 'Новое уведомление', 'New notification')
_INDEX = {'uz-Latn-1995': 0, 'uz-Latn-2026': 1, 'ru': 2, 'en': 3}


def resolve_locale(ui_locale: str | None, today: date | None = None) -> str:
    if ui_locale in _INDEX:
        return ui_locale
    today = today or datetime.now(UTC).date()
    return 'uz-Latn-2026' if today >= UZ_2026_FROM else 'uz-Latn-1995'


def push_text(kind: str, ui_locale: str | None) -> tuple[str, str]:
    """Return (title, body) for the lock screen."""
    index = _INDEX[resolve_locale(ui_locale)]
    if kind in _SHOP_KINDS:
        event = _SHOP
    else:
        event = _EVENTS.get(kind, _GIFT if kind.startswith('gift_') else None)
    body = f'{_PREFIX[index]}: {event[index]}' if event else _PREFIX[index]
    return 'Yondo', body
