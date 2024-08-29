from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class UserModelCreateInput(BaseModel):
    provider: str
    defaultSelected: str
    api_key: str
    user: int | None = None
    organization_uuid: Optional[UUID | str] = None


class UserModelUpdateInput(BaseModel):
    provider: Optional[str]
    defaultSelected: Optional[str]
    api_key: Optional[str]
    default: Optional[bool]
    organization_uuid: Optional[UUID | str] = None


class UserModelOut(BaseModel):
    uuid: UUID | str
    provider: str
    defaultSelected: str
    api_key: str
    default: bool
    user: int


class UserModelOutWithModelsList(UserModelOut):
    models: list[str] = []


class UserModelDeleteOut(BaseModel):
    status: str
