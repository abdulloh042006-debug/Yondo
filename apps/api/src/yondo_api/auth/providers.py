from dataclasses import dataclass
from typing import Protocol

from yondo_api.api.errors import ApplicationError


@dataclass(frozen=True, slots=True)
class OtpDelivery:
    development_code: str | None = None


class OtpDeliveryProvider(Protocol):
    async def deliver(self, phone_number: str, code: str) -> OtpDelivery: ...


class OtpRateLimitHook(Protocol):
    async def check(self) -> None: ...


class DevelopmentOtpProvider:
    async def deliver(self, phone_number: str, code: str) -> OtpDelivery:
        return OtpDelivery(development_code=code)


class UnconfiguredOtpProvider:
    async def deliver(self, phone_number: str, code: str) -> OtpDelivery:
        raise ApplicationError(
            'otp_delivery_unavailable',
            'OTP delivery is not configured',
            503,
        )


class NoopOtpRateLimitHook:
    async def check(self) -> None:
        return None


class RedisOtpRateLimitHook:
    def __init__(self, redis_client: object, requests_per_minute: int) -> None:
        self.redis_client = redis_client
        self.requests_per_minute = requests_per_minute

    async def check(self) -> None:
        import time

        minute = int(time.time() // 60)
        key = f'yondo:otp:provider:{minute}'
        count = await self.redis_client.incr(key)  # type: ignore[attr-defined]
        if count == 1:
            await self.redis_client.expire(key, 120)  # type: ignore[attr-defined]
        if count > self.requests_per_minute:
            raise ApplicationError('otp_rate_limited', 'OTP request rate limit exceeded', 429)
