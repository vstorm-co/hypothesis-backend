from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

from src.templates.enums import VisibilityChoices
from src.utils import validate_html


class TemplateBase(BaseModel):
    name: str | None = None
    share: bool = False
    visibility: str = VisibilityChoices.JUST_ME
    content_html: str | None = None

    @field_validator("content_html")
    @classmethod
    def validate_content_html(cls, value):
        if isinstance(value, str):
            is_valid = validate_html(value)
            assert is_valid, "content_html- Invalid HTML"

        return value


class TemplateDB(TemplateBase):
    uuid: UUID
    created_at: datetime
    user_id: int
    content: str | None = None


class TemplateCreateInput(TemplateBase):
    content: str


class TemplateCreateInputDetails(TemplateCreateInput):
    user_id: int


class TemplateDetails(TemplateBase):
    uuid: UUID
    content: str


class TemplateUpdate(TemplateBase):
    content: str | None = None


class TemplateUpdateInputDetails(TemplateUpdate):
    uuid: str
    user_id: int


class TemplateDeleteOutput(BaseModel):
    status: str
