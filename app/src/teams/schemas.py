from pydantic import BaseModel


class TeamCreate(BaseModel):
    name: str


class TeamUpdate(BaseModel):
    name: str


class TeamUpdateWithId(TeamUpdate):
    team_uuid: str


class AddUserToTeam(BaseModel):
    team_uuid: str
    user_id: int
