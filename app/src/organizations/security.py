from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from src.auth.service import is_user_admin_by_id
from src.database import database, organization_admins, organizations_users


async def is_user_in_organization(user_id: int, organization_uuid: str) -> bool:
    # auth_user admin can do anything
    if await is_user_admin_by_id(user_id):
        return True

    try:
        select_query = select(organizations_users).where(
            organizations_users.c.user_id == user_id,
            organizations_users.c.organization_uuid == organization_uuid,
        )
        await database.fetch_one(select_query)
        return True
    except NoResultFound:
        return False


async def is_user_organization_admin(user_id: int, organization_uuid: str) -> bool:
    # look at line 9
    if await is_user_admin_by_id(user_id):
        return True

    if not await is_user_in_organization(user_id, organization_uuid):
        return False

    try:
        select_query = select(organization_admins).where(
            organization_admins.c.auth_user_id == user_id,
            organization_admins.c.organization_uuid == organization_uuid,
        )
        await database.fetch_one(select_query)
        return True
    except NoResultFound:
        return False
