import logging

from fastapi import APIRouter, Depends
from sqlalchemy.exc import NoResultFound

from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.user_models.schemas import UserModelCreateInput, UserModelUpdateInput, UserModelOut, UserModelDeleteOut
from src.user_models.service import get_user_models_by_user_id, get_user_model_by_uuid, create_user_model_in_db, \
    update_user_model_in_db, change_user_model_active_status, delete_user_model_in_db, decrypt_api_key

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/available-models")
async def get_available_models(
    # jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    return {
        "openai": [
            "gpt-4-1106-preview",
            "gpt-3.5-turbo-1106",
            "gpt-4-turbo-2024-04-09",
            "gpt-4o-2024-05-13",
        ],
        "claude": [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
        ]
    }


@router.get("", response_model=list[UserModelOut])
async def get_user_models(
        jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    user_models = await get_user_models_by_user_id(jwt_data.user_id)

    for model in user_models:
        model_dict = dict(model)
        if not model_dict.get("api_key"):
            continue
        model["api_key"] = decrypt_api_key(model["api_key"])

    return [UserModelOut(**dict(model)) for model in user_models]


@router.get("/{model_uuid}", response_model=UserModelOut)
async def get_specific_user_model(
        model_uuid, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    user_model = await get_user_model_by_uuid(model_uuid, jwt_data.user_id)

    if not user_model:
        raise NoResultFound()

    user_model = UserModelOut(**dict(user_model))
    user_model.api_key = decrypt_api_key(user_model.api_key)

    return user_model


@router.post("", response_model=UserModelOut)
async def create_user_model(
    user_model_data: UserModelCreateInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    user_model_data.user = jwt_data.user_id

    user_model = await create_user_model_in_db(user_model_data)

    return UserModelOut(**dict(user_model))


@router.put("/{model_uuid}", response_model=UserModelOut)
async def update_user_model(
        model_uuid, user_model_data: UserModelUpdateInput, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    user_model = await update_user_model_in_db(model_uuid, jwt_data.user_id, user_model_data)

    return UserModelOut(**dict(user_model))


@router.delete("/{model_uuid}", response_model=UserModelDeleteOut)
async def delete_user_model(
        model_uuid, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    await delete_user_model_in_db(model_uuid, jwt_data.user_id)

    return UserModelDeleteOut(status="deleted")


@router.post("/{model_uuid}/toggle-active", response_model=UserModelOut)
async def toggle_user_model_active_status(
        model_uuid: str, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    user_model = await change_user_model_active_status(model_uuid, jwt_data.user_id)

    return UserModelOut(**dict(user_model))
