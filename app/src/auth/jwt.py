from datetime import datetime, timedelta

from databases.interfaces import Record
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.auth.config import settings as auth_settings
from src.auth.exceptions import AuthorizationFailed, AuthRequired, InvalidToken
from src.auth.schemas import JWTData


class OptionalHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        try:
            return await super().__call__(request)
        except AuthRequired:
            return None


optional_bearer = OptionalHTTPBearer(auto_error=False)


def create_access_token(
        *,
        user: Record,
        expires_delta: timedelta = timedelta(minutes=auth_settings.JWT_EXP),
) -> str:
    jwt_data = {
        "sub": str(user["id"]),
        "exp": datetime.utcnow() + expires_delta,
        "is_admin": user["is_admin"],
    }

    encoded_jwt = jwt.encode(
        jwt_data, auth_settings.JWT_SECRET, algorithm=auth_settings.JWT_ALG
    )
    return encoded_jwt


def decode_token(token: HTTPAuthorizationCredentials) -> dict:
    try:
        return jwt.decode(
            token.credentials,
            auth_settings.JWT_SECRET,
            algorithms=[auth_settings.JWT_ALG],
        )
    except JWTError:
        raise InvalidToken()


async def parse_jwt_user_data_optional(
        token: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
) -> JWTData | None:
    if not token:
        return None

    if isinstance(token.credentials, str):
        creds = token.credentials
        if creds[0] == '"' and creds[-1] == '"':
            token.credentials = creds[1:-1]

    try:
        payload = decode_token(token)
        return JWTData(**payload)
    except InvalidToken:
        return None


async def parse_jwt_user_data(
        token: JWTData | None = Depends(parse_jwt_user_data_optional),
) -> JWTData:
    if not token:
        raise AuthRequired()

    return token


async def parse_jwt_admin_data(
        token: JWTData = Depends(parse_jwt_user_data),
) -> JWTData:
    if not token.is_admin:
        raise AuthorizationFailed()

    return token


async def validate_admin_access(
        token: JWTData | None = Depends(parse_jwt_user_data_optional),
) -> None:
    if token and token.is_admin:
        return

    raise AuthorizationFailed()
