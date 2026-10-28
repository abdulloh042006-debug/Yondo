from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatMessageWrite(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    kind: Literal['text', 'meeting_point'] = 'text'
    body: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    sender_id: UUID | None
    kind: str
    body: str | None
    payload: dict | None
    system_code: str | None
    created_at: datetime

    @field_validator('created_at')
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ChatSocketTicket(BaseModel):
    ticket: str
    expires_in_seconds: int = 90


class ChatReadResult(BaseModel):
    booking_id: UUID
    unread_count: int


class ChatUnreadItem(BaseModel):
    booking_id: UUID
    unread_count: int
