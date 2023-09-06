import uuid

from databases.interfaces import Record
from sqlalchemy import delete, insert, select, update

from src.database import auth_user, database, organization
from src.organizations.schemas import (
    AddUserInput,
    OrganizationChange,
    OrganizationCreate,
    OrganizationDelete,
)

# from src.organizations import service


async def get_organizations_from_db(user_id: int) -> Record | None:
    select_query = select(organization).join(auth_user).where(auth_user.c.id == user_id)

    return await database.fetch_all(select_query)


async def get_organization_by_id_from_db(organization_uuid: str) -> Record | None:
    select_query = select(organization).where(organization.c.uuid == organization_uuid)
    return await database.fetch_one(select_query)


async def create_organization_in_db(
    organization_data: OrganizationCreate,
) -> Record | None:
    insert_query = (
        insert(organization)
        .values({"uuid": uuid.uuid4(), "name": organization_data.name})
        .returning(organization)
    )
    return await database.fetch_one(insert_query)


async def update_organization_in_db(organization_data: OrganizationChange):
    update_query = (
        update(organization)
        .where(organization.c.uuid == organization_data.organization_uuid)
        .values({"name": organization_data.name})
        .returning(organization)
    )

    return await database.fetch_one(update_query)


async def delete_organization_from_db(organization_data: OrganizationDelete):
    update_query = update(auth_user).where(
        auth_user.c.organization_uuid == organization_data.organization_uuid
    )
    await database.fetch_all(update_query)

    delete_query = delete(organization).where(
        organization.c.uuid == organization_data.organization_uuid
    )
    await database.execute(delete_query)


async def add_user_to_organization_in_db(data: AddUserInput) -> Record | None:
    update_query = (
        update(auth_user)
        .where(auth_user.c.organization_uuid == data.user_id)
        .values({"organization_uuid": data.organization_uuid})
    )
    return await database.fetch_one(update_query)
