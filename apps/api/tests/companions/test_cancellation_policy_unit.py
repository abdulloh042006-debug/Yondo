"""Pure rules (no database): classification, counting, settings validation and defaults."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from yondo_api.cancellations.policy import (
    CancellationPolicy,
    CountedEvent,
    is_last_minute,
    lead_seconds,
    summarize,
)
from yondo_api.config import Settings

NOW = datetime(2027, 1, 1, tzinfo=UTC)


def settings(**kw):
    return Settings(_env_file=None, environment='test', **kw)


def policy(**kw):
    return CancellationPolicy.from_settings(settings(**kw))


def event(kind='cancelled', excuse='none', last_minute=False, status='accepted', at=NOW):
    return CountedEvent(kind, excuse, last_minute, status, at)


@pytest.mark.parametrize(
    ('lead', 'expected'),
    [(24 * 3600 + 1, False), (24 * 3600, False), (24 * 3600 - 1, True), (0, True), (-60, True)],
)
def test_last_minute_boundary_is_strictly_before_the_deadline(lead, expected):
    assert is_last_minute(lead, 24) is expected


def test_lead_seconds_handles_naive_and_aware_times():
    start = datetime(2027, 1, 10, 6, 0)  # naive = UTC (SQLite)
    assert lead_seconds(start, datetime(2027, 1, 10, 5, 0, tzinfo=UTC)) == 3600
    assert lead_seconds(start, datetime(2027, 1, 10, 7, 0, tzinfo=UTC)) == -3600


def test_defaults_are_conservative_placeholders():
    s = settings()
    assert s.cancellation_tracking_enabled is True
    assert s.cancellation_last_minute_hours == 24
    assert s.booking_restriction_default_days <= s.booking_restriction_max_days
    # There is no automatic-restriction or money setting at all.
    assert not [n for n in Settings.model_fields if 'fee' in n and 'cancel' in n]
    assert not [n for n in Settings.model_fields if 'auto' in n and 'restrict' in n]


def test_counters_ignore_excused_pending_and_out_of_window_events():
    p = policy()
    since = NOW - timedelta(days=30)
    counters = summarize(
        [
            event(last_minute=True),
            event(),
            event(status='pending'),  # withdrawing an unanswered request: recorded, not counted
            event(excuse='granted'),  # excused: never counts
            event(excuse='claimed'),  # claimed emergency: counts only as a claim
            event(excuse='rejected'),  # claim refused: counts
            event(kind='declined'),
            event(kind='expired'),
            event(kind='no_show'),
            event(kind='no_show', excuse='granted'),
            event(at=NOW - timedelta(days=31)),
        ],
        p,
        since,
    )
    assert (counters.cancellations, counters.last_minute) == (3, 1)
    assert (counters.no_shows, counters.emergency_claims, counters.excused) == (1, 1, 2)


def test_pending_requests_count_only_when_configured():
    assert summarize([event(status='pending')], policy(cancellation_count_pending_requests=True),
                     NOW - timedelta(days=1)).cancellations == 1


def test_a_closed_case_moves_the_baseline_of_its_trigger_only():
    p = policy()
    since = {t: NOW - timedelta(days=30)
             for t in ('cancellations', 'last_minute', 'no_shows', 'emergency_claims')}
    since['cancellations'] = NOW + timedelta(hours=1)
    counters = summarize([event(last_minute=True), event(kind='no_show')], p, since)
    assert (counters.cancellations, counters.last_minute, counters.no_shows) == (0, 1, 1)


def test_settings_validation_rejects_inconsistent_values():
    with pytest.raises(ValidationError):
        settings(booking_restriction_default_days=10, booking_restriction_max_days=5)
    with pytest.raises(ValidationError):
        settings(cancellation_warning_threshold=6, cancellation_review_threshold=5)
    with pytest.raises(ValidationError):
        settings(cancellation_last_minute_hours=0)
    with pytest.raises(ValidationError):
        settings(cancellation_window_days=-1)
    # 0 switches a threshold off; a warning without a review threshold is allowed.
    assert settings(cancellation_review_threshold=0).cancellation_review_threshold == 0


def test_every_policy_number_is_configurable_from_the_environment(monkeypatch):
    monkeypatch.setenv('YONDO_CANCELLATION_LAST_MINUTE_HOURS', '12')
    monkeypatch.setenv('YONDO_CANCELLATION_WINDOW_DAYS', '60')
    monkeypatch.setenv('YONDO_BOOKING_RESTRICTION_DEFAULT_DAYS', '3')
    monkeypatch.setenv('YONDO_BOOKING_REQUESTS_PER_HOUR_LIMIT', '5')
    s = Settings(_env_file=None, environment='test')
    assert (s.cancellation_last_minute_hours, s.cancellation_window_days) == (12, 60)
    assert (s.booking_restriction_default_days, s.booking_requests_per_hour_limit) == (3, 5)
