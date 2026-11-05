"""Store the user's interface language, including the Uzbek alphabet variant.

Revision ID: 20261023_0015
Revises: 20261013_0014
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261023_0015'
down_revision: str | None = '20261013_0014'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UI_LOCALES = "ui_locale IS NULL OR ui_locale IN ('uz-Latn-1995', 'uz-Latn-2026', 'ru', 'en')"


def upgrade() -> None:
    # Additive and nullable: existing users keep NULL (= not chosen, client default applies).
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('ui_locale', sa.String(length=16), nullable=True))
        batch.create_check_constraint('ck_users_ui_locale', UI_LOCALES)


def downgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.drop_constraint('ck_users_ui_locale', type_='check')
        batch.drop_column('ui_locale')
