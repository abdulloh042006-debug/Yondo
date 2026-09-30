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
