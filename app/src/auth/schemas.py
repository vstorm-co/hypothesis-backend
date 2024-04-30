import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.models import ORJSONModel

STRONG_PASSWORD_PATTERN = re.compile(r"^(?=.*[\d])(?=.*[!@#$%^&*])[\w!@#$%^&*]{6,128}$")


class AuthUser(ORJSONModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if isinstance(value, str):
            is_valid = re.match(STRONG_PASSWORD_PATTERN, value)
            not_valid_info = """
            Password must contain at least:
            - one lower character,
            - one upper character,
            - digit or special symbol
            """
            assert is_valid, not_valid_info
        return value


class JWTData(ORJSONModel):
    user_id: int = Field(alias="sub")
    is_admin: bool = False


class AccessTokenResponse(ORJSONModel):
    access_token: str
    refresh_token: str


class UserResponse(ORJSONModel):
    email: EmailStr


class GoogleUserInfo(BaseModel):
    # watch out
    # this is mostly like to change in the future
    # as google love to change their response
    # current status: 2024-03-20
    iss: str
    azp: str
    aud: str
    sub: str
    email: str
    email_verified: bool
    at_hash: str
    name: str
    picture: str
    given_name: str
    iat: int
    exp: int
    google_access_token: str
    google_refresh_token: str
    family_name: str | None = None


class UserDB(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    created_at: datetime
    updated_at: datetime | None = None
    picture: str | None = None
    name: str | None = None
    credentials: dict | None = None


class OrganizationInfoVerifyResponse(BaseModel):
    name: str
    created: bool


class VerifyResponse(GoogleUserInfo):
    user_id: int
    access_token: str
    refresh_token: str
    organization: OrganizationInfoVerifyResponse | None = None
