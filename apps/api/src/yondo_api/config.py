from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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
    # Telegram Gateway (https://core.telegram.org/gateway): delivers login codes to the user's
    # Telegram account. Unset token = not configured. Never log or echo the token.
    telegram_gateway_token: SecretStr | None = None
    telegram_gateway_base_url: str = 'https://gatewayapi.telegram.org'
    telegram_gateway_timeout_seconds: float = Field(default=10.0, gt=0)
    # Unset until the fee policy has been approved. Values are basis points.
    platform_fee_bps: int | None = Field(default=None, ge=0, le=10_000)
    # Offline CLICK Shop API emulator only. Never accepts or moves real funds.
    click_test_enabled: bool = False
    click_test_service_id: int | None = Field(default=None, gt=0)
    click_test_secret: SecretStr = SecretStr('')
    # TezCheck payment aggregator (https://tezcheck.uz/api-docs). Empty token = not configured.
    tezcheck_api_url: str = 'https://api.tezcheck.uz/api/merchant/v1'
    tezcheck_token: SecretStr = SecretStr('')
    tezcheck_cash_desk_code: str = ''
    tezcheck_webhook_secret: SecretStr = SecretStr('')
    tezcheck_return_url: str = ''
    # Accept payments TezCheck marks as environment "test" (its test provider). Never in prod.
    tezcheck_accept_test_payments: bool = False

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

    @model_validator(mode='after')
    def validate_companion_settings(self) -> Settings:
        if (
            self.companion_price_max_minor is not None
            and self.companion_price_max_minor < self.companion_price_min_minor
        ):
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

    @field_validator('telegram_gateway_token')
    @classmethod
    def empty_telegram_gateway_token_is_unset(cls, value: SecretStr | None) -> SecretStr | None:
        # `YONDO_TELEGRAM_GATEWAY_TOKEN=` (empty) in an env file must mean "not configured".
        if value is not None and not value.get_secret_value().strip():
            return None
        return value

    @model_validator(mode='after')
    def validate_telegram_gateway(self) -> Settings:
        if self.telegram_gateway_token is None:
            return self
        if not self.telegram_gateway_base_url.startswith('https://'):
            raise ValueError('YONDO_TELEGRAM_GATEWAY_BASE_URL must be an https URL')
        return self

    @model_validator(mode='after')
    def validate_click_test_mode(self) -> Settings:
        if self.click_test_enabled and (
            self.environment not in {'test', 'development'}
            or self.click_test_service_id is None
            or len(self.click_test_secret.get_secret_value()) < 32
        ):
            raise ValueError(
                'CLICK test mode requires a local environment, service ID and 32+ character key'
            )
        return self

    @model_validator(mode='after')
    def validate_tezcheck(self) -> Settings:
        if self.tezcheck_accept_test_payments and self.environment == 'production':
            raise ValueError('YONDO_TEZCHECK_ACCEPT_TEST_PAYMENTS is not allowed in production')
        if self.tezcheck_token.get_secret_value():
            if not self.tezcheck_api_url.startswith('https://'):
                raise ValueError('YONDO_TEZCHECK_API_URL must be an https URL')
            if len(self.tezcheck_webhook_secret.get_secret_value()) < 16:
                raise ValueError(
                    'TezCheck needs YONDO_TEZCHECK_WEBHOOK_SECRET (16+ characters): '
                    'without it payment events cannot be verified'
                )
        return self

    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace('postgresql+psycopg_async', 'postgresql+psycopg')

    @property
    def database_url_async(self) -> str:
        return self.database_url.replace('postgresql+psycopg://', 'postgresql+psycopg_async://')


@lru_cache
def get_settings() -> Settings:
    return Settings()
