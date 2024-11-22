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
        message_content_ilike: str | None = None,
) -> Select:
    query: Select = Room.__table__.select()

    match visibility:
        case VisibilityChoices.JUST_ME:
            query = get_user_rooms_query(user_id)
        case VisibilityChoices.ORGANIZATION:
            query = get_organization_rooms_query(organization_uuid)
        case None:
            query = await get_user_and_organization_rooms_query(user_id)

    if message_content_ilike:
        query = query.join(Message, Message.room_id == Room.uuid)

        filter_conditions = or_(
            Message.content.ilike(f"%{message_content_ilike}%"),
            Message.content_dict.cast(String).ilike(f"%{message_content_ilike}%"),
            Message.content_html.ilike(f"%{message_content_ilike}%"),
            Room.name.ilike(f"%{message_content_ilike}%")
        )

        query = query.filter(filter_conditions)

    return query
