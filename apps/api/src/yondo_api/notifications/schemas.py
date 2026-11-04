from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from yondo_api.core.schemas import Input, Output, UtcDatetime


class NotificationResponse(Output):
    id: UUID
    kind: str
    title: str
    body: str
    data: dict[str, Any]
    read_at: UtcDatetime | None
    created_at: UtcDatetime


class UnreadCount(Output):
    unread: int


class DeviceRegistration(Input):
    token: str = Field(min_length=8, max_length=512)
    platform: Literal['android', 'ios', 'web']


class DeviceRemoval(Input):
    token: str = Field(min_length=8, max_length=512)
