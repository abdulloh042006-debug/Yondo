from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

MAX_BIGINT = 9_223_372_036_854_775_807


def _utc(value: datetime) -> str:
    value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return value.isoformat().replace('+00:00', 'Z')


# Serializes database datetimes (naive on SQLite) as explicit UTC instants.
UtcDatetime = Annotated[datetime, PlainSerializer(_utc, return_type=str)]
MinorAmount = Annotated[int, Field(strict=True, ge=0, le=MAX_BIGINT)]


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    next_offset: int | None = None


class PageParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=100_000)


def page_of[T](rows: list[T], params: PageParams) -> Page[T]:
    """Build a page from ``limit + 1`` fetched rows."""
    has_more = len(rows) > params.limit
    return Page[T](
        items=rows[: params.limit],
        next_offset=params.offset + params.limit if has_more else None,
    )
