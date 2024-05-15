from fastapi_pagination import Page
from sqlalchemy.sql.selectable import Select

from src.database import database
from src.pagination_utils import paginate
from src.templates.schemas import TemplateDB


async def paginate_templates(query: Select) -> Page[TemplateDB]:
    return await paginate(database, query)
