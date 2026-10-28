"""Migration 20261028_0018: upgrade / downgrade / upgrade on a scratch SQLite database."""

import sqlite3

import pytest
from alembic import command
from alembic.config import Config

from yondo_api.config import get_settings

NEW_TABLES = {
    'cancellation_events', 'cancellation_cases', 'booking_restrictions',
    'cancellation_audit_entries',
}


def tables(path):
    with sqlite3.connect(path) as db:
        return {r[0] for r in db.execute("select name from sqlite_master where type='table'")}


@pytest.fixture
def alembic_config(tmp_path, monkeypatch):
    path = tmp_path / 'migration.db'
    monkeypatch.setenv('YONDO_DATABASE_URL', f'sqlite:///{path}')
    get_settings.cache_clear()
    yield Config('alembic.ini'), path
    get_settings.cache_clear()


def test_upgrade_downgrade_upgrade(alembic_config):
    cfg, path = alembic_config
    command.upgrade(cfg, '20261023_0017')
    assert not NEW_TABLES & tables(path)
    command.upgrade(cfg, 'head')
    assert NEW_TABLES <= tables(path)
    with sqlite3.connect(path) as db:
        # Booking-less restriction notices are allowed only for their own kinds.
        db.execute('PRAGMA foreign_keys=OFF')
        sql = (
            'insert into user_notifications (id, recipient_id, kind, source_key, details, '
            "created_at, updated_at) values (?, 'u1', ?, ?, '{}', '2027-01-01', '2027-01-01')"
        )
        db.execute(sql, ('n1', 'booking_restricted', 's1'))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(sql, ('n2', 'booking_cancelled', 's2'))
    command.downgrade(cfg, '20261023_0017')
    assert not NEW_TABLES & tables(path)
    with sqlite3.connect(path) as db:
        # The notice of a new kind could not survive the old constraint and was removed.
        assert db.execute("select count(*) from user_notifications").fetchone()[0] == 0
    command.upgrade(cfg, 'head')
    assert NEW_TABLES <= tables(path)
