from fastapi_pagination import Page
from fastapi_pagination.ext.databases import paginate
from sqlalchemy import select

from src.chat.enums import VisibilityChoices
from src.chat.schemas import RoomDB
from src.database import database, room


async def paginate_rooms(user_id: int) -> Page[RoomDB]:
    select_query = select(room).where(
        room.c.user_id == user_id,
        room.c.visibility == VisibilityChoices.JUST_ME,
    )
    return await paginate(database, select_query)
