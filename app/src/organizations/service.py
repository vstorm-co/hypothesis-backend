import logging
import uuid

from asyncpg import ForeignKeyViolationError
from databases.interfaces import Record
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import NoResultFound

from src.database import auth_user, database, organization
from src.organizations.schemas import OrganizationChange, OrganizationCreate

logger = logging.getLogger(__name__)


async def get_organizations_from_db() -> list[Record] | None:
    select_query = select(organization)

    return await database.fetch_all(select_query)


async def get_user_organization_by_id_from_db(
    organization_uuid: str, user_id: int
) -> Record | None:
    try:
        select_query = select(organization).where(
            organization.c.uuid == organization_uuid, auth_user.c.id == user_id
        )
        return await database.fetch_one(select_query)
    except NoResultFound:
        # Handle the case where no result was found (no such organization)
        return None


async def create_organization_in_db(
    organization_data: OrganizationCreate,
) -> Record | None:
    # check if organization already exists
    select_query = select(organization).where(
        organization.c.name == organization_data.name
    )
    org = await database.fetch_one(select_query)
    if org:
        logger.info("Organization already exists")
        return None

    # add organization to organization table
    insert_values = {
        "uuid": uuid.uuid4(),
        "name": organization_data.name,
    }
    insert_query = insert(organization).values(**insert_values).returning(organization)
    return await database.fetch_one(insert_query)


async def update_organization_in_db(organization_data: OrganizationChange):
    # update organization in organization table
    update_values = {
        "name": organization_data.name,
    }

    update_query = (
        update(organization)
        .where(organization.c.uuid == organization_data.organization_uuid)
        .values(**update_values)
        .returning(organization)
    )

    logger.info("Organization updated")
    try:
        return await database.fetch_one(update_query)
    except NoResultFound:
        # Organization not found
        return None


async def delete_organization_from_db(organization_uuid: str):
    # check if organization exists
    select_query = select(organization).where(organization.c.uuid == organization_uuid)
    org = await database.fetch_one(select_query)
    if not org:
        logger.info("Organization does not exist")
        return None

    # delete organization from auth_user table
    update_query = (
        update(auth_user)
        .where(auth_user.c.organization_uuid == organization_uuid)
        .values({"organization_uuid": None})
    )
    await database.fetch_all(update_query)
    logger.info("Organization deleted from auth_user table")

    # delete organization from organization table
    delete_query = delete(organization).where(organization.c.uuid == organization_uuid)
    await database.execute(delete_query)
    logger.info("Organization deleted")
    return org


async def set_user_organization_in_db(
    organization_uuid: str, user_id: int
) -> Record | None:
    select_query = select(auth_user).where(auth_user.c.id == user_id)
    user = await database.fetch_one(select_query)
    if user and user["organization_uuid"] is not None:
        logger.info("User already has an organization")
        logger.info("Changing user organization")

    # add organization to auth_user table
    insert_query = (
        update(auth_user)
        .where(auth_user.c.id == user_id)
        .values({"organization_uuid": organization_uuid})
        .returning(auth_user)
    )
    try:
        return await database.fetch_one(insert_query)
    except ForeignKeyViolationError:
        # Organization not found
        return None
