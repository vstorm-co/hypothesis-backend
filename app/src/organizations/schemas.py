from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.auth.schemas import UserDBNoSecrets


class OrganizationBase(BaseModel):
    name: str
    picture: str | None = None


class OrganizationDB(OrganizationBase):
    uuid: UUID
    created_at: datetime
    updated_at: datetime | None = None


class OrganizationDetails(OrganizationDB):
    users: list[UserDBNoSecrets]


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationCreateDetails(OrganizationCreate):
    domain: str | None = None


class OrganizationUpdate(BaseModel):
    name: str


class OrganizationDelete(OrganizationBase):
    organization_uuid: str


class OrganizationDeleteOutput(BaseModel):
    status: str


class AddUsersToOrganizationInput(BaseModel):
    user_ids: list[int] | None = None
    admin_ids: list[int] | None = None


class AddNewUsersToOrganizationInput(BaseModel):
    user_ids: list[str] | None = None
    admin_ids: list[str] | None = None


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
    updated_at: datetime | None = None


class OrganizationPictureUpdate(BaseModel):
    picture: str


class AddUserToOrganizationByEmails(BaseModel):
    emails: list[str]
    as_admin: bool = False
