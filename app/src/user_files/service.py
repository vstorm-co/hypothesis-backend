import uuid

from databases.interfaces import Record
from sqlalchemy import delete, insert, select

from src.database import File, database
from src.user_files.schemas import CreateUserFileInput


async def get_user_files_from_db(user_id) -> list[Record] | None:
    select_query = select(File).where(File.user == user_id)
    return await database.fetch_all(select_query)


async def get_specific_user_file_from_db(file_uuid) -> Record | None:
    select_query = select(File).where(File.uuid == file_uuid)
    return await database.fetch_one(select_query)


async def add_user_file_to_db(user_id, data: CreateUserFileInput) -> Record | None:
    insert_query = (
        insert(File)
        .values(
            {
                "uuid": uuid.uuid4(),
                "user": user_id,
                "title": data.title,
                "content": data.content,
                "source": data.source,
            }
        )
        .returning(File)
    )
    return await database.fetch_one(insert_query)


async def delete_user_file_from_db(file_uuid) -> Record | None:
    delete_query = delete(File).where(File.uuid == file_uuid)
    return await database.fetch_one(delete_query)
