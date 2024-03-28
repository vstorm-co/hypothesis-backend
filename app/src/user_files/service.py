import uuid

from databases.interfaces import Record
from sqlalchemy import delete, insert, select, update

from src.database import UserFile, database
from src.user_files.schemas import CreateUserFileInput, NewUserFileContent


async def get_user_files_from_db(user_id: int) -> list[Record]:
    select_query = select(UserFile).where(UserFile.user == user_id)

    return await database.fetch_all(select_query)


async def get_specific_user_file_from_db(file_uuid: str, user_id: int) -> Record | None:
    select_query = select(UserFile).where(
        UserFile.uuid == file_uuid,
        UserFile.user == user_id,
    )

    return await database.fetch_one(select_query)


async def upsert_user_file_to_db(
    user_id: int, data: CreateUserFileInput
) -> Record | None:
    existing_file = await get_file_by_source_value_and_user(data.source_value, user_id)
    upsert_query: insert | update

    values = data.model_dump(exclude={"room_id", "id", "mime_type"})
    if existing_file:
        upsert_query = (
            update(UserFile)
            .where(UserFile.uuid == existing_file["uuid"])
            .values(
                {
                    "user": user_id,
                    **values,
                }
            )
            .returning(UserFile)
        )
        return await database.fetch_one(upsert_query)

    upsert_query = (
        insert(UserFile)
        .values(
            {
                "uuid": uuid.uuid4(),
                "user": user_id,
                **values,
            }
        )
        .returning(UserFile)
    )
    return await database.fetch_one(upsert_query)


async def get_file_by_source_value_and_user(
    source_value: str, user_id: int
) -> Record | None:
    select_query = select(UserFile).where(
        (UserFile.source_value == source_value) & (UserFile.user == user_id)
    )
    return await database.fetch_one(select_query)


async def delete_user_file_from_db(file_uuid) -> Record | None:
    delete_query = delete(UserFile).where(UserFile.uuid == file_uuid)
    return await database.fetch_one(delete_query)


async def optimize_file_content_in_db(
    file_uuid: str, data: NewUserFileContent
) -> Record | None:
    update_query = (
        update(UserFile)
        .where(UserFile.uuid == file_uuid)
        .values(**data.model_dump())
        .returning(UserFile)
    )
    return await database.fetch_one(update_query)
