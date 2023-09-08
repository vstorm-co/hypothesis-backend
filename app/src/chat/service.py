import uuid

from databases.interfaces import Record
from sqlalchemy import delete, insert, or_, select, update
from sqlalchemy.exc import NoResultFound

from src.chat.enums import VisibilityChoices
from src.chat.schemas import (
    MessageDetails,
    RoomCreateInputDetails,
    RoomUpdateInputDetails,
)
from src.database import auth_user, database, message, room


async def create_room_in_db(room_data: RoomCreateInputDetails) -> Record | None:
    insert_values = {
        "uuid": uuid.uuid4(),
        "user_id": room_data.user_id,
        "name": room_data.name,
        "share": room_data.share,
        "visibility": room_data.visibility or "just_me",
    }

    insert_query = insert(room).values(**insert_values).returning(room)
    return await database.fetch_one(insert_query)


async def get_rooms_from_db(user_id) -> list[Record]:
    select_query = (
        select(room)
        .join(auth_user)
        .where(
            or_(
                room.c.user_id == user_id,
                room.c.visibility == VisibilityChoices.ORGANIZATION
                and auth_user.c.organization_uuid == room.c.organization_uuid,
            )
        )
    )

    return await database.fetch_all(select_query)


async def get_room_by_id_from_db(room_id: str) -> Record | None:
    select_query = select(room).where(room.c.uuid == room_id)

    try:
        return await database.fetch_one(select_query)
    except NoResultFound:
        return None


async def update_room_in_db(update_data: RoomUpdateInputDetails) -> Record | None:
    current_room = await get_room_by_id_from_db(update_data.room_id)
    if not current_room:
        return None

    values_to_update = dict(current_room)

    if update_data.name:
        values_to_update["name"] = update_data.name
    if update_data.visibility:
        values_to_update["visibility"] = update_data.visibility
    values_to_update["share"] = update_data.share

    update_query = (
        update(room)
        .where(
            room.c.uuid == update_data.room_id, room.c.user_id == update_data.user_id
        )
        .values(**values_to_update)
        .returning(room)
    )

    try:
        return await database.fetch_one(update_query)
    except NoResultFound:
        return None


async def delete_room_from_db(room_id: str, user_id: int) -> Record | None:
    delete_query = delete(room).where(room.c.uuid == room_id, room.c.user_id == user_id)
    return await database.fetch_one(delete_query)


async def get_messages_from_db(room_id: str) -> list[Record]:
    select_query = select(message).where(message.c.room_id == room_id)

    return await database.fetch_all(select_query)


async def create_message_in_db(user_message: MessageDetails) -> Record | None:
    insert_query = (
        insert(message)
        .values(
            {
                "uuid": uuid.uuid4(),
                "room_id": user_message.room_id,
                "created_by": user_message.created_by,
                "content": user_message.content,
            }
        )
        .returning(message)
    )
    return await database.fetch_one(insert_query)
