from datetime import datetime
from typing import Annotated
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


class UserProfileUpdate(BaseModel):
    age: int | None = Field(default=None, ge=0)
    gender: str | None = Field(default=None, max_length=64)
    city: str | None = Field(default=None, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    phone_number: str
    age: int | None
    gender: str | None
    city: str | None
    roles: list[UserRoleType]
    created_at: datetime
