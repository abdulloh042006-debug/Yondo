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
