from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from yondo_api.models.user import UserRoleType

OtpValue = Annotated[str, StringConstraints(pattern=r'^\d{6}$')]


class OtpRequest(BaseModel):
    phone_number: str = Field(min_length=9, max_length=32)


class OtpRequestResponse(BaseModel):
    message: str
    expires_in_seconds: int
    resend_after_seconds: int
    development_otp: str | None = None


class OtpVerification(BaseModel):
    phone_number: str = Field(min_length=9, max_length=32)
    code: OtpValue


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=256)


class RoleSelection(BaseModel):
    roles: list[UserRoleType] = Field(min_length=1)


# Interface language. Uzbek has two Latin spellings: the 1995 alphabet (o‘ g‘ sh ch) and the 2026
# alphabet (ö ğ ş ç, in force from 2027-04-22); the year is a BCP 47 variant subtag.
UiLocale = Literal['uz-Latn-1995', 'uz-Latn-2026', 'ru', 'en']


class UserProfileUpdate(BaseModel):
    """Partial update: only fields present in the request body are changed."""

    age: int | None = Field(default=None, ge=0)
    gender: str | None = Field(default=None, max_length=64)
    city: str | None = Field(default=None, max_length=128)
    ui_locale: UiLocale | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    phone_number: str
    age: int | None
    gender: str | None
    city: str | None
    ui_locale: UiLocale | None = None
    roles: list[UserRoleType]
    created_at: datetime
