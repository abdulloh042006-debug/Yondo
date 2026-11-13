"""Indexed knowledge-base sections: one row per approved document and language."""

from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class AssistantSection(TimestampMixin, Base):
    __tablename__ = 'assistant_sections'
    __table_args__ = (
        UniqueConstraint('doc_id', 'language', name='uq_assistant_sections_doc_language'),
        CheckConstraint(
            "audience IN ('public', 'internal', 'shared')", name='ck_assistant_sections_audience'
        ),
        Index('ix_assistant_sections_language_audience', 'language', 'audience'),
        # PostgreSQL-only search indexes, created by migration 0020 (pg_trgm + full text).
        Index(
            'ix_assistant_sections_trgm',
            'search_text',
            postgresql_using='gin',
            postgresql_ops={'search_text': 'gin_trgm_ops'},
        ).ddl_if(dialect='postgresql'),
        Index(
            'ix_assistant_sections_fts',
            func.to_tsvector(text("'simple'"), text('search_text')),
            postgresql_using='gin',
        ).ddl_if(dialect='postgresql'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    doc_id: Mapped[str] = mapped_column(String(128))
    language: Mapped[str] = mapped_column(String(8))
    audience: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(512))
    # Shown to the user verbatim: the section's own "### " heading (or the document title) and
    # the section text after it.
    title: Mapped[str] = mapped_column(String(512))
    answer: Mapped[str] = mapped_column(Text)
    # Normalised (lower case, Uzbek alphabets folded) title + answer, used only for matching.
    search_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
