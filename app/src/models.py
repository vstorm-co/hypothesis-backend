from datetime import datetime
from typing import Any, Type
from zoneinfo import ZoneInfo

from pydantic import BaseModel, model_validator


def convert_datetime_to_gmt(dt: datetime) -> str:
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


class ORJSONModel(BaseModel):
    class Config:
        json_encoders = {datetime: convert_datetime_to_gmt}
        populate_by_name = True

    @model_validator(mode="after")
    @classmethod
    def set_null_microseconds(cls, model: Any) -> Type["ORJSONModel"]:
        #  model is actually a BaseModel object
        for k, v in model.model_fields.items():
            if isinstance(v, datetime):
                model[k] = v.replace(microsecond=0)

        return model
