import uuid

from databases.interfaces import Record
from sqlalchemy import insert, select

from src.chat.schemas import Message
from src.database import database, message, room


async def create_room_in_db(user_id) -> Record | None:
    insert_query = (
        insert(room).values({"uuid": uuid.uuid4(), "user_id": user_id}).returning(room)
    )
    return await database.fetch_one(insert_query)


async def get_room_from_db(user_id) -> Record | None:
    select_query = select(room).where(room.c.user_id == user_id)

    return await database.fetch_all(select_query)


async def get_messages_from_db(room_id: str) -> Record | None:
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
