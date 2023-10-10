import logging
import uuid
from typing import Tuple

from asyncpg import ForeignKeyViolationError, UniqueViolationError
from databases.interfaces import Record
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import NoResultFound

from src.auth.exceptions import InvalidCredentials
from src.auth.schemas import UserDB
from src.auth.service import is_user_admin_by_id
from src.database import (
    Organization,
    OrganizationAdmin,
    OrganizationUser,
    User,
    database,
)
from src.organizations.schemas import OrganizationCreate, OrganizationUpdate

logger = logging.getLogger(__name__)


# GET ORGANIZATIONS
async def get_organizations_from_db() -> list[Record] | None:
    select_query = select(Organization)

    return await database.fetch_all(select_query)


async def get_organizations_from_db_by_domain(domain: str) -> list[Record] | None:
    select_query = select(Organization).where(Organization.domain == domain)

    return await database.fetch_all(select_query)


async def get_organizations_by_user_id_from_db(user_id: int) -> list[Record] | None:
    select_query = (
        select(Organization)
        .join(OrganizationUser)
        .where(OrganizationUser.auth_user_id == user_id)
    )

    return await database.fetch_all(select_query)


# GET ORGANIZATION BY ID
async def get_organization_by_id_from_db(
    organization_uuid: str, user_id: int
) -> Record | None:
    where_clause = [
        Organization.uuid == organization_uuid,
    ]

    # if user is not admin, only return the organization
    # if it is the user's organization
    if not await is_user_admin_by_id(user_id):
        where_clause.append(User.id == user_id)

    try:
        select_query = select(Organization).where(*where_clause)
        return await database.fetch_one(select_query)
    except NoResultFound:
        # Handle the case where no result was found (no such organization)
        logger.warning(f"Organization with uuid {organization_uuid} not found")
        return None


async def get_users_from_organization_by_id_from_db(
    organization_uuid: str,
) -> list[Record] | None:
    # auth get auth users
    select_query = (
        select(User)
        .join(OrganizationUser)
        .where(OrganizationUser.organization_uuid == organization_uuid)
    )

    return await database.fetch_all(select_query)


async def get_admins_from_organization_by_id_from_db(
    organization_uuid: str,
) -> list[Record] | None:
    # auth get auth users
    select_query = (
        select(User)
        .join(OrganizationAdmin)
        .where(OrganizationAdmin.organization_uuid == organization_uuid)
    )

    return await database.fetch_all(select_query)


# CREATE ORGANIZATION
async def create_organization_in_db(
    organization_data: OrganizationCreate,
) -> Record | None:
    # add organization to organization table
    insert_values = {
        "uuid": uuid.uuid4(),
        **organization_data.model_dump(),
    }
    insert_query = insert(Organization).values(**insert_values).returning(Organization)
    try:
        return await database.fetch_one(insert_query)
    except UniqueViolationError:
        logger.info(f"Organization with name {organization_data.name} already exists")
        return None


async def get_or_create_organization_in_db(
    organization_data: OrganizationCreate,
) -> Tuple[Record | None, bool]:
    # check if organization exists
    select_query = select(Organization).where(
        Organization.name == organization_data.name
    )
    org = await database.fetch_one(select_query)
    if org:
        return org, False

    # add organization to organization table
    insert_values = {
        "uuid": uuid.uuid4(),
        **organization_data.model_dump(),
    }
    insert_query = insert(Organization).values(**insert_values).returning(Organization)
    return await database.fetch_one(insert_query), True


# UPDATE ORGANIZATION
async def update_organization_in_db(
    organization_uuid: str, user_id: int, organization_data: OrganizationUpdate
):
    # update organization in organization table
    update_values = {
        **organization_data.model_dump(),
    }

    where_clause = []
    if not await is_user_admin_by_id(user_id):
        where_clause.append(User.id == user_id)

    update_query = (
        update(Organization)
        .where(*where_clause)
        .values(**update_values)
        .returning(Organization)
    )

    try:
        return await database.fetch_one(update_query)
    except NoResultFound:
        # Organization not found
        logger.warning(f"Organization with uuid {organization_uuid} not found")
        return None


# DELETE ORGANIZATION
async def delete_organization_from_db(organization_uuid: str) -> Record | None:
    # check if organization exists
    select_query = select(Organization).where(Organization.uuid == organization_uuid)
    org = await database.fetch_one(select_query)
    if not org:
        logger.info(f"Organization with uuid {organization_uuid} does not exist")
        return None

    # delete organization from organization table
    delete_query = delete(Organization).where(Organization.uuid == organization_uuid)
    await database.execute(delete_query)
    logger.info(f"Organization uuid: {organization_uuid} deleted")
    return org


# ADD SPECIFIC
async def add_users_to_organization_in_db(
    organization_uuid: str, user_ids: list[int]
) -> None:
    insert_values = [
        {
            "organization_uuid": organization_uuid,
            "auth_user_id": user_id,
        }
        for user_id in user_ids
    ]

    insert_query = insert(OrganizationUser).values(insert_values)
    try:
        await database.execute(insert_query)
    except ForeignKeyViolationError:
        logger.info(f"Organization with uuid {organization_uuid} does not exist")
        return None
    except UniqueViolationError:
        logger.info("User already exists in organization")
        return None

    logger.info(f"Users {user_ids} added to organization uuid: {organization_uuid}")


async def add_admins_to_organization_in_db(
    organization_uuid: str, admin_ids: list[int]
) -> None:
    insert_values = [
        {
            "organization_uuid": organization_uuid,
            "auth_user_id": admin_id,
        }
        for admin_id in admin_ids
    ]

    insert_query = insert(OrganizationAdmin).values(insert_values)
    try:
        await database.execute(insert_query)
    except ForeignKeyViolationError:
        logger.warning(f"Organization with uuid {organization_uuid} does not exist")
        return None
    except UniqueViolationError:
        logger.info("User already exists in organization")
        return None

    logger.info(f"Admins {admin_ids} added to organization uuid: {organization_uuid}")


# DELETE ALL
async def remove_all_users_from_organization_in_db(organization_uuid: str) -> None:
    delete_query = delete(OrganizationUser).where(
        OrganizationUser.organization_uuid == organization_uuid
    )
    await database.execute(delete_query)
    logger.info(f"All users removed from organization uuid: {organization_uuid}")


async def remove_all_admins_from_organization_in_db(organization_uuid: str) -> None:
    delete_query = delete(OrganizationAdmin).where(
        OrganizationAdmin.organization_uuid == organization_uuid
    )
    await database.execute(delete_query)
    logger.info(f"All admins removed from organization uuid: {organization_uuid}")


# DELETE SPECIFIC
async def delete_users_from_organization_in_db(
    organization_uuid: str, user_ids: list[int]
) -> None:
    delete_query = delete(OrganizationUser).where(
        OrganizationUser.organization_uuid == organization_uuid,
        OrganizationUser.auth_user_id.in_(user_ids),
    )
    await database.execute(delete_query)
    logger.info(f"Users {user_ids} removed from organization uuid: {organization_uuid}")


async def delete_admins_from_organization_in_db(
    organization_uuid: str, admin_ids: list[int]
) -> None:
    delete_query = delete(OrganizationAdmin).where(
        OrganizationAdmin.organization_uuid == organization_uuid,
        OrganizationAdmin.auth_user_id.in_(admin_ids),
    )
    await database.execute(delete_query)
    logger.info(
        f"Admins {admin_ids} removed from organization uuid: {organization_uuid}"
    )


# ADD ORGANIZATION ON USER LOGIN (IF DOMAIN EXISTS)
async def get_or_create_organization_on_user_login(
    organization_details: OrganizationCreate, user: UserDB
) -> bool:
    org, created = await get_or_create_organization_in_db(organization_details)

    if not org:
        raise InvalidCredentials()

    # add user as a member of the organization and as an admin
    logger.info("Adding user to the organization...")
    await add_users_to_organization_in_db(org["uuid"], [user.id])
    logger.info("User added to the organization")
    if created:
        # if org is created, add user as admin
        logger.info("Adding user as admin to the organization...")
        await add_admins_to_organization_in_db(org["uuid"], [user.id])
        logger.info("User added as admin to the organization")

    return created
