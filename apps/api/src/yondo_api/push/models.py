"""Push notification device registry and the server's Web Push (VAPID) key pair."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class PushDevice(TimestampMixin, Base):
    """One push target: an Android FCM token or a browser Web Push subscription."""

    __tablename__ = 'push_devices'
    __table_args__ = (
        CheckConstraint("platform IN ('android', 'web')", name='ck_push_device_platform'),
        CheckConstraint(
            "(platform = 'android' AND fcm_token IS NOT NULL AND endpoint IS NULL "
            'AND p256dh IS NULL AND auth_secret IS NULL) OR '
            "(platform = 'web' AND fcm_token IS NULL AND endpoint IS NOT NULL "
            'AND p256dh IS NOT NULL AND auth_secret IS NOT NULL)',
            name='ck_push_device_target',
        ),
        Index('ix_push_devices_user', 'user_id'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    platform: Mapped[str] = mapped_column(String(16))
    fcm_token: Mapped[str | None] = mapped_column(String(1024), unique=True)
    endpoint: Mapped[str | None] = mapped_column(String(1024), unique=True)
    p256dh: Mapped[str | None] = mapped_column(String(128))
    auth_secret: Mapped[str | None] = mapped_column(String(64))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PushVapidKey(TimestampMixin, Base):
    """The single Web Push VAPID key pair, generated once when the env does not supply one.

    The private key is a raw P-256 scalar (base64url). It never leaves the server: it is not
    logged and not returned by any endpoint; only the public key is published.
    """

    __tablename__ = 'push_vapid_keys'
    __table_args__ = (CheckConstraint('id = 1', name='ck_push_vapid_single_row'),)
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    private_key: Mapped[str] = mapped_column(Text)
    public_key: Mapped[str] = mapped_column(String(128))
