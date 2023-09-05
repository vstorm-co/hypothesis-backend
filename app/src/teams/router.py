from fastapi import APIRouter, Depends

from src.auth.jwt import parse_jwt_admin_data, parse_jwt_user_data
from src.auth.schemas import JWTData
from src.teams import service
from src.teams.schemas import (
    AddTeamToUserOutput,
    AddUserToTeamInput,
    TeamCreate,
    TeamDB,
    TeamDeleteOutput,
    TeamUpdate,
    TeamUpdateDetails,
)

router = APIRouter()


@router.get("", response_model=list[TeamDB])
async def get_teams(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    teams = await service.get_teams_from_db(jwt_data.user_id)

    return [TeamDB(**dict(team)) for team in teams]


# make path for getting team by id
@router.get("/{team_id}", response_model=TeamDB)
async def get_team_by_id(
    team_id: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    team = await service.get_team_by_id_from_db(team_id)

    if not team:
        pass

    return TeamDB(**dict(team))


@router.post("", response_model=TeamDB)
async def create_team(
    team_data: TeamCreate, jwt_data: JWTData = Depends(parse_jwt_admin_data)
):
    team = await service.create_team_in_db(team_data)

    if not team:
        pass

    return TeamDB(**dict(team))


@router.put("/{team_id}", response_model=TeamDB)
async def update_team(
    team_id: str,
    team_data: TeamUpdate,
    jwt_data: JWTData = Depends(parse_jwt_admin_data),
):
    team_data_with_id = TeamUpdateDetails(**team_data.model_dump(), team_uuid=team_id)
    team = await service.update_team_in_db(team_data_with_id)

    if not team:
        pass

    return TeamDB(**dict(team))


@router.delete("/{team_id}", response_model=TeamDeleteOutput)
async def delete_team(team_id: str, jwt_data: JWTData = Depends(parse_jwt_admin_data)):
    await service.delete_team_from_db(team_id)

    return TeamDeleteOutput(status="Ok")


@router.post("/add-to-user", response_model=AddTeamToUserOutput)
async def add_user_to_team(
    add_user_data: AddUserToTeamInput, jwt_data: JWTData = Depends(parse_jwt_admin_data)
):
    await service.add_user_to_team_in_db(add_user_data)

    return AddTeamToUserOutput(status="Ok")
