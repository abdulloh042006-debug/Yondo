from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    provider_reference: str
    checkout_url: str


@dataclass(frozen=True, slots=True)
class PaymentEvent:
    event_id: str
    provider_reference: str
    status: str


class PaymentProvider(Protocol):
    async def create_checkout(
        self,
        *,
        idempotency_key: str,
        amount_minor: int,
        currency: str,
        description: str,
    ) -> CheckoutSession: ...

    async def verify_event(self, body: bytes, headers: dict[str, str]) -> PaymentEvent: ...


class UnconfiguredPaymentProvider:
    async def create_checkout(self, **kwargs) -> CheckoutSession:
        raise RuntimeError('Payment provider is not configured')

    async def verify_event(self, body: bytes, headers: dict[str, str]) -> PaymentEvent:
        raise RuntimeError('Payment provider is not configured')
