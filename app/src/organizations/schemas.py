from uuid import UUID

from pydantic import BaseModel


class OrganizationBase(BaseModel):
    name: str
    picture: str


class OrganizationDB(OrganizationBase):
    uuid: UUID


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
    user_id: int


class SetUserOrganizationOutput(BaseModel):
    status: str
