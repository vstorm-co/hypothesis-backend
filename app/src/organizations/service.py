import logging
import uuid

from asyncpg import ForeignKeyViolationError, UniqueViolationError
from databases.interfaces import Record
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import NoResultFound

from src.auth.service import is_user_admin_by_id
from src.database import (
    auth_user,
    database,
    organization,
    organization_admins,
    organizations_users,
)
from src.organizations.schemas import (
    OrganizationCreate,
    OrganizationUpdate,
    SetUserOrganizationInput,
)

logger = logging.getLogger(__name__)


async def get_organizations_from_db() -> list[Record] | None:
    select_query = select(organization)

    return await database.fetch_all(select_query)


async def get_organization_by_id_from_db(
    organization_uuid: str, user_id: int
) -> Record | None:
    where_clause = [
        organization.c.uuid == organization_uuid,
    ]

    # if user is not admin, only return the organization
    # if it is the user's organization
    if not is_user_admin_by_id(user_id):
        where_clause.append(auth_user.c.id == user_id)

    try:
        select_query = select(organization).where(*where_clause)
        return await database.fetch_one(select_query)
    except NoResultFound:
        # Handle the case where no result was found (no such organization)
        logger.warning(f"Organization with uuid {organization_uuid} not found")
        return None


async def create_organization_in_db(
    organization_data: OrganizationCreate,
) -> Record | None:
    # add organization to organization table
    insert_values = {
        "uuid": uuid.uuid4(),
        **organization_data.model_dump(),
    }
    insert_query = insert(organization).values(**insert_values).returning(organization)
    try:
        return await database.fetch_one(insert_query)
    except UniqueViolationError:
        logger.info(f"Organization with name {organization_data.name} already exists")
        return None


async def update_organization_in_db(
    organization_uuid: str, user_id: int, organization_data: OrganizationUpdate
):
    # update organization in organization table
    update_values = {
        **organization_data.model_dump(),
    }

    where_clause = []
    if not is_user_admin_by_id(user_id):
        where_clause.append(auth_user.c.id == user_id)

    update_query = (
        update(organization)
        .where(*where_clause)
        .values(**update_values)
        .returning(organization)
    )

    try:
        return await database.fetch_one(update_query)
    except NoResultFound:
        # Organization not found
        logger.warning(f"Organization with uuid {organization_uuid} not found")
        return None


async def delete_organization_from_db(
    organization_uuid: str, user_id: int
) -> Record | None:
    # check if organization exists
    select_query = select(organization).where(organization.c.uuid == organization_uuid)
    org = await database.fetch_one(select_query)
    if not org:
        logger.info(f"Organization with uuid {organization_uuid} does not exist")
        return None

    # delete organization from organization table
    delete_query = delete(organization).where(organization.c.uuid == organization_uuid)
    await database.execute(delete_query)
    logger.info(f"Organization uuid: {organization_uuid} deleted")
    return org


async def add_users_to_organization_in_db(
    data: SetUserOrganizationInput,
) -> Record | None:
    org_users = None

    for user_id in data.user_ids:
        insert_values = {
            "organization_uuid": data.organization_uuid,
            "auth_user_id": user_id,
        }

        org_users = await insert_users_to_org(insert_values)

    for admin_id in data.admin_ids:
        insert_values = {
            "organization_uuid": data.organization_uuid,
            "auth_user_id": admin_id,
        }

        org_users = await insert_users_to_org(insert_values, admins=True)

    return org_users


async def insert_users_to_org(values: dict, admins: bool = False) -> Record | None:
    db_table = organization_admins if admins else organizations_users

    insert_query = insert(db_table).values(**values).returning(db_table)
    try:
        org_users = await database.fetch_one(insert_query)
    except ForeignKeyViolationError:
        # Organization not found
        return None
    except UniqueViolationError:
        # Handle the case of a duplicate entry
        logger.warning("User already exists in organization")
        return None

    return org_users
