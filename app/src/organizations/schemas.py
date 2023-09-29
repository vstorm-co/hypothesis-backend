from datetime import datetime
from uuid import UUID

from fastapi import UploadFile
from pydantic import BaseModel

from src.auth.schemas import UserDB
from src.organizations.utils import as_form


class OrganizationBase(BaseModel):
    name: str
    picture: str | None = None


class OrganizationDB(OrganizationBase):
    uuid: UUID
    created_at: datetime


class OrganizationDetails(OrganizationDB):
    users: list[UserDB]
    admins: list[UserDB]


@as_form
class OrganizationCreate(OrganizationBase):
    file: UploadFile | None


class OrganizationCreateDetails(OrganizationCreate):
    domain: str | None = None


class OrganizationUpdate(OrganizationBase):
    pass


class OrganizationDelete(OrganizationBase):
    organization_uuid: str


class OrganizationDeleteOutput(BaseModel):
    status: str


class AddUsersToOrganizationInput(BaseModel):
    organization_uuid: str
    user_ids: list[int] | None = None
    admin_ids: list[int] | None = None


class AddUsersToOrganizationOutput(BaseModel):
    status: str


class RemoveUsersFromOrganizationInput(BaseModel):
    user_ids: list[int] | None = None
    admin_ids: list[int] | None = None


class RemoveUsersFromOrganizationOutput(BaseModel):
    status: str


# Organizations users
class OrganizationUserDB(BaseModel):
    id: int
    organization_uuid: UUID
    auth_user_id: int


# Organizations admins
class OrganizationAdminDB(BaseModel):
    id: int
    organization_uuid: UUID
    auth_user_id: int
    created_at: datetime
