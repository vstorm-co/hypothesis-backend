import logging

from fastapi import APIRouter, Depends, UploadFile

from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.chat.chatting import hypo_ai
from src.user_files.exceptions import (
    FailedToDownloadAndExtractFile,
    UserFileAlreadyExists,
    UserFileDoesNotExist,
)
from src.user_files.schemas import CreateUserFileInput, DeleteUserFileOutput, UserFileDB
from src.user_files.service import (
    add_user_file_to_db,
    delete_user_file_from_db,
    get_file_by_source_value_and_user,
    get_specific_user_file_from_db,
    get_user_files_from_db,
)
from src.user_files.utils import download_and_extract_file

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("", response_model=list[UserFileDB])
async def get_user_files(
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    user_files = await get_user_files_from_db(jwt_data.user_id)

    return [UserFileDB(**dict(file)) for file in user_files]


@router.get("/{file_uuid}", response_model=UserFileDB)
async def get_specific_user_file(
    file_uuid, jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    user_file = await get_specific_user_file_from_db(file_uuid)

    if not user_file:
        raise UserFileDoesNotExist()

    return UserFileDB(**dict(user_file))


@router.post("", response_model=UserFileDB)
async def create_user_file(
    data: CreateUserFileInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    existing_file = await get_file_by_source_value_and_user(
        data.source_value, jwt_data.user_id
    )
    if existing_file:
        raise UserFileAlreadyExists()

    if data.source_type == "url":
        logger.info(f"Downloading and extracting file from: {data.source_value}")
        content = download_and_extract_file(data.source_value)
        if not content:
            raise FailedToDownloadAndExtractFile()
        data.content = content
        # get title from url file name
        data.title = hypo_ai.get_title_from_url(data.source_value)

    data.optimized_content = hypo_ai.optimize_content(data.content)
    user_file = await add_user_file_to_db(jwt_data.user_id, data)

    if not user_file:
        raise UserFileAlreadyExists()

    return UserFileDB(**dict(user_file))


@router.post("/from-file", response_model=UserFileDB)
async def create_user_file_from_file(
    file: UploadFile,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    data = CreateUserFileInput(
        source_type="file",
        source_value="file",
        title=file.filename or "file",
        content=file.file.read().decode("utf-8"),
    )
    optimized_content = hypo_ai.optimize_content(data.content)
    data.optimized_content = optimized_content
    user_file = await add_user_file_to_db(jwt_data.user_id, data)

    if not user_file:
        raise UserFileAlreadyExists()

    return UserFileDB(**dict(user_file))


@router.delete("{file_uuid}", response_model=DeleteUserFileOutput)
async def delete_user_file(file_uuid):
    await delete_user_file_from_db(file_uuid)
    return DeleteUserFileOutput(status="success")
