import uuid

from databases.interfaces import Record
from sqlalchemy import delete, insert, or_, select, update
from sqlalchemy.exc import NoResultFound

from src.database import User, database, Template
from src.templates.enums import VisibilityChoices
from src.templates.schemas import TemplateCreateInputDetails, TemplateUpdateInputDetails


async def get_templates_from_db(user_id) -> list[Record]:
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
    return await database.fetch_all(select_query)


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

    if update_data.name:
        values_to_update["name"] = update_data.name
    if update_data.visibility:
        values_to_update["visibility"] = update_data.visibility
    if update_data.content:
        values_to_update["content"] = update_data.content
    values_to_update["share"] = update_data.share

    update_query = (
        update(Template)
        .where(
            Template.uuid == update_data.uuid,
            Template.user_id == update_data.user_id,
        )
        .values(**values_to_update)
        .returning(Template)
    )

    try:
        return await database.fetch_one(update_query)
    except NoResultFound:
        return None


async def delete_template_from_db(template_id: str, user_id: int) -> Record | None:
    delete_query = delete(Template).where(
        Template.uuid == template_id, Template.user_id == user_id
    )
    return await database.fetch_one(delete_query)
