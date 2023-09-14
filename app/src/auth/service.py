import uuid
from datetime import datetime, timedelta

from databases.interfaces import Record
from pydantic import UUID4
from sqlalchemy import insert, select
from sqlalchemy.exc import NoResultFound

from src import utils
from src.auth.config import settings as auth_settings
from src.auth.exceptions import InvalidCredentials
from src.auth.schemas import AuthUser
from src.auth.security import check_password, generate_random_password, hash_password
from src.database import auth_user, database, refresh_tokens


async def get_or_create_user(user: dict, is_admin: bool = False) -> Record | None:
    select_query = select(auth_user).where(auth_user.c.email == user["email"])
    existing_user = await database.fetch_one(select_query)

    if existing_user:
        return existing_user

    insert_query = (
        insert(auth_user)
        .values(
            {
                "email": user["email"],
                "created_at": datetime.utcnow(),
                "password": hash_password(
                    user.get("password") or generate_random_password()
                ),
                "is_admin": is_admin,
                "picture": user.get("picture"),
                "name": user.get("name"),
            }
        )
        .returning(auth_user)
    )

    return await database.fetch_one(insert_query)


async def get_user_by_id(user_id: int) -> Record | None:
    select_query = select(auth_user).where(auth_user.c.id == user_id)

    try:
        return await database.fetch_one(select_query)
    except NoResultFound:
        return None


async def get_user_by_email(email: str) -> Record | None:
    select_query = select(auth_user).where(auth_user.c.email == email)

    return await database.fetch_one(select_query)


async def create_refresh_token(
    *, user_id: int, refresh_token: str | None = None
) -> str:
    if not refresh_token:
        refresh_token = utils.generate_random_alphanum(64)

    insert_query = refresh_tokens.insert().values(
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
    select_query = refresh_tokens.select().where(
        refresh_tokens.c.refresh_token == refresh_token
    )

    return await database.fetch_one(select_query)


async def expire_refresh_token(refresh_token_uuid: UUID4) -> None:
    update_query = (
        refresh_tokens.update()
        .values(expires_at=datetime.utcnow() - timedelta(days=1))
        .where(refresh_tokens.c.uuid == refresh_token_uuid)
    )

    await database.execute(update_query)


async def authenticate_user(auth_data: AuthUser) -> Record:
    user = await get_user_by_email(auth_data.email)
    if not user:
        raise InvalidCredentials()

    if not check_password(auth_data.password, user["password"]):
        raise InvalidCredentials()

    return user
