from datetime import datetime

from databases.interfaces import Record
from fastapi import Depends

from src.auth import service
from src.auth.exceptions import EmailTaken, RefreshTokenNotValid
from src.auth.schemas import AuthUser


async def valid_user_create(user: AuthUser) -> AuthUser:
    if await service.get_user_by_email(user.email):
        raise EmailTaken()

    return user


async def valid_refresh_token(
    refresh_token: str,
) -> Record:
    db_refresh_token = await service.get_refresh_token(refresh_token)
    if not db_refresh_token:
        raise RefreshTokenNotValid()

    if not _is_valid_refresh_token(db_refresh_token):
        raise RefreshTokenNotValid()

    return db_refresh_token


async def valid_refresh_token_by_user(
    refresh_token: Record = Depends(valid_refresh_token),
) -> Record:
    user = await service.get_user_by_id(refresh_token["user_id"])
    if not user:
        raise RefreshTokenNotValid()

    return user


def _is_valid_refresh_token(db_refresh_token: Record) -> bool:
    exp_at_obj = db_refresh_token["expires_at"]
    now = datetime.utcnow().replace(tzinfo=exp_at_obj.tzinfo)

    return now <= exp_at_obj
