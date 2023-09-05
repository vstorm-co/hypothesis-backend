import uuid

from databases.interfaces import Record
from sqlalchemy import delete, insert, select, update

from src.chat.schemas import (
    MessageDetails,
    RoomCreateInputDetails,
    RoomUpdateInputDetails,
)
from src.database import database, message, room


async def create_room_in_db(room_data: RoomCreateInputDetails) -> Record | None:
    insert_query = (
        insert(room)
        .values(
            {"uuid": uuid.uuid4(), "user_id": room_data.user_id, "name": room_data.name}
        )
        .returning(room)
    )
    return await database.fetch_one(insert_query)


async def update_room_in_db(room_data: RoomUpdateInputDetails) -> Record | None:
    update_query = (
        update(room)
        .where(room.c.uuid == room_data.room_id)
        .values({"name": room_data.name})
        .returning(room)
    )
    return await database.fetch_one(update_query)


async def get_rooms_from_db(user_id) -> list[Record]:
    select_query = select(room).where(room.c.user_id == user_id)

    return await database.fetch_all(select_query)


async def get_room_by_id_from_db(room_id: str, user_id: int) -> Record | None:
    select_query = select(room).where(room.c.uuid == room_id, room.c.user_id == user_id)

    return await database.fetch_one(select_query)


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
