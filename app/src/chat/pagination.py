from fastapi_pagination import Page
from fastapi_pagination.ext.databases import paginate
from sqlalchemy.sql.selectable import Select

from src.chat.schemas import RoomDB
from src.database import database


async def paginate_rooms(query: Select) -> Page[RoomDB]:
    return await paginate(database, query)
