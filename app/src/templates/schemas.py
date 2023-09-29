from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.templates.enums import VisibilityChoices


class TemplateBase(BaseModel):
    name: str | None = None
    share: bool = False
    visibility: str = VisibilityChoices.JUST_ME


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
