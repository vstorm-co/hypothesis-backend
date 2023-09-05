from fastapi import APIRouter, Depends
from starlette import status

from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.teams import service
from src.teams.schemas import TeamCreate, TeamUpdate, TeamUpdateWithId, AddUserToTeam

router = APIRouter()


# TODO Add JWT data to endpoints

@router.get("/team")
async def get_teams(jwt_data: JWTData = Depends(parse_jwt_user_data)):
    teams = await service.get_teams_from_db(jwt_data.user_id)
    return teams


@router.post("/team", status_code=status.HTTP_201_CREATED)
async def create_team(
        team_data: TeamCreate
):
    team = await service.create_team_in_db(team_data)
    return {"team": team}


@router.put("/team/{team_id}")
async def update_team(
        team_id: str,
        team_data: TeamUpdate
):
    team_data_with_id = TeamUpdateWithId(**team_data.model_dump(), team_id=team_id)
    team = await service.update_team_in_db(team_data_with_id)
    return {"team": team}


@router.post("/add_to_team")
async def add_user_to_team(data: AddUserToTeam):
    await service.add_user_to_team_in_db(data)
    return {"status": "Ok"}
