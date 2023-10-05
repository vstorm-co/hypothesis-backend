import uuid

from databases.interfaces import Record
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.sql.selectable import Select

from src.chat.enums import VisibilityChoices
from src.chat.schemas import (
    MessageDetails,
    RoomCreateInputDetails,
    RoomUpdateInputDetails,
)
from src.database import database, Message, Room


async def create_room_in_db(room_data: RoomCreateInputDetails) -> Record | None:
    insert_values = {
        "uuid": uuid.uuid4(),
        "user_id": room_data.user_id,
        "name": room_data.name,
        "share": room_data.share,
        "visibility": room_data.visibility or "just_me",
    }

    insert_query = insert(Room).values(**insert_values).returning(Room)
    return await database.fetch_one(insert_query)


def get_user_rooms_query(user_id) -> Select:
    select_query = select(Room).where(
        Room.user_id == user_id,
        Room.visibility == VisibilityChoices.JUST_ME,
    )

    return select_query


async def get_organization_rooms_from_db(organization_uuid: str) -> list[Record]:
    select_query = select(Room).where(
        Room.organization_uuid == organization_uuid,
        Room.visibility == VisibilityChoices.ORGANIZATION,
    )

    return await database.fetch_all(select_query)


async def get_room_by_id_from_db(room_id: str) -> Record | None:
    select_query = select(Room).where(Room.uuid == room_id)

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

    values_to_update["organization_uuid"] = update_data.organization_uuid
    values_to_update["share"] = update_data.share

    update_query = (
        update(Room)
        .where(
            Room.uuid == update_data.room_id, Room.user_id == update_data.user_id
        )
        .values(**values_to_update)
        .returning(Room)
    )

    try:
        return await database.fetch_one(update_query)
    except NoResultFound:
        return None


async def delete_room_from_db(room_id: str, user_id: int) -> Record | None:
    delete_query = delete(Room).where(Room.uuid == room_id, Room.user_id == user_id)
    return await database.fetch_one(delete_query)


async def get_messages_from_db(room_id: str) -> list[Record]:
    select_query = (
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at)
    )
    return await database.fetch_all(select_query)


async def create_message_in_db(user_message: MessageDetails) -> Record | None:
    insert_values = {
        "uuid": uuid.uuid4(),
        **user_message.model_dump(),
    }

    insert_query = insert(Message).values(insert_values).returning(Message)
    return await database.fetch_one(insert_query)
