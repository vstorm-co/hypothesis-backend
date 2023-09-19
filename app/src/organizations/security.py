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
            organizations_users.c.auth_user_id == user_id,
            organizations_users.c.organization_uuid == organization_uuid,
        )
        record = await database.fetch_one(select_query)
        return True if record else False
    except NoResultFound:
        return False


async def is_user_organization_admin(user_id: int, organization_uuid: str) -> bool:
    # look at function `is_user_in_organization` description
    if await is_user_admin_by_id(user_id):
        return True

    if not await is_user_in_organization(user_id, organization_uuid):
        return False

    try:
        select_query = select(organization_admins).where(
            organization_admins.c.auth_user_id == user_id,
            organization_admins.c.organization_uuid == organization_uuid,
        )
        record = await database.fetch_one(select_query)
        return True if record else False
    except NoResultFound:
        return False


async def check_admin_user_count_before_deletion(
    organization_uuid: str, user_ids: list[int], admin_ids: list[int]
) -> bool:
    """
    Validates the deletion operation by comparing
    the counts of users or administrators
    selected for deletion with
    the total counts in the organization.
    """
    select_query = select(organizations_users).where(
        organizations_users.c.organization_uuid == organization_uuid
    )
    org_users = await database.fetch_all(select_query)

    select_query = select(organization_admins).where(
        organization_admins.c.organization_uuid == organization_uuid
    )
    org_admins = await database.fetch_all(select_query)

    if len(user_ids) == len(org_users):
        return False

    if len(admin_ids) == len(org_admins):
        return False

    return True
