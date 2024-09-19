from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from src.auth.service import is_user_admin_by_id
from src.database import OrganizationAdmin, OrganizationUser, database


async def is_user_in_organization(user_id: int, organization_uuid: str) -> bool:
    if not organization_uuid:
        return True

    # auth_user admin can do anything
    if await is_user_admin_by_id(user_id):
        return True

    try:
        select_query = select(OrganizationUser).where(
            OrganizationUser.auth_user_id == user_id,
            OrganizationUser.organization_uuid == organization_uuid,
        )
        record = await database.fetch_one(select_query)
        return True if record else False
    except NoResultFound:
        return False


async def is_user_organization_admin(user_id: int, organization_uuid: str) -> bool:
    # look at function `is_user_in_organization` description
    # if await is_user_admin_by_id(user_id):
    #     return True

    if not await is_user_in_organization(user_id, organization_uuid):
        return False

    try:
        select_query = select(OrganizationAdmin).where(
            OrganizationAdmin.auth_user_id == user_id,
            OrganizationAdmin.organization_uuid == organization_uuid,
        )
        record = await database.fetch_one(select_query)
        return True if record else False
    except NoResultFound:
        return False


async def check_admin_count_before_deletion(
    organization_uuid: str, admin_ids: list[int] | None
) -> bool:
    """
    Validates the deletion operation by comparing
    the counts of administrators
    selected for deletion with
    the total counts in the organization.
    """
    if not admin_ids:
        return True

    select_query = select(OrganizationAdmin).where(
        OrganizationAdmin.organization_uuid == organization_uuid
    )
    org_admins = await database.fetch_all(select_query)

    if len(admin_ids) == len(org_admins):
        return False

    return True


async def check_user_count_before_deletion(
    organization_uuid: str, user_ids: list[int] | None
) -> bool:
    """
    Validates the deletion operation by comparing
    the counts of users
    selected for deletion with
    the total counts in the organization.
    """
    if not user_ids:
        return True

    select_query = select(OrganizationUser).where(
        OrganizationUser.organization_uuid == organization_uuid
    )
    org_users = await database.fetch_all(select_query)

    if len(user_ids) == len(org_users):
        return False

    return True
