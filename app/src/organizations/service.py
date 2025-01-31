import logging
import uuid
from typing import Tuple

from asyncpg import ForeignKeyViolationError, UniqueViolationError
from databases.interfaces import Record
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import NoResultFound

from src.auth.exceptions import InvalidCredentials
from src.auth.schemas import UserDB, UserDBNoSecrets
from src.auth.service import get_user_by_email
from src.database import (
    Organization,
    OrganizationAdmin,
    OrganizationUser,
    User,
    database,
)
from src.organizations.schemas import (
    OrganizationCreate,
    OrganizationCreateDetails,
    OrganizationPictureUpdate,
    OrganizationUpdate,
)

logger = logging.getLogger(__name__)


# GET ORGANIZATIONS
async def get_organizations_from_db() -> list[Record] | None:
    select_query = select(Organization)

    return await database.fetch_all(select_query)


async def get_organizations_from_db_by_domain(domain: str) -> list[Record] | None:
    select_query = select(Organization).where(Organization.domain == domain)

    return await database.fetch_all(select_query)


async def get_organizations_by_user_id_from_db(user_id: int) -> list[Record]:
    select_query = (
        select(Organization)
        .join(OrganizationUser)
        .where(OrganizationUser.auth_user_id == user_id)
    )

    return await database.fetch_all(select_query)


# GET ORGANIZATION BY ID
async def get_organization_by_id_from_db(organization_uuid: str) -> Record | None:
    where_clause = [
        Organization.uuid == organization_uuid,
    ]

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


async def get_or_create_organization_in_db_by_domain_name(
    organization_data: OrganizationCreateDetails,
) -> Tuple[Record | None, bool]:
    # check if organization exists
    select_query = select(Organization).where(
        Organization.domain == organization_data.domain
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
    organization_uuid: str, organization_data: OrganizationUpdate
):
    where_clause = [
        Organization.uuid == organization_uuid,
    ]

    update_query = (
        update(Organization)
        .where(*where_clause)
        .values(**organization_data.model_dump())
        .returning(Organization)
    )

    try:
        return await database.fetch_one(update_query)
    except NoResultFound:
        # Organization not found
        logger.warning(f"Organization with uuid {organization_uuid} not found")
        return None


async def update_organization_picture(
    organization_uuid: str, picture_data: OrganizationPictureUpdate
):
    where_clause = [
        Organization.uuid == organization_uuid,
    ]

    update_query = (
        update(Organization)
        .where(*where_clause)
        .values(**picture_data.model_dump())
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

    for value in insert_values:
        insert_query = insert(OrganizationUser).values(value)
        logger.info(
            f"""Adding user {value['auth_user_id']}
            to organization uuid: {organization_uuid}"""
        )
        try:
            await database.execute(insert_query)
        except ForeignKeyViolationError:
            logger.warning(f"Organization with uuid {organization_uuid} does not exist")
            continue
        except UniqueViolationError:
            logger.info(f"User {value['auth_user_id']} already exists in organization")
            continue

    logger.info(f"Adding users to organization uuid: {organization_uuid} finished")


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

    for value in insert_values:
        insert_query = insert(OrganizationAdmin).values(value)
        logger.info(
            f"""Adding admin {value['auth_user_id']}
            to organization uuid: {organization_uuid}"""
        )
        try:
            await database.execute(insert_query)
        except ForeignKeyViolationError:
            logger.warning(f"Organization with uuid {organization_uuid} does not exist")
            continue
        except UniqueViolationError:
            logger.info(f"User {value['auth_user_id']} already exists in organization")
            continue

    logger.info(f"Adding admins to organization uuid: {organization_uuid} finished")


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
    organization_details: OrganizationCreateDetails, user: UserDB
) -> bool:
    org, created = await get_or_create_organization_in_db_by_domain_name(
        organization_details
    )

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


async def add_users_to_organization_in_db_by_emails(
    organization_uuid: str,
    emails: list[str],
    as_admin: bool = False,
) -> str:
    user_ids = []
    emails_added = []
    emails_skipped = []
    for email in emails:
        user_db = await get_user_by_email(email)
        if not user_db:
            # SO FAR
            # in future we will handle it by sending an invitation
            logger.warning(f"User with email {email} not found")
            emails_skipped.append(email)
            continue
        emails_added.append(email)
        user = UserDBNoSecrets(**dict(user_db))
        user_ids.append(user.id)

    await add_users_to_organization_in_db(organization_uuid, user_ids)
    if as_admin:
        await add_admins_to_organization_in_db(organization_uuid, user_ids)

    return f"""Users: {','.join(emails_added)}
    added to organization uuid: {organization_uuid}
    emails skipped: {','.join(emails_skipped)}"""
