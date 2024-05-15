from __future__ import annotations

__all__ = ["paginate"]

from datetime import datetime
from typing import Any, List, Optional, Sequence

from databases import Database
from fastapi_pagination.api import apply_items_transformer, create_page
from fastapi_pagination.bases import AbstractParams
from fastapi_pagination.ext.sqlalchemy import paginate_query
from fastapi_pagination.types import AdditionalData, AsyncItemsTransformer
from fastapi_pagination.utils import verify_params
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.sql import Select

from src.datetime_utils import aware_datetime_field


def enrich_paginated_items(page_items: Sequence[BaseModel]):
    for item in page_items:
        for field_attr in item.model_fields:
            room_attr = item.__getattribute__(field_attr)

            if isinstance(room_attr, datetime):
                set_value = aware_datetime_field(room_attr)
                item.__setattr__(field_attr, set_value)


async def paginate(
    db: Database,
    query: Select,
    params: Optional[AbstractParams] = None,
    *,
    transformer: Optional[AsyncItemsTransformer] = None,
    additional_data: Optional[AdditionalData] = None,
    convert_to_mapping: bool = True,
) -> Any:
    params, raw_params = verify_params(params, "limit-offset")

    if raw_params.include_total:
        total = await db.fetch_val(
            select(func.count()).select_from(query.order_by(None).alias())
        )
    else:
        total = None

    query = paginate_query(query, params)
    raw_items = await db.fetch_all(query)

    items: List[Any] = raw_items
    if convert_to_mapping:
        items = [{**item._mapping} for item in raw_items]

    t_items = await apply_items_transformer(items, transformer, async_=True)

    return create_page(
        t_items,
        total=total,
        params=params,
        **(additional_data or {}),
    )
