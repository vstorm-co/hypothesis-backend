from datetime import datetime
from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy.sql import Select
from sqlalchemy import cast, Text, select, or_, String, and_
from src.chat.enums import VisibilityChoices
from src.chat.service import (
    get_organization_rooms_query,
    get_user_and_organization_rooms_query,
    get_user_rooms_query,
)
from src.database import Room, Message


class RoomFilter(Filter):
    name: Optional[str] = None
    name__like: Optional[str] = None
    # name__ilike: Optional[str] = None
    share: Optional[bool] = None
    created_at: Optional[str] = None
    created_at__gt: Optional[datetime] = None
    created_at__lt: Optional[datetime] = None
    created_at__gte: Optional[datetime] = None
    created_at__lte: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updated_at__gt: Optional[datetime] = None
    updated_at__lt: Optional[datetime] = None
    updated_at__gte: Optional[datetime] = None
    updated_at__lte: Optional[datetime] = None
    user_id: Optional[int] = None

    class Constants(Filter.Constants):
        model = Room
        ordering_field_name = "order_by"

    order_by: Optional[list[str]] = [
        "visibility",
    ]


# custom filters
async def get_query_filtered_by_visibility(
        visibility: str | None,
        user_id: int,
        organization_uuid: str | None,
        search_query: str | None = None,
) -> Select:
    base_columns = [
        Room.uuid,
        Room.name,
        Room.share,
        Room.visibility,
        Room.created_at,
        Room.updated_at,
        Room.user_id,
        Room.organization_uuid
    ]

    match visibility:
        case VisibilityChoices.JUST_ME:
            base_query = get_user_rooms_query(user_id)
        case VisibilityChoices.ORGANIZATION:
            base_query = get_organization_rooms_query(organization_uuid)
        case None:
            base_query = await get_user_and_organization_rooms_query(user_id)

    if not search_query:
        return base_query

    search_pattern = f"%{search_query}%"

    message_subquery = (
        select(Message.room_id)
        .join(Room, Room.uuid == Message.room_id)
        .where(
            or_(
                Message.content.ilike(search_pattern),
                Message.content_html.ilike(search_pattern),
                cast(Message.content_dict, String).ilike(search_pattern)
            )
        )
    )

    match visibility:
        case VisibilityChoices.JUST_ME:
            message_subquery = message_subquery.where(Room.user_id == user_id)
        case VisibilityChoices.ORGANIZATION:
            message_subquery = message_subquery.where(Room.organization_uuid == organization_uuid)
        case None:
            message_subquery = message_subquery.where(
                or_(
                    Room.user_id == user_id,
                    Room.organization_uuid == organization_uuid
                )
            )

    final_query = select(*base_columns).where(
        or_(
            and_(
                Room.name.ilike(search_pattern),
                Room.uuid.in_(select(Room.uuid).select_from(base_query.subquery()))
            ),
            Room.uuid.in_(message_subquery)
        )
    )

    return final_query
