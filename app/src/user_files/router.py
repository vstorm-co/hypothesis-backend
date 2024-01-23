import logging

from fastapi import APIRouter, Depends

from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.user_files.schemas import CreateUserFileInput, DeleteUserFileOutput, UserFileDB
from src.user_files.service import (
    add_user_file_to_db,
    delete_user_file_from_db,
    get_specific_user_file_from_db,
    get_user_files_from_db,
)

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("")
async def get_user_files(
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    user_files = await get_user_files_from_db(jwt_data.user_id)
    if not user_files:
        return "No ok"
    return [UserFileDB(**dict(file)) for file in user_files]


@router.get("/{file_uuid}", response_model=UserFileDB)
async def get_specific_user_file(
    file_uuid, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    user_file = await get_specific_user_file_from_db(file_uuid)

    if not user_file:
        return "No ok"

    return UserFileDB(**dict(user_file))


@router.post("", response_model=UserFileDB)
async def create_user_file(
    data: CreateUserFileInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    user_file = await add_user_file_to_db(jwt_data.user_id, data)

    if not user_file:
        return "No ok"

    return UserFileDB(**dict(user_file))


@router.delete("{file_uuid}", response_model=DeleteUserFileOutput)
async def delete_user_file(file_uuid):
    await delete_user_file_from_db(file_uuid)
    return DeleteUserFileOutput(status="success")
