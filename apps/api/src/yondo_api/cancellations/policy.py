"""Pure cancellation-policy rules (no database, no clock): classification and counting.

All numbers come from `Settings` (YONDO_CANCELLATION_* / YONDO_BOOKING_*); the defaults are
PLACEHOLDERS awaiting the owner's approved policy (docs/cancellation-policy.md).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from yondo_api.config import Settings

# Booking states in which the other party has committed (accepted) or paid (confirmed).
COMMITTED_STATUSES = ('accepted', 'confirmed')
COUNTING_EXCUSE_STATES = ('none', 'rejected')  # 'claimed' and 'granted' never count.


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class CancellationPolicy:
    tracking_enabled: bool
    last_minute_hours: int
    window_days: int
    count_pending_requests: bool
    warning_threshold: int
    review_threshold: int
    last_minute_review_threshold: int
    no_show_review_threshold: int
    emergency_claim_review_threshold: int
    restriction_default_days: int
    restriction_max_days: int

    @classmethod
    def from_settings(cls, settings: Settings) -> CancellationPolicy:
        return cls(
            tracking_enabled=settings.cancellation_tracking_enabled,
            last_minute_hours=settings.cancellation_last_minute_hours,
            window_days=settings.cancellation_window_days,
            count_pending_requests=settings.cancellation_count_pending_requests,
            warning_threshold=settings.cancellation_warning_threshold,
            review_threshold=settings.cancellation_review_threshold,
            last_minute_review_threshold=settings.cancellation_last_minute_review_threshold,
            no_show_review_threshold=settings.cancellation_no_show_review_threshold,
            emergency_claim_review_threshold=settings.cancellation_emergency_claim_review_threshold,
            restriction_default_days=settings.booking_restriction_default_days,
            restriction_max_days=settings.booking_restriction_max_days,
        )

    def thresholds(self) -> dict[str, int]:
        """Case trigger -> threshold (0 = that trigger is switched off)."""
        return {
            'cancellations': self.review_threshold,
            'last_minute': self.last_minute_review_threshold,
            'no_shows': self.no_show_review_threshold,
            'emergency_claims': self.emergency_claim_review_threshold,
        }

    def window_start(self, now: datetime) -> datetime:
        return now - timedelta(days=self.window_days)


def iso_z(value: datetime) -> str:
    """UTC instant with a `Z` suffix, the same spelling the API uses for datetimes."""
    return as_utc(value).isoformat().replace('+00:00', 'Z')


def lead_seconds(starts_at: datetime, occurred_at: datetime) -> int:
    """Seconds from the event to the booking start; negative once the start has passed."""
    return int((as_utc(starts_at) - as_utc(occurred_at)).total_seconds())


def is_last_minute(lead: int, last_minute_hours: int) -> bool:
    """Strictly less than the deadline: cancelling exactly `last_minute_hours` ahead is on time."""
    return lead < last_minute_hours * 3600


@dataclass(frozen=True, slots=True)
class CountedEvent:
    """The fields of an event that the counters need."""

    kind: str
    excuse_state: str
    last_minute: bool
    booking_status_before: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class Counters:
    cancellations: int = 0
    last_minute: int = 0
    no_shows: int = 0
    emergency_claims: int = 0
    excused: int = 0  # granted: tracked, never counted

    def get(self, trigger: str) -> int:
        return getattr(self, trigger)


def counts_as_cancellation(event: CountedEvent, policy: CancellationPolicy) -> bool:
    if event.kind != 'cancelled' or event.excuse_state not in COUNTING_EXCUSE_STATES:
        return False
    # Withdrawing a request nobody has accepted yet costs the other side nothing.
    return policy.count_pending_requests or event.booking_status_before in COMMITTED_STATUSES


def summarize(
    events: Iterable[CountedEvent],
    policy: CancellationPolicy,
    since: dict[str, datetime] | datetime,
) -> Counters:
    """Count events per trigger.

    `since` is the window start, or a per-trigger map (a closed review case moves the baseline
    of its trigger forward so a reviewed history is not counted twice).
    """
    def floor(trigger: str) -> datetime:
        return since if isinstance(since, datetime) else since[trigger]

    counters = dict.fromkeys(
        ('cancellations', 'last_minute', 'no_shows', 'emergency_claims', 'excused'), 0
    )
    for event in events:
        if event.kind in ('cancelled', 'no_show') and event.excuse_state == 'granted':
            counters['excused'] += 1
        if (
            event.kind in ('cancelled', 'no_show')
            and event.excuse_state == 'claimed'
            and event.occurred_at >= floor('emergency_claims')
        ):
            counters['emergency_claims'] += 1
        if counts_as_cancellation(event, policy):
            if event.occurred_at >= floor('cancellations'):
                counters['cancellations'] += 1
            if event.last_minute and event.occurred_at >= floor('last_minute'):
                counters['last_minute'] += 1
        elif (
            event.kind == 'no_show'
            and event.excuse_state in COUNTING_EXCUSE_STATES
            and event.occurred_at >= floor('no_shows')
        ):
            counters['no_shows'] += 1
    return Counters(**counters)
