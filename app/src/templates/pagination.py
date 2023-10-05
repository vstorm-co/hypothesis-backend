from fastapi_pagination import Page
from fastapi_pagination.ext.databases import paginate
from sqlalchemy import or_, select

from src.chat.enums import VisibilityChoices
from src.database import auth_user, database, template
from src.templates.schemas import TemplateDB


async def paginate_templates(user_id) -> Page[TemplateDB]:
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
    return await paginate(database, select_query)
