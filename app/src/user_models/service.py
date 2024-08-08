import uuid

from cryptography.fernet import Fernet
from databases.interfaces import Record
from sqlalchemy import and_, delete, insert, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload

from src.config import settings
from src.database import UserModel, database, OrganizationModel, Organization, OrganizationUser, OrganizationAdmin
from src.user_models.schemas import UserModelCreateInput, UserModelUpdateInput


cipher_suite = Fernet(settings.FERNET_KEY.encode())


async def get_org_model(org_models):
    user_model_uuids = [model["user_model_uuid"] for model in org_models]
    models_query = select(UserModel).where(UserModel.uuid.in_(user_model_uuids))

    user_models = await database.fetch_all(models_query)

    return user_models


async def get_user_models_by_user_id(user_id: int) -> list[Record]:
    # get very first organization that user belongs to
    select_user_org_query = select(Organization).join(
        OrganizationUser
    ).where(
        OrganizationUser.auth_user_id == user_id
    )

    user_orgs = await database.fetch_all(select_user_org_query)

    if user_orgs:
        user_org = user_orgs[0]
        # get all user models for the organization
        select_org_models_query = select(OrganizationModel).where(
            OrganizationModel.organization_uuid == user_org["uuid"]
        )

        org_models = await database.fetch_all(select_org_models_query)
        if org_models:
            user_models = await get_org_model(org_models)

            return user_models

    select_query = select(UserModel).where(UserModel.user == user_id)

    user_models = await database.fetch_all(select_query)

    return user_models


async def get_user_model_by_uuid(model_uuid: str, user_id: int) -> Record | None:
    select_query = select(UserModel).where(
        and_(UserModel.uuid == model_uuid, UserModel.user == user_id)
    )

    try:
        return await database.fetch_one(select_query)
    except NoResultFound:
        return None


async def create_user_model_in_db(
    user_model_data: UserModelCreateInput,
) -> Record | None:
    # Encrypt the api_key
    user_model_data.api_key = cipher_suite.encrypt(
        user_model_data.api_key.encode()
    ).decode()

    insert_query = (
        insert(UserModel)
        .values(
            {
                "uuid": uuid.uuid4(),
                **user_model_data.model_dump(),
            }
        )
        .returning(UserModel)
    )

    user_model = await database.fetch_one(insert_query)
    user_model = dict(user_model)

    # get very first organization that user belongs to
    select_user_org_query = select(Organization).join(
        OrganizationUser
    ).where(
        OrganizationUser.auth_user_id == user_model["user"]
    )

    user_orgs = await database.fetch_all(select_user_org_query)

    if user_orgs:
        # add the user model to the organization
        organization = user_orgs[0]

        # get existing org models
        # select_org_models_query = select(OrganizationModel).where(
        #     OrganizationModel.organization_uuid == organization["uuid"]
        # )

        # org_models_relation = await database.fetch_all(select_org_models_query)
        #
        # if org_models_relation:
        #     org_models = await get_org_model(org_models_relation)
        #
        #     for model_db in org_models:
        #         model = dict(model_db)
        #
        #         if model["provider"] == user_model_data.provider:



        # check if

        insert_org_model_query = (
            insert(OrganizationModel)
            .values(
                {
                    "uuid": uuid.uuid4(),
                    "organization_uuid": organization["uuid"],
                    "user_model_uuid": user_model["uuid"],
                }
            )
        )

        await database.fetch_one(insert_org_model_query)

    return user_model


async def update_user_model_in_db(
    model_uuid: str, user_id: int, user_model_data: UserModelUpdateInput
) -> Record | None:
    # Encrypt the api_key
    if user_model_data.api_key:
        user_model_data.api_key = cipher_suite.encrypt(
            user_model_data.api_key.encode()
        ).decode()

    update_query = (
        update(UserModel)
        .where(and_(UserModel.uuid == model_uuid, UserModel.user == user_id))
        .values(
            **user_model_data.model_dump(
                exclude={
                    "default",
                }
            )
        )
        .returning(UserModel)
    )

    return await database.fetch_one(update_query)


async def change_user_model_default_status(
    model_uuid: str, user_id: int
) -> Record | None:
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

        await database.fetch_one(update_query)

    update_query = (
        update(UserModel)
        .where(and_(UserModel.uuid == model_uuid, UserModel.user == user_id))
        .values(default=new_default_status)
        .returning(UserModel)
    )

    return await database.fetch_one(update_query)


async def delete_user_model_in_db(model_uuid: str, user_id: int) -> Record | None:
    delete_query = delete(UserModel).where(
        and_(UserModel.uuid == model_uuid, UserModel.user == user_id)
    )

    return await database.fetch_one(delete_query)


async def get_default_user_model(user_id: int) -> Record | None:
    select_query = select(UserModel).where(
        and_(
            UserModel.user == user_id,
            UserModel.default is True,
        )
    )

    try:
        return await database.fetch_one(select_query)
    except NoResultFound:
        return None


def decrypt_api_key(api_key: str) -> str:
    return cipher_suite.decrypt(api_key.encode()).decode()
