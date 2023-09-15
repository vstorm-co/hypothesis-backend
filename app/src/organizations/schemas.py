from uuid import UUID

from pydantic import BaseModel


class OrganizationBase(BaseModel):
    name: str
    picture: str


class OrganizationDB(OrganizationBase):
    uuid: UUID
    created_at: str


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(OrganizationBase):
    pass


class OrganizationDelete(OrganizationBase):
    organization_uuid: str


class OrganizationDeleteOutput(BaseModel):
    status: str


class SetUserOrganizationInput(BaseModel):
    organization_uuid: str
    user_ids: list[int]
    admin_ids: list[int]


class SetUserOrganizationOutput(BaseModel):
    status: str
