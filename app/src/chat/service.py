import uuid

from databases.interfaces import Record
from sqlalchemy import insert, select, update

from src.chat.schemas import Message, RoomCreateWithUserId, RoomUpdateWithId
from src.database import database, message, room


async def create_room_in_db(room_data: RoomCreateWithUserId) -> Record | None:
    insert_query = (
        insert(room)
        .values(
            {"uuid": uuid.uuid4(), "user_id": room_data.user_id, "name": room_data.name}
        )
        .returning(room)
    )
    return await database.fetch_one(insert_query)


async def update_room_in_db(room_data: RoomUpdateWithId) -> Record | None:
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


async def get_messages_from_db(room_id: str) -> list[Record]:
    select_query = select(message).where(message.c.room_id == room_id)

    return await database.fetch_all(select_query)


async def get_all_rooms_from_db() -> Record | None:
    select_query = select(room)

    return await database.fetch_one(select_query)


async def create_message_in_db(user_message: Message):
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
