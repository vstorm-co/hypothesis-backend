import logging

from fastapi import APIRouter, Depends
from sqlalchemy.exc import NoResultFound

from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.user_models.constants import AVAILABLE_MODELS
from src.user_models.schemas import (
    UserModelCreateInput,
    UserModelDeleteOut,
    UserModelOut,
    UserModelOutWithModelsList,
    UserModelUpdateInput,
)
from src.user_models.service import (
    change_user_model_default_status,
    create_user_model_in_db,
    decrypt_api_key,
    delete_user_model_in_db,
    get_default_user_model,
    get_user_model_by_uuid,
    get_user_models_by_user_id,
    update_user_model_in_db,
)

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/available-models")
async def get_available_models(
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    return [
        {
            "provider": provider,
            "models": models,
        }
        for provider, models in AVAILABLE_MODELS.items()
    ]


@router.get("", response_model=list[UserModelOutWithModelsList])
async def get_user_models(
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    user_models_db = await get_user_models_by_user_id(jwt_data.user_id)

    user_models = [
        UserModelOutWithModelsList(**dict(model)) for model in user_models_db
    ]

    for model in user_models:
        model.api_key = decrypt_api_key(model.api_key)
        # Lowercase the keys in the available models dict
        available_models_copy = {
            key.lower(): value for key, value in AVAILABLE_MODELS.copy().items()
        }
        model.models = available_models_copy.get(model.provider.lower(), [])

    return user_models


@router.get("/{model_uuid}", response_model=UserModelOut)
async def get_specific_user_model(
    model_uuid, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    user_model_db = await get_user_model_by_uuid(model_uuid, jwt_data.user_id)

    if not user_model_db:
        raise NoResultFound()

    user_model = UserModelOut(**dict(user_model_db))
    user_model.api_key = decrypt_api_key(user_model.api_key)

    return user_model


@router.post("", response_model=UserModelOut)
async def create_user_model(
    user_model_data: UserModelCreateInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    user_model_data.user = jwt_data.user_id

    user_model = await create_user_model_in_db(user_model_data)
    if not user_model:
        raise NoResultFound()

    return UserModelOut(**dict(user_model))


@router.put("/{model_uuid}", response_model=UserModelOut)
async def update_user_model(
    model_uuid,
    user_model_data: UserModelUpdateInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    user_model = await update_user_model_in_db(
        model_uuid, jwt_data.user_id, user_model_data
    )
    if not user_model:
        raise NoResultFound()

    return UserModelOut(**dict(user_model))


@router.post("/{model_uuid}/toggle-default", response_model=UserModelOut)
async def toggle_user_model_default_status(
    model_uuid: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    user_model = await change_user_model_default_status(model_uuid, jwt_data.user_id)
    if not user_model:
        raise NoResultFound()

    return UserModelOut(**dict(user_model))


@router.delete("/{model_uuid}", response_model=UserModelDeleteOut)
async def delete_user_model(
    model_uuid, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    await delete_user_model_in_db(model_uuid, jwt_data.user_id)

    return UserModelDeleteOut(status="deleted")


@router.get("/default-model", response_model=UserModelOut)
async def get_default_user_model_from_db(
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    user_model = await get_default_user_model(jwt_data.user_id)
    if not user_model:
        raise NoResultFound()

    return UserModelOut(**dict(user_model))
