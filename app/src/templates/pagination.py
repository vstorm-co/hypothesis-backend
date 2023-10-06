from fastapi_pagination import Page
from fastapi_pagination.ext.databases import paginate
from sqlalchemy.sql.selectable import Select

from src.database import database
from src.templates.schemas import TemplateDB


async def paginate_templates(query: Select) -> Page[TemplateDB]:
    return await paginate(database, query)
