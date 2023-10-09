from datetime import datetime
from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter

from src.database import Template


class TemplateFilter(Filter):
    name: Optional[str] = None
    name__like: Optional[str] = None
    share: Optional[bool] = None
    created_at: Optional[str] = None
    created_at__gt: Optional[datetime] = None
    created_at__lt: Optional[datetime] = None
    created_at__gte: Optional[datetime] = None
    created_at__lte: Optional[datetime] = None
    user_id: Optional[int] = None
    organization_uuid: Optional[str] = None

    class Constants(Filter.Constants):
        model = Template
