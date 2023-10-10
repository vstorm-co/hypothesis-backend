from datetime import datetime
from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy.sql import Select

from src.chat.enums import VisibilityChoices
from src.chat.service import (
    get_organization_rooms_query,
    get_user_and_organization_rooms_query,
    get_user_rooms_query,
)
from src.database import Room


class RoomFilter(Filter):
    name: Optional[str] = None
    name__like: Optional[str] = None
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
def get_query_filtered_by_visibility(  # type: ignore
    visibility: str | None,
    user_id: int,
    organization_uuid: str | None,
) -> Select:
    match visibility:
        case VisibilityChoices.JUST_ME:
            return get_user_rooms_query(user_id)
        case VisibilityChoices.ORGANIZATION:
            return get_organization_rooms_query(organization_uuid)
        case None:
            return get_user_and_organization_rooms_query(user_id, organization_uuid)
