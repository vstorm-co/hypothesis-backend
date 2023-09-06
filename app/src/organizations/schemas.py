from pydantic import BaseModel


class OrganizationBase(BaseModel):
    name: str


class OrganizationDB(OrganizationBase):
    organization_uuid: str


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationChange(OrganizationBase):
    organization_uuid: str


class OrganizationDelete(OrganizationBase):
    organization_uuid: str


class OrganizationDeleteOutput(BaseModel):
    status: str


class AddUserInput(BaseModel):
    organization_uuid: str
    user_id: int


class AddUserOutput(BaseModel):
    status: str
