from datetime import datetime
from typing import Sequence

from pydantic import BaseModel

from src.datetime_utils import aware_datetime_field


def enrich_paginated_items(page_items: Sequence[BaseModel]):
    for item in page_items:
        for field_attr in item.model_fields:
            room_attr = item.__getattribute__(field_attr)

            if isinstance(room_attr, datetime):
                set_value = aware_datetime_field(room_attr)
                item.__setattr__(field_attr, set_value)
