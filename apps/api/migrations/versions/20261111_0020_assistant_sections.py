"""assistant knowledge index (approved documents only)

Additive: one new table. On PostgreSQL it also enables pg_trgm and adds a trigram index and a
full-text index on the normalised search text.

Revision ID: 20261111_0020
Revises: 20261111_0019
Create Date: 2026-11-11 07:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261111_0020'
down_revision: str | None = '20261111_0019'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'assistant_sections',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('doc_id', sa.String(length=128), nullable=False),
        sa.Column('language', sa.String(length=8), nullable=False),
        sa.Column('audience', sa.String(length=16), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=512), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('search_text', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.CheckConstraint(
            "audience IN ('public', 'internal', 'shared')", name='ck_assistant_sections_audience'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('doc_id', 'language', name='uq_assistant_sections_doc_language'),
    )
    op.create_index(
        'ix_assistant_sections_language_audience',
        'assistant_sections',
        ['language', 'audience'],
        unique=False,
    )
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
        op.execute(
            'CREATE INDEX ix_assistant_sections_trgm ON assistant_sections '
            'USING gin (search_text gin_trgm_ops)'
        )
        op.execute(
            'CREATE INDEX ix_assistant_sections_fts ON assistant_sections '
            "USING gin (to_tsvector('simple', search_text))"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP INDEX IF EXISTS ix_assistant_sections_fts')
        op.execute('DROP INDEX IF EXISTS ix_assistant_sections_trgm')
        # pg_trgm is left installed: other objects may use it.
    op.drop_index('ix_assistant_sections_language_audience', table_name='assistant_sections')
    op.drop_table('assistant_sections')
