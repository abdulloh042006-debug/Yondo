from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Normalize database values; SQLite returns naive datetimes for timezone columns."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
