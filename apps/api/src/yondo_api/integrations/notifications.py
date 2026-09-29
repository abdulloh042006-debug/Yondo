from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PushMessage:
    token: str
    title: str
    body: str
    data: dict[str, str]


class NotificationProvider(Protocol):
    async def send(self, message: PushMessage) -> str: ...
