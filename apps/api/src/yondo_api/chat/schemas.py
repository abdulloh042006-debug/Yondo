from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Discriminator, Field, Tag

from yondo_api.bookings.schemas import MeetingPlace
from yondo_api.core.schemas import Input, Output, UtcDatetime


class TextMessage(Input):
    kind: Literal['text'] = 'text'
    body: str = Field(min_length=1, max_length=2000)


class MeetingPointMessage(Input):
    kind: Literal['meeting_point']
    meeting_point: MeetingPlace
    body: str = Field(default='', max_length=500)


def _message_kind(value: Any) -> str:
    if isinstance(value, dict):
        return value.get('kind', 'text')
    return getattr(value, 'kind', 'text')


# ``kind`` defaults to text so simple clients can send ``{"body": "..."}``.
OutgoingMessage = Annotated[
    Annotated[TextMessage, Tag('text')] | Annotated[MeetingPointMessage, Tag('meeting_point')],
    Discriminator(_message_kind),
]


class MessageResponse(Output):
    id: UUID
    booking_id: UUID
    sender_id: UUID | None
    kind: str
    body: str
    payload: dict[str, Any]
    image_url: str | None = None
    created_at: UtcDatetime


class Conversation(Output):
    booking_id: UUID
    booking_status: str
    counterpart_id: UUID
    counterpart_name: str | None
    starts_at: UtcDatetime
    last_message: MessageResponse | None
    unread: int
    can_send: bool


class UnreadTotal(Output):
    unread: int
