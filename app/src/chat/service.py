import uuid
from datetime import datetime

import pytz
from databases.interfaces import Record
from sqlalchemy import and_, delete, func, insert, or_, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.sql.selectable import Select

from src.chat.enums import VisibilityChoices
from src.chat.schemas import (
    MessageDetails,
    RoomCreateInputDetails,
    RoomUpdateInputDetails,
)
from src.database import Message, Room, TokenUsage, database
from src.organizations.service import get_organizations_by_user_id_from_db
from src.token_usage.service import (
    create_token_usage_in_db,
    get_token_usage_input_from_message,
)


async def create_room_in_db(room_data: RoomCreateInputDetails) -> Record | None:
    insert_values = {
        "uuid": uuid.uuid4(),
        "user_id": room_data.user_id,
        "name": room_data.name,
        "share": room_data.share,
        "visibility": room_data.visibility or "just_me",
        "organization_uuid": room_data.organization_uuid,
    }

    insert_query = insert(Room).values(**insert_values).returning(Room)
    return await database.fetch_one(insert_query)


def get_user_rooms_where_clause(user_id: int) -> tuple:
    return (
        Room.user_id == user_id,
        Room.visibility == VisibilityChoices.JUST_ME,
    )


def get_user_rooms_query(user_id: int) -> Select:
    where_clause = get_user_rooms_where_clause(user_id)

    select_query = select(Room).where(
        *where_clause,
    )

    return select_query


def get_organizations_rooms_where_clause(organization_uuid: str | None) -> tuple:
    return (
        Room.organization_uuid == organization_uuid,
        Room.visibility == VisibilityChoices.ORGANIZATION,
    )


def get_organization_rooms_query(organization_uuid: str | None) -> Select:
    where_clause = get_organizations_rooms_where_clause(organization_uuid)

    select_query = select(Room).where(
        *where_clause,
    )

    return select_query


async def get_user_and_organization_rooms_query(user_id: int) -> Select:
    where_clause = (and_(*get_user_rooms_where_clause(user_id)),)

    # get user organizations
    organizations: list[Record] = await get_organizations_by_user_id_from_db(user_id)
    for organization in organizations:
        if not organization["uuid"]:
            continue

        where_clause += (  # type: ignore
            and_(*get_organizations_rooms_where_clause(organization["uuid"])),
        )

    select_query = select(Room).where(
        or_(*where_clause),
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


async def update_room_in_db(
    update_data: RoomUpdateInputDetails, update_share: bool = True
) -> Record | None:
    current_room = await get_room_by_id_from_db(update_data.room_id)
    if not current_room:
        return None

    values_to_update = dict(current_room)
    # do not update created_at and updated_at
    values_to_update.pop("created_at")
    values_to_update.pop("updated_at")

    if update_data.name:
        values_to_update["name"] = update_data.name
    if update_data.visibility:
        values_to_update["visibility"] = update_data.visibility

    values_to_update["organization_uuid"] = update_data.organization_uuid

    if update_share:
        values_to_update["share"] = update_data.share

    update_query = (
        update(Room)
        .where(Room.uuid == update_data.room_id, Room.user_id == update_data.user_id)
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


async def get_room_messages_from_db(room_id: str) -> list[Record]:
    select_query = (
        select(Message, TokenUsage)
        .where(Message.room_id == room_id, Message.token_usage_id == TokenUsage.id)
        .order_by(Message.created_at)
    )

    return await database.fetch_all(select_query)


async def get_room_messages_to_specific_message(
    room_id: str, message_id: str | None
) -> list[Record]:
    select_all_messages_query = (
        select(Message).where(Message.room_id == room_id).order_by(Message.updated_at)
    )
    if not message_id:
        return await database.fetch_all(select_all_messages_query)
    specific_message_select_query = select(Message).where(
        Message.uuid == message_id, Message.room_id == room_id
    )
    database_message = await database.fetch_one(specific_message_select_query)
    if not database_message:
        raise NoResultFound()
    message_date = database_message["updated_at"]
    message_date_unix = int(message_date.timestamp())
    select_older_than_specific_message_query = (
        select(Message)
        .where(Message.room_id == room_id)
        .where(
            or_(
                func.extract("epoch", Message.updated_at) <= message_date_unix,
                Message.uuid == message_id,
            )
        )
        .order_by(Message.created_at)
    )
    dates_from_db = await database.fetch_all(select_older_than_specific_message_query)
    return dates_from_db


async def create_message_in_db(user_message: MessageDetails) -> Record | None:
    token_usage_input = get_token_usage_input_from_message(user_message)
    token_usage: Record | None = await create_token_usage_in_db(token_usage_input)

    if not token_usage:
        return None

    insert_values = {
        "uuid": uuid.uuid4(),
        **user_message.model_dump(),
        "token_usage_id": token_usage["id"],
    }

    insert_query = insert(Message).values(insert_values).returning(Message)
    message = await database.fetch_one(insert_query)

    return message


async def delete_messages_from_db(
    room_id: str, date_from: datetime | None
) -> Record | None:
    message_date_unix: int = 0
    if not date_from:
        date_from = datetime.now()

    # set timezone to UTC if not set
    if not date_from.tzinfo:
        date_from = date_from.replace(tzinfo=pytz.UTC)

    # get unix timestamp
    if date_from:
        message_date_unix = int(date_from.timestamp())

    delete_query = delete(Message).where(
        and_(
            Message.room_id == room_id,
            func.extract("epoch", Message.updated_at) >= message_date_unix,
        )
    )
    return await database.fetch_one(delete_query)
