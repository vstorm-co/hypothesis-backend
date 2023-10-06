import uuid

from databases.interfaces import Record
from sqlalchemy import delete, insert, or_, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.sql.selectable import Select

from src.database import auth_user, database, template
from src.templates.enums import VisibilityChoices
from src.templates.schemas import TemplateCreateInputDetails, TemplateUpdateInputDetails


def get_templates_query(user_id) -> Select:
    select_query = (
        select(template)
        .join(auth_user)
        .where(
            or_(
                template.c.user_id == user_id,
                template.c.visibility == VisibilityChoices.ORGANIZATION
                and auth_user.c.organization_uuid == template.c.organization_uuid,
            )
        )
    )
    return select_query


async def get_template_by_id_from_db(template_id: str) -> Record | None:
    select_query = select(template).where(template.c.uuid == template_id)

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
    }

    insert_query = insert(template).values(**insert_values).returning(template)
    return await database.fetch_one(insert_query)


async def update_template_in_db(
    update_data: TemplateUpdateInputDetails,
) -> Record | None:
    current_template = await get_template_by_id_from_db(update_data.uuid)
    if not current_template:
        return None

    values_to_update = dict(current_template)

    if update_data.name:
        values_to_update["name"] = update_data.name
    if update_data.visibility:
        values_to_update["visibility"] = update_data.visibility
    if update_data.content:
        values_to_update["content"] = update_data.content
    values_to_update["share"] = update_data.share

    update_query = (
        update(template)
        .where(
            template.c.uuid == update_data.uuid,
            template.c.user_id == update_data.user_id,
        )
        .values(**values_to_update)
        .returning(template)
    )

    try:
        return await database.fetch_one(update_query)
    except NoResultFound:
        return None


async def delete_template_from_db(template_id: str, user_id: int) -> Record | None:
    delete_query = delete(template).where(
        template.c.uuid == template_id, template.c.user_id == user_id
    )
    return await database.fetch_one(delete_query)
