import logging

from sqlalchemy import delete

from src.database import Organization, Room, Template, User, database

logger = logging.getLogger(__name__)


# TODO Delete this
async def clean_entire_database() -> None:
    await database.fetch_all(delete(Organization))
    await database.fetch_all(delete(Room))
    await database.fetch_all(delete(Template))
    await database.fetch_all(delete(User))
    return None
