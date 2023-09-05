import uuid

from databases.interfaces import Record
from sqlalchemy import select, insert, update, delete

from src.database import database, auth_user, team, users_teams
# from src.teams.database import team
from src.teams.schemas import TeamCreate, TeamUpdateWithId, AddUserToTeam


async def create_team_in_db(team_data: TeamCreate) -> Record | None:
    insert_query = (
        insert(team)
        .values(
            {"uuid": uuid.uuid4(), "name": team_data.name}
        )
        .returning(team)
    )
    return await database.fetch_one(insert_query)


async def get_teams_from_db(user_id: int) -> list[Record]:
    # select_query = select(team).where(users_teams.c.auth_user_id == user_id)
    # select_query = select(team).where(team.auth_user_id == user_id)
    # select_query = select(team).join(users_teams).where(users_teams.c.auth_user_id == user_id)
    select_query = (
        select(team)
        .join(users_teams)
        .where(users_teams.c.auth_user_id == user_id)
    )
    return await database.fetch_all(select_query)


async def update_team_in_db(team_data: TeamUpdateWithId) -> Record | None:
    update_query = (
        update(team)
        .where(team.c.uuid == team_data.team_uuid)
        .values({"name": team_data.name})
        .returning(team)
    )
    return await database.fetch_one(update_query)


async def add_user_to_team_in_db(data: AddUserToTeam) -> Record | None:
    insert_query = (
        insert(users_teams)
        .values(
            {"team_uuid": data.team_uuid, "auth_user_id": data.user_id}
        )
        .returning(users_teams)
    )
    return await database.fetch_one(insert_query)
