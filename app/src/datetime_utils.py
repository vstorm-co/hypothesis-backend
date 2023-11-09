from datetime import datetime
from typing import Sequence

import pytz
from pydantic import BaseModel


def aware_datetime_fields(page_items: Sequence[BaseModel]):
    for item in page_items:
        for field_attr in item.model_fields:
            room_attr = item.__getattribute__(field_attr)
            if isinstance(room_attr, datetime):
                val = room_attr
                tz = pytz.timezone("Europe/Warsaw")
                aware_datetime = val.replace(tzinfo=pytz.utc).astimezone(tz)
                item.__setattr__(field_attr, aware_datetime)
