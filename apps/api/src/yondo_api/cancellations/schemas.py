from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from yondo_api.account.router import UtcDatetime

Role = Literal['customer', 'companion']
EventKind = Literal['cancelled', 'declined', 'no_show', 'expired']
Party = Literal['customer', 'companion', 'admin', 'system']
ExcuseState = Literal['none', 'claimed', 'granted', 'rejected']
ReviewState = Literal['none', 'open', 'reviewed']
CaseTrigger = Literal['cancellations', 'last_minute', 'no_shows', 'emergency_claims']
Note = Field(min_length=8, max_length=2000)


class MyEventRead(BaseModel):
    """A user's own event. No user ids at all: a customer never sees a companion's id."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    booking_id: UUID
    kind: EventKind
    subject_role: Role | None
    occurred_at: UtcDatetime
    last_minute: bool
    reason: str
    excuse_state: ExcuseState
    review_state: ReviewState


class MyRestrictionRead(BaseModel):
    """Own restriction: end time and role only; the admin's reason stays internal."""

    id: UUID
    role: Role
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    active: bool
    lifted_at: UtcDatetime | None


class DisputeWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    note: str = Note
    emergency: bool = Field(default=False, description='Claim that this was an emergency.')


class AdminEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    booking_id: UUID
    kind: EventKind
    party: Party
    actor_user_id: UUID | None
    subject_user_id: UUID | None
    subject_role: Role | None
    booking_status_before: str
    booking_starts_at: UtcDatetime
    occurred_at: UtcDatetime
    lead_seconds: int
    last_minute: bool
    reason: str
    excuse_state: ExcuseState
    review_state: ReviewState
    dispute_note: str | None
    disputed_at: UtcDatetime | None
    reviewed_by: UUID | None
    reviewed_at: UtcDatetime | None
    review_note: str | None


class EventReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['excuse', 'uphold']
    note: str = Note


class NoShowWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    party: Role = Field(description='Who did not show up.')
    note: str = Note
    excused: bool = False


class AdminCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    role: Role
    trigger: CaseTrigger
    status: Literal['open', 'closed']
    snapshot: dict
    opened_at: UtcDatetime
    closed_at: UtcDatetime | None
    closed_by: UUID | None
    resolution: Literal['no_action', 'restricted'] | None
    note: str | None


class CaseClose(BaseModel):
    model_config = ConfigDict(extra='forbid')
    note: str = Note


class RestrictionCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    user_id: UUID
    role: Role
    duration_days: int | None = Field(
        default=None, ge=1, le=365, description='Omitted = the configured default.'
    )
    reason: str = Note
    case_id: UUID | None = None


class RestrictionLift(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reason: str = Note


class AdminRestrictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    role: Role
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    reason: str
    case_id: UUID | None
    created_by: UUID
    lifted_at: UtcDatetime | None
    lifted_by: UUID | None
    lift_reason: str | None
    active: bool


class CancellationAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    action: str
    actor_kind: str
    actor_user_id: UUID | None
    subject_user_id: UUID | None
    booking_id: UUID | None
    event_id: UUID | None
    case_id: UUID | None
    restriction_id: UUID | None
    previous_state: dict | None
    new_state: dict | None
    reason: str | None
    created_at: UtcDatetime


class CountersRead(BaseModel):
    cancellations: int
    last_minute: int
    no_shows: int
    emergency_claims: int
    excused: int


class RoleSummary(BaseModel):
    role: Role
    window_days: int
    counters: CountersRead
    thresholds: dict[str, int]
    needs_review: bool
    open_case_ids: list[UUID]
    active_restriction: AdminRestrictionRead | None


class UserCancellationSummary(BaseModel):
    user_id: UUID
    roles: list[RoleSummary]
