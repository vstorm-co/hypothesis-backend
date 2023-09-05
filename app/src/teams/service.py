import uuid

from databases.interfaces import Record
from sqlalchemy import insert, select, update

from src.database import database, team, users_teams

# from src.teams.database import team
from src.teams.schemas import AddUserToTeamInput, TeamCreate, TeamUpdateDetails


async def create_team_in_db(team_data: TeamCreate) -> Record | None:
    insert_query = (
        insert(team)
        .values({"uuid": uuid.uuid4(), "name": team_data.name})
        .returning(team)
    )
    return await database.fetch_one(insert_query)


async def get_teams_from_db(user_id: int) -> list[Record]:
    select_query = (
        select(team).join(users_teams).where(users_teams.c.auth_user_id == user_id)
    )
    return await database.fetch_all(select_query)


async def get_team_by_id_from_db(team_id: str) -> Record | None:
    select_query = select(team).where(team.c.uuid == team_id)
    return await database.fetch_one(select_query)


async def update_team_in_db(team_data: TeamUpdateDetails) -> Record | None:
    update_query = (
        update(team)
        .where(team.c.uuid == team_data.team_uuid)
        .values({"name": team_data.name})
        .returning(team)
    )
    return await database.fetch_one(update_query)


async def delete_team_from_db(team_id: str) -> None:
    # delete from users_teams where team_uuid = team_id
    delete_query = users_teams.delete().where(users_teams.c.team_uuid == team_id)
    await database.execute(delete_query)

    # delete team
    delete_query = team.delete().where(team.c.uuid == team_id)
    await database.execute(delete_query)


async def add_user_to_team_in_db(data: AddUserToTeamInput) -> Record | None:
    insert_query = (
        insert(users_teams)
        .values({"team_uuid": data.team_uuid, "auth_user_id": data.user_id})
        .returning(users_teams)
    )
    return await database.fetch_one(insert_query)
