import uuid

from databases.interfaces import Record
from sqlalchemy import delete, insert, select

from src.database import UserFile, database
from src.user_files.schemas import CreateUserFileInput


async def get_user_files_from_db(user_id) -> list[Record]:
    select_query = select(UserFile).where(UserFile.user == user_id)
    return await database.fetch_all(select_query)


async def get_specific_user_file_from_db(file_uuid) -> Record | None:
    select_query = select(UserFile).where(UserFile.uuid == file_uuid)
    return await database.fetch_one(select_query)


async def add_user_file_to_db(user_id, data: CreateUserFileInput) -> Record | None:
    insert_query = (
        insert(UserFile)
        .values(
            {
                "uuid": uuid.uuid4(),
                "user": user_id,
                **data.model_dump(),
            }
        )
        .returning(UserFile)
    )
    return await database.fetch_one(insert_query)


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
