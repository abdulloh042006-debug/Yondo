from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class StoryKind(StrEnum):
    # Built from the companion's live free windows at read time; never typed free text.
    AVAILABILITY = 'availability'
    # A short caption, optionally on top of one of the companion's own profile photos.
    NOTE = 'note'


class CompanionStory(TimestampMixin, Base):
    """A 24-hour card on the home screen. No media of its own, no location, no viewer tracking."""

    __tablename__ = 'companion_stories'
    __table_args__ = (
        CheckConstraint("kind IN ('availability', 'note')", name='ck_companion_story_kind'),
        CheckConstraint(
            "kind = 'availability' OR length(caption) > 0", name='ck_companion_story_note_caption'
        ),
        Index('ix_companion_stories_profile_expires', 'profile_id', 'expires_at'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey('companion_profiles.id', ondelete='CASCADE')
    )
    kind: Mapped[str] = mapped_column(String(16))
    caption: Mapped[str] = mapped_column(String(80), default='')
    # Backdrop and call-to-action target; if the photo or service is deleted the card stays.
    photo_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('companion_photos.id', ondelete='SET NULL')
    )
    service_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('companion_services.id', ondelete='SET NULL')
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Soft removal keeps the row for reports and the admin trail (captions are blanked on erasure).
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removed_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    removal_note: Mapped[str | None] = mapped_column(Text)
