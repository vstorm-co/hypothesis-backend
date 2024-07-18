import uuid

from cryptography.fernet import Fernet
from databases.interfaces import Record
from sqlalchemy import and_, delete, insert, select, update
from sqlalchemy.exc import NoResultFound

from src.config import settings
from src.database import UserModel, database
from src.user_models.schemas import UserModelCreateInput, UserModelUpdateInput

cipher_suite = Fernet(settings.FERNET_KEY.encode())


async def get_user_models_by_user_id(user_id: int) -> list[Record] | None:
    select_query = select(UserModel).where(UserModel.user == user_id)

    return await database.fetch_all(select_query)


async def get_user_model_by_uuid(uuid: str, user_id: int) -> Record | None:
    select_query = select(UserModel).where(and_(UserModel.uuid == uuid, UserModel.user == user_id))

    try:
        return await database.fetch_one(select_query)
    except NoResultFound:
        return None


async def create_user_model_in_db(user_model_data: UserModelCreateInput) -> Record:
    # Encrypt the api_key
    user_model_data.api_key = cipher_suite.encrypt(user_model_data.api_key.encode()).decode()

    insert_query = insert(UserModel).values({
        "uuid": uuid.uuid4(),
        **user_model_data.model_dump(),
    }).returning(UserModel)

    return await database.fetch_one(insert_query)


async def update_user_model_in_db(model_uuid: str, user_id: int, user_model_data: UserModelUpdateInput) -> Record:
    # Encrypt the api_key
    if user_model_data.api_key:
        user_model_data.api_key = cipher_suite.encrypt(user_model_data.api_key.encode()).decode()

    update_query = (
        update(UserModel)
        .where(and_(UserModel.uuid == model_uuid, UserModel.user == user_id))
        .values(**user_model_data.model_dump())
        .returning(UserModel)
    )

    return await database.fetch_one(update_query)


async def change_user_model_default_status(model_uuid: str, user_id: int) -> Record:
    current_user_model_db = await get_user_model_by_uuid(model_uuid, user_id)
    if not current_user_model_db:
        raise NoResultFound

    current_user_model = UserModel(**dict(current_user_model_db))
    new_default_status = not current_user_model.default

    # if new_default_status is True, then rest user models need to be set to False
    if new_default_status:
        update_query = (
            update(UserModel)
            .where(
                UserModel.user == user_id,
                UserModel.uuid != model_uuid,
            )
            .values(default=False)
        )

        await database.execute(update_query)

    update_query = (
        update(UserModel)
        .where(and_(UserModel.uuid == model_uuid, UserModel.user == user_id))
        .values(default=new_default_status)
        .returning(UserModel)
    )

    return await database.fetch_one(update_query)


async def delete_user_model_in_db(model_uuid: str, user_id: int) -> Record:
    delete_query = delete(UserModel).where(and_(UserModel.uuid == model_uuid, UserModel.user == user_id))

    return await database.fetch_one(delete_query)


async def get_default_user_model(user_id: int) -> Record | None:
    select_query = select(UserModel).where(
        and_(
            UserModel.user == user_id,
            UserModel.default == True,
        )
    )

    try:
        return await database.fetch_one(select_query)
    except NoResultFound:
        return None


def decrypt_api_key(api_key: str) -> str:
    return cipher_suite.decrypt(api_key.encode()).decode()
