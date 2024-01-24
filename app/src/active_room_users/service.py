import logging

from asyncpg import ForeignKeyViolationError, UniqueViolationError
from sqlalchemy import and_, delete, insert, select

from src.active_room_users.schemas import ActiveRoomUsersInput
from src.auth.schemas import UserDB
from src.auth.service import get_user_by_id
from src.database import ActiveRoomUsers, database

logger = logging.getLogger(__name__)


async def create_active_room_user_in_db(
    room_uuid: str,
    user_id: int,
) -> None:
    active_room_user = ActiveRoomUsersInput(room_uuid=room_uuid, user_id=user_id)

    insert_query = insert(ActiveRoomUsers).values(**active_room_user.model_dump())
    try:
        await database.execute(insert_query)
    except ForeignKeyViolationError:
        logger.warning(f"Room with uuid {room_uuid} does not exist")
        return None
    except UniqueViolationError:
        logger.warning("User already exists in room")
        return None

    logger.info(f"Active user {user_id} added to room {room_uuid}")


async def delete_active_room_user_from_db(
    room_uuid: str,
    user_id: int,
) -> None:
    delete_query = delete(ActiveRoomUsers).where(
        and_(
            ActiveRoomUsers.room_uuid == room_uuid,
            ActiveRoomUsers.user_id == user_id,
        )
    )
    await database.execute(delete_query)
    logger.info(f"Active user {user_id} deleted from room {room_uuid}")


async def get_room_active_users_from_db(room_uuid: str) -> list[UserDB]:
    select_query = select(ActiveRoomUsers).where(ActiveRoomUsers.room_uuid == room_uuid)
    active_users = await database.fetch_all(select_query)

    users = [
        UserDB(**dict(await get_user_by_id(active_user["user_id"])))  # type: ignore
        for active_user in active_users
    ]
    return users
