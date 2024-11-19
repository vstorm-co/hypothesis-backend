import uuid
from datetime import datetime
from logging import getLogger

import pytz
from databases.interfaces import Record
from sqlalchemy import (
    Integer,
    and_,
    any_,
    case,
    cast,
    delete,
    func,
    insert,
    or_,
    select,
    update,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.sql.selectable import Select

from src.chat.enums import VisibilityChoices
from src.chat.schemas import (
    MessageDetails,
    RoomCreateInputDetails,
    RoomUpdateInputDetails,
)
from src.database import ActiveRoomUsers, Message, Room, TokenUsage, database
from src.organizations.service import get_organizations_by_user_id_from_db
from src.token_usage.service import (
    create_token_usage_in_db,
    get_token_usage_input_from_message,
    update_token_usage_in_db,
)

logger = getLogger(__name__)


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


# async def get_user_and_organization_rooms_query(user_id: int) -> Select:
#     where_clause = (and_(*get_user_rooms_where_clause(user_id)),)
#
#     # get user organizations
#     organizations: list[Record] = await get_organizations_by_user_id_from_db(user_id)
#     for organization in organizations:
#         if not organization["uuid"]:
#             continue
#
#         where_clause += (  # type: ignore
#             and_(*get_organizations_rooms_where_clause(organization["uuid"])),
#         )
#
#     # Define the subquery to fetch active user IDs for each room
#     subquery = (
#         select(
#             ActiveRoomUsers.room_uuid,
#             func.array_agg(ActiveRoomUsers.user_id).label("active_user_ids"),
#         ).group_by(ActiveRoomUsers.room_uuid)
#     ).subquery()
#
#     # Construct the main select query
#     select_query = (
#         select(Room, subquery.c.active_user_ids)
#         .where(
#             or_(*where_clause),
#         )
#         .select_from(Room)
#         .outerjoin(subquery, Room.uuid == subquery.c.room_uuid)
#         # order by the number of active users descending
#         # by getting length of active_user_ids array and casting
#         # it to integer to be able to order by it
#         .order_by(
#             cast(
#                 func.coalesce(func.array_length(subquery.c.active_user_ids, 1), 0),
#                 Integer,
#             ).desc()
#         )
#     )
#
#     return select_query
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

    # Define the subquery to fetch active user IDs for each room
    subquery = (
        select(
            ActiveRoomUsers.room_uuid,
            func.array_agg(ActiveRoomUsers.user_id).label("active_user_ids"),
        ).group_by(ActiveRoomUsers.room_uuid)
    ).subquery()

    # Construct the main select query
    select_query = (
        select(Room, subquery.c.active_user_ids)
        .where(
            or_(*where_clause),
        )
        .select_from(Room)
        .outerjoin(subquery, Room.uuid == subquery.c.room_uuid)
        # order by whether the user is in the room first, then by number of active users
        .order_by(
            case(
                (
                    user_id == any_(subquery.c.active_user_ids),
                    "0",
                ),  # Cast the output to string
                else_="1",  # Cast the else output to string
            ),
            cast(
                func.coalesce(func.array_length(subquery.c.active_user_ids, 1), 0),
                Integer,
            ).desc(),
        )
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
    update_data: RoomUpdateInputDetails,
    update_share: bool = True,
    update_visibility: bool = True,
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

    if update_visibility:
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
    message_date = message_date.astimezone(pytz.utc).replace(tzinfo=None)
    select_older_than_specific_message_query = (
        select(Message)
        .where(Message.room_id == room_id)
        .where(
            or_(
                Message.updated_at <= message_date,
                Message.uuid == message_id,
            )
        )
        .order_by(Message.created_at)
    )
    messages_db = await database.fetch_all(select_older_than_specific_message_query)
    return messages_db


async def get_message_by_id_from_db(message_id: str) -> Record | None:
    select_query = select(Message).where(Message.uuid == message_id)

    try:
        return await database.fetch_one(select_query)
    except NoResultFound:
        return None


async def create_message_in_db(user_message: MessageDetails) -> Record | None:
    token_usage_input = get_token_usage_input_from_message(user_message)
    token_usage: Record | None = await create_token_usage_in_db(token_usage_input)

    if not token_usage:
        logger.error("Token usage could not be created")
        return None

    insert_values = {
        "uuid": uuid.uuid4(),
        **user_message.model_dump(),
        "token_usage_id": token_usage["id"],
    }

    insert_query = insert(Message).values(insert_values).returning(Message)
    message = await database.fetch_one(insert_query)

    return message


async def update_message_in_db(
    message_uuid: str, message_data: MessageDetails
) -> Record | None:
    current_message: Record | None = await get_message_by_id_from_db(message_uuid)
    if not current_message:
        return None

    # update token usage
    token_usage_input = get_token_usage_input_from_message(message_data)
    await update_token_usage_in_db(current_message["token_usage_id"], token_usage_input)

    update_query = (
        update(Message)
        .where(Message.uuid == message_uuid)
        .values(message_data.model_dump())
        .returning(Message)
    )

    try:
        return await database.fetch_one(update_query)
    except NoResultFound:
        return None


async def delete_messages_from_db(
    room_id: str, date_from: datetime | None
) -> Record | None:
    if not date_from:
        date_from = datetime.now()

    # set timezone to UTC if not set
    if not date_from.tzinfo:
        date_from = date_from.replace(tzinfo=pytz.UTC)

    date_from = date_from.astimezone(pytz.utc)
    date_from = date_from.replace(tzinfo=None)

    delete_query = delete(Message).filter(
        and_(
            Message.room_id == room_id,
            Message.updated_at >= date_from,
        )
    )
    return await database.fetch_one(delete_query)


async def get_non_deleted_messages(room_id: str, date_from: datetime | None) -> list[Record]:
    if not date_from:
        date_from = datetime.now()

    if not date_from.tzinfo:
        date_from = date_from.replace(tzinfo=pytz.UTC)

    date_from = date_from.astimezone(pytz.utc).replace(tzinfo=None)

    query = select(Message).filter(
        and_(
            Message.room_id == room_id,
            Message.updated_at < date_from,
        )
    )
    return await database.fetch_all(query)


async def delete_user_message_from_db(message_id: str, user_id: int) -> Record | None:
    delete_query = delete(Message).where(
        Message.uuid == message_id, Message.user_id == user_id
    )
    return await database.fetch_one(delete_query)
