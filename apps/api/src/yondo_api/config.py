from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_prefix='YONDO_',
        case_sensitive=False,
        extra='ignore',
    )

    app_name: str = 'Yondo API'
    app_version: str = '0.1.0'
    environment: Literal['development', 'test', 'staging', 'production'] = 'development'
    debug: bool = False
    log_level: str = 'INFO'
    api_v1_prefix: str = '/api/v1'
    database_url: str = 'postgresql+psycopg://yondo:yondo@localhost:5432/yondo'
    redis_url: str = 'redis://localhost:6379/0'
    storage_endpoint: str = 'http://localhost:9000'
    storage_bucket: str = 'yondo-local'
    storage_access_key: str = ''
    storage_secret_key: str = Field(default='', repr=False)
    storage_region: str = 'us-east-1'
    fcm_project_id: str = ''
    auth_otp_pepper: SecretStr = SecretStr('development-only-change-me')
    auth_access_token_lifetime_seconds: int = Field(default=900, gt=0)
    auth_refresh_token_lifetime_seconds: int = Field(default=2_592_000, gt=0)
    auth_otp_provider_rate_limit_per_minute: int = Field(default=0, ge=0)

    # Technical resource limits, configurable independently of business policy.
    companion_max_photos: int = Field(default=20, gt=0, le=1000)
    companion_photo_max_bytes: int = Field(default=10_485_760, gt=0)
    companion_photo_max_pixels: int = Field(default=25_000_000, gt=0)
    companion_service_codes: tuple[str, ...] = (
        'coffee',
        'walking',
        'cinema',
        'shopping',
        'event',
        'city_friend',
        'conversation',
        'study_coworking',
    )
    # No currency, price cap, or duration policy is inferred. Empty means unset.
    companion_allowed_currencies: tuple[str, ...] = ()
    companion_price_min_minor: int = Field(default=0, ge=0)
    companion_price_max_minor: int | None = Field(default=None, gt=0)
    companion_allowed_unit_minutes: tuple[int, ...] = ()

    # Accounts. PLACEHOLDER policy: minimum age must be confirmed by the business/legal team.
    account_min_age: int = Field(default=18, ge=0, le=150)

    # Object storage backend. 'local' is a development-only filesystem adapter.
    storage_backend: Literal['disabled', 's3', 'local'] = 'disabled'
    storage_path_style: bool = True
    storage_public_endpoint: str | None = None
    storage_local_root: str = '.storage'
    storage_local_public_url: str = 'http://localhost:8000/api/v1/storage/local'

    # Browser origins allowed to call the API (admin/vendor web panel). JSON array.
    cors_allow_origins: tuple[str, ...] = ()

    # Realtime fan-out. 'auto' uses memory in tests and Redis elsewhere.
    realtime_backend: Literal['auto', 'memory', 'redis'] = 'auto'

    # Booking. PLACEHOLDER policy values; every number is configurable and pending approval.
    booking_default_timezone: str = 'Asia/Tashkent'
    booking_min_lead_minutes: int = Field(default=60, ge=0)
    booking_max_horizon_days: int = Field(default=60, gt=0)
    booking_max_duration_minutes: int = Field(default=480, gt=0)
    booking_request_ttl_minutes: int = Field(default=120, gt=0)
    booking_payment_window_minutes: int = Field(default=60, gt=0)
    booking_platform_fee_bps: int = Field(default=1000, ge=0, le=10_000)
    booking_companion_commission_bps: int = Field(default=0, ge=0, le=10_000)
    booking_free_cancellation_hours: int = Field(default=24, ge=0)
    booking_late_cancellation_refund_bps: int = Field(default=5000, ge=0, le=10_000)
    booking_contract_version: str = 'draft-2026-11'

    # Meeting flow.
    meeting_checkin_window_minutes: int = Field(default=30, ge=0)
    meeting_no_show_grace_minutes: int = Field(default=15, ge=0)
    # PLACEHOLDER: active meetings nobody ended are completed this long after scheduled end.
    meeting_auto_complete_hours: int = Field(default=2, gt=0)

    # Payments. 'sandbox' simulates a provider and is refused outside local environments.
    payment_provider: Literal['auto', 'sandbox', 'disabled'] = 'auto'
    payment_webhook_secret: SecretStr = SecretStr('development-only-webhook-secret')
    payment_checkout_base_url: str = 'http://localhost:8000/api/v1/payments/sandbox'
    payout_release_delay_hours: int = Field(default=24, ge=0)

    # Reviews. Quick-tag taxonomy is a PLACEHOLDER pending product approval.
    review_window_days: int = Field(default=14, gt=0)
    review_tags_for_companion: tuple[str, ...] = (
        'punctual',
        'friendly',
        'great_conversation',
        'respectful',
        'as_described',
    )
    review_tags_for_customer: tuple[str, ...] = (
        'respectful',
        'punctual',
        'polite',
        'followed_rules',
        'pleasant',
    )

    # Gifts marketplace.
    gift_platform_fee_bps: int = Field(default=0, ge=0, le=10_000)
    vendor_commission_bps: int = Field(default=0, ge=0, le=10_000)
    gift_max_product_images: int = Field(default=10, gt=0, le=100)
    gift_payment_window_minutes: int = Field(default=30, gt=0)

    # Notifications and background worker.
    push_provider: Literal['log', 'fcm', 'disabled'] = 'log'
    fcm_service_account_file: str | None = None
    meeting_reminder_minutes: int = Field(default=60, gt=0)
    review_reminder_minutes: int = Field(default=120, gt=0)
    worker_interval_seconds: int = Field(default=30, gt=0)

    # Safety. PLACEHOLDER: how long after a meeting a dispute may be opened.
    booking_share_ttl_hours: int = Field(default=24, gt=0)
    dispute_window_days: int = Field(default=7, gt=0)

    @model_validator(mode='after')
    def validate_companion_settings(self) -> Settings:
        if (self.companion_price_max_minor is not None
                and self.companion_price_max_minor < self.companion_price_min_minor):
            raise ValueError('Companion maximum price must not be below minimum price')
        if any(value <= 0 for value in self.companion_allowed_unit_minutes):
            raise ValueError('Companion pricing units must be positive minutes')
        return self

    @model_validator(mode='after')
    def validate_production_auth_settings(self) -> Settings:
        if self.environment in {'staging', 'production'} and (
            self.auth_otp_pepper.get_secret_value() == 'development-only-change-me'
            or len(self.auth_otp_pepper.get_secret_value()) < 32
        ):
            raise ValueError(
                'YONDO_AUTH_OTP_PEPPER must be at least 32 characters outside local environments'
            )
        return self

    @model_validator(mode='after')
    def validate_production_integrations(self) -> Settings:
        if self.environment in {'staging', 'production'}:
            if self.payment_provider == 'sandbox':
                raise ValueError('The sandbox payment provider is only for local environments')
            if self.storage_backend == 'local':
                raise ValueError('Local filesystem storage is only for local environments')
        return self

    @property
    def effective_payment_provider(self) -> str:
        if self.payment_provider == 'auto':
            return 'sandbox' if self.is_local else 'disabled'
        return self.payment_provider

    @property
    def is_local(self) -> bool:
        return self.environment in {'development', 'test'}

    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace('postgresql+psycopg_async', 'postgresql+psycopg')

    @property
    def database_url_async(self) -> str:
        return self.database_url.replace(
            'postgresql+psycopg://', 'postgresql+psycopg_async://'
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
