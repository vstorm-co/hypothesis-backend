import logging
import uuid

from asyncpg import ForeignKeyViolationError, UniqueViolationError
from databases.interfaces import Record
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import NoResultFound

from src.database import auth_user, database, organization
from src.organizations.schemas import OrganizationCreate, OrganizationUpdate

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


async def update_organization_in_db(organization_uuid: str, organization_data: OrganizationUpdate):
    # update organization in organization table
    update_values = {
        **organization_data.model_dump(exclude={"organization_uuid"}),
    }

    update_query = (
        update(organization)
        .where(organization.c.uuid == organization_uuid)
        .values(**update_values)
        .returning(organization)
    )

    try:
        return await database.fetch_one(update_query)
    except NoResultFound:
        # Organization not found
        logger.warning(f"Organization with uuid {organization_uuid} not found")
        return None


async def delete_organization_from_db(organization_uuid: str):
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
