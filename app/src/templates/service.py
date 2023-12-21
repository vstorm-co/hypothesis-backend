import uuid

from databases.interfaces import Record
from sqlalchemy import and_, delete, insert, or_, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.sql.selectable import Select

from src.database import Template, User, database
from src.organizations.service import get_organizations_by_user_id_from_db
from src.templates.enums import VisibilityChoices
from src.templates.schemas import (
    TemplateCreateInputDetails,
    TemplateUpdateInputDetails,
    TemplateUpdateNameInput,
)


def get_templates_query(user_id) -> Select:
    select_query = (
        select(Template)
        .join(User)
        .where(
            or_(
                Template.user_id == user_id,
                Template.visibility == VisibilityChoices.ORGANIZATION
                and User.organization_uuid == Template.organization_uuid,
            )
        )
    )
    return select_query


def get_user_templates_where_clause(user_id: int) -> tuple:
    return (
        Template.user_id == user_id,
        Template.visibility == VisibilityChoices.JUST_ME,
    )


def get_user_templates_query(user_id: int) -> Select:
    where_clause = get_user_templates_where_clause(user_id)

    select_query = select(Template).where(
        *where_clause,
    )

    return select_query


def get_organizations_templates_where_clause(organization_uuid: str | None) -> tuple:
    return (
        Template.organization_uuid == organization_uuid,
        Template.visibility == VisibilityChoices.ORGANIZATION,
    )


def get_organization_templates_query(organization_uuid: str | None) -> Select:
    where_clause = get_organizations_templates_where_clause(organization_uuid)

    select_query = select(Template).where(
        *where_clause,
    )

    return select_query


async def get_user_and_organization_templates_query(user_id: int) -> Select:
    where_clause = (and_(*get_user_templates_where_clause(user_id)),)

    organizations: list[Record] = await get_organizations_by_user_id_from_db(user_id)
    for organization in organizations:
        if not organization["uuid"]:
            continue

        where_clause += (  # type: ignore
            and_(*get_organizations_templates_where_clause(organization["uuid"])),
        )

    select_query = select(Template).where(or_(*where_clause))

    return select_query


async def get_template_by_id_from_db(template_id: str) -> Record | None:
    select_query = select(Template).where(Template.uuid == template_id)

    try:
        return await database.fetch_one(select_query)
    except NoResultFound:
        return None


async def create_template_in_db(
    template_data: TemplateCreateInputDetails,
) -> Record | None:
    insert_values = {
        "uuid": uuid.uuid4(),
        "user_id": template_data.user_id,
        "name": template_data.name,
        "share": template_data.share,
        "visibility": template_data.visibility or "just_me",
        "content": template_data.content,
        "content_html": template_data.content_html,
    }

    insert_query = insert(Template).values(**insert_values).returning(Template)
    return await database.fetch_one(insert_query)


async def update_template_in_db(
    update_data: TemplateUpdateInputDetails,
) -> Record | None:
    current_template = await get_template_by_id_from_db(update_data.uuid)
    if not current_template:
        return None

    values_to_update = dict(current_template)
    # do not update created_at and updated_at
    values_to_update.pop("created_at")
    values_to_update.pop("updated_at")

    if update_data.name is not None:
        values_to_update["name"] = update_data.name
    values_to_update["visibility"] = update_data.visibility
    if update_data.content is not None:
        values_to_update["content"] = update_data.content
    if update_data.content_html is not None:
        values_to_update["content_html"] = update_data.content_html
    if update_data.organization_uuid:
        values_to_update["organization_uuid"] = update_data.organization_uuid
    if update_data.visibility == VisibilityChoices.JUST_ME:
        values_to_update["organization_uuid"] = None
    values_to_update["share"] = update_data.share

    update_query = (
        update(Template)
        .where(
            Template.uuid == update_data.uuid,
        )
        .values(**values_to_update)
        .returning(Template)
    )

    try:
        return await database.fetch_one(update_query)
    except NoResultFound:
        return None


async def update_template_name_in_db(
    template_id: str, update_data: TemplateUpdateNameInput
) -> Record | None:
    update_query = (
        update(Template)
        .where(
            Template.uuid == template_id,
        )
        .values(name=update_data.name)
        .returning(Template)
    )

    return await database.fetch_one(update_query)


async def delete_template_from_db(template_id: str, user_id: int) -> Record | None:
    delete_query = delete(Template).where(
        Template.uuid == template_id, Template.user_id == user_id
    )
    return await database.fetch_one(delete_query)
