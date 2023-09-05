from uuid import UUID

from pydantic import BaseModel


class TeamBase(BaseModel):
    name: str


class TeamCreate(TeamBase):
    pass


class TeamDB(TeamBase):
    uuid: UUID


class TeamUpdate(BaseModel):
    name: str


class TeamUpdateDetails(TeamUpdate):
    team_uuid: str


class DeleteOutputBase(BaseModel):
    status: str


class TeamDeleteOutput(DeleteOutputBase):
    status: str


class AddTeamToUserOutput(DeleteOutputBase):
    status: str


class AddUserToTeamInput(BaseModel):
    team_uuid: str
    user_id: int
