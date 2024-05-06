import uuid
from datetime import datetime, timedelta

from databases.interfaces import Record
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import UUID4
from sqlalchemy import insert, select, update
from sqlalchemy.exc import NoResultFound

from src import utils
from src.auth.config import settings as auth_settings
from src.auth.exceptions import InvalidCredentials, UserNotFound
from src.auth.jwt import parse_jwt_user_data_optional
from src.auth.schemas import AuthUser, JWTData, UserDB
from src.auth.security import check_password, generate_random_password, hash_password
from src.database import RefreshToken, User, database


async def get_or_create_user(user: dict, is_admin: bool = False) -> Record | None:
    select_query = select(User).where(User.email == user["email"])
    existing_user = await database.fetch_one(select_query)

    if existing_user:
        if user.get("google_access_token"):
            update_query = (
                update(User)
                .where(User.email == user["email"])
                .values(
                    {
                        "credentials": {
                            "google_access_token": user.get("google_access_token"),
                            "google_refresh_token": user.get("google_refresh_token"),
                        }
                    }
                )
                .returning(User)
            )
            return await database.fetch_one(update_query)
        return existing_user

    insert_query = (
        insert(User)
        .values(
            {
                "email": user["email"],
                "password": hash_password(
                    user.get("password") or generate_random_password()
                ),
                "is_admin": is_admin,
                "picture": user.get("picture"),
                "name": user.get("name"),
                "credentials": {
                    "google_access_token": user.get("google_access_token"),
                    "google_refresh_token": user.get("google_refresh_token"),
                },
            }
        )
        .returning(User)
    )

    return await database.fetch_one(insert_query)


async def get_users_from_db() -> dict:
    select_query = select(User)

    await database.fetch_all(select_query)

    return {
        "status": "ok",
    }


async def get_user_by_id(user_id: int) -> Record | None:
    select_query = select(User).where(User.id == user_id)

    try:
        return await database.fetch_one(select_query)
    except NoResultFound:
        return None


async def get_user_by_email(email: str) -> Record | None:
    select_query = select(User).where(User.email == email)

    return await database.fetch_one(select_query)


async def create_refresh_token(
    *, user_id: int, refresh_token: str | None = None
) -> str:
    if not refresh_token:
        refresh_token = utils.generate_random_alphanum(64)

    insert_query = insert(RefreshToken).values(
        uuid=uuid.uuid4(),
        refresh_token=refresh_token,
        expires_at=(
            datetime.utcnow() + timedelta(seconds=auth_settings.REFRESH_TOKEN_EXP)
        ),
        user_id=user_id,
    )
    await database.execute(insert_query)

    return refresh_token


async def get_refresh_token(refresh_token: str) -> Record | None:
    select_query = select(RefreshToken).where(
        RefreshToken.refresh_token == refresh_token
    )

    return await database.fetch_one(select_query)


async def expire_refresh_token(refresh_token_uuid: UUID4) -> None:
    update_query = (
        update(RefreshToken)
        .values(expires_at=datetime.utcnow() - timedelta(days=1))
        .where(RefreshToken.uuid == refresh_token_uuid)
    )

    await database.execute(update_query)


async def authenticate_user(auth_data: AuthUser) -> Record:
    user = await get_user_by_email(auth_data.email)
    if not user:
        raise InvalidCredentials()

    if not check_password(auth_data.password, user["password"]):
        raise InvalidCredentials()

    return user


async def is_user_admin_by_id(user_id: int) -> bool:
    user_data = await get_user_by_id(user_id)
    if not user_data:
        raise UserNotFound()

    user = UserDB(**dict(user_data))

    return user.is_admin


async def get_user_by_token(token: str | None) -> UserDB:
    # check if user is authenticated
    if not token:
        raise UserNotFound()

    jwt_data: JWTData | None = await parse_jwt_user_data_optional(
        HTTPAuthorizationCredentials(scheme="bearer", credentials=token)
    )
    if not jwt_data:
        raise UserNotFound()
    user = await get_user_by_id(jwt_data.user_id)

    if not user:
        raise UserNotFound()
    user_db = UserDB(**dict(user))

    return user_db


async def update_user_google_token(
    user: UserDB, google_access_token: str | None
) -> Record | None:
    new_credentials = user.credentials.copy() if user.credentials else {}
    if google_access_token:
        new_credentials["google_access_token"] = google_access_token

    update_query = (
        update(User)
        .where(User.email == user.email)
        .values(
            {
                "credentials": new_credentials,
            }
        )
        .returning(User)
    )

    return await database.fetch_one(update_query)
