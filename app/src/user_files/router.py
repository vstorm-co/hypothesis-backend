import json
import logging

from fastapi import APIRouter, Depends, File, UploadFile

from src.auth.exceptions import UserNotFound
from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData, UserDB
from src.auth.service import get_user_by_id
from src.chat.bot_ai import bot_ai
from src.google_drive.downloader import get_google_drive_pdf_details, get_google_file_info
from src.listener.constants import (
    listener_room_name,
    optimizing_user_file_content_info,
    user_file_updated_info,
)
from src.listener.schemas import WSEventMessage
from src.redis import pub_sub_manager
from src.scraping.downloaders import download_and_extract_content_from_url
from src.user_files.constants import UserFileSourceType
from src.user_files.exceptions import (
    FailedToDownloadAndExtractFile,
    UserFileAlreadyExists,
    UserFileDoesNotExist,
)
from src.user_files.schemas import CreateUserFileInput, DeleteUserFileOutput, UserFileDB
from src.user_files.service import (
    delete_user_file_from_db,
    get_specific_user_file_from_db,
    get_user_files_from_db,
    upsert_user_file_to_db,
)

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
    user_file = await get_specific_user_file_from_db(file_uuid, jwt_data.user_id)

    if not user_file:
        raise UserFileDoesNotExist()

    return UserFileDB(**dict(user_file))


@router.post("", response_model=UserFileDB | dict[str, str])
async def create_user_file(
    file_data: CreateUserFileInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    # get_user_by_token
    user = await get_user_by_id(jwt_data.user_id)
    if not user:
        raise UserNotFound()
    user_db = UserDB(**dict(user))

    logger.info(f"Downloading and extracting file from: {file_data.source_value}")
    if file_data.source_type == UserFileSourceType.URL:
        url_data = await download_and_extract_content_from_url(file_data.source_value, get_urn=True)
        if not url_data:
            raise FailedToDownloadAndExtractFile()

        file_data.content = url_data.get("content", "")
        # get title from url file name
        file_data.title = await bot_ai.get_title_from_url(
            url=file_data.source_value, user_id=jwt_data.user_id
        )
        file_data.extension = file_data.source_value.split(".")[-1]
    if file_data.source_type == UserFileSourceType.GOOGLE_DRIVE:
        file_data.content = file_data.source_value.encode("utf-8").decode("unicode_escape")

        if not file_data.id and file_data.mime_type == "application/pdf":
            logger.error("File ID is missing")
            return {"status": "error", "message": "File ID is missing"}

        if file_data.mime_type == "application/pdf":
            pdf_details: dict | None = await get_google_drive_pdf_details(
                file_data.id, user_db
            )
            if pdf_details:
                logger.info("Downloaded content from google drive")
                file_data.content = pdf_details["content"]
                file_data.title = pdf_details["name"]
        else:
            file_info = get_google_file_info(file_data.id, {
                "Authorization": f"Bearer {user_db.credentials.get('google_access_token', '')}",
            })
            file_data.title = file_info.get("name", await bot_ai.get_title_from_content(file_data.content))

    await pub_sub_manager.publish(
        file_data.room_id or "",
        json.dumps(
            WSEventMessage(
                type=optimizing_user_file_content_info,
                id=str(jwt_data.user_id),
                source="update-user-file-content",
            ).model_dump(mode="json")
        ),
    )

    user_file = await upsert_user_file_to_db(jwt_data.user_id, file_data)

    if not user_file:
        raise UserFileAlreadyExists()

    await pub_sub_manager.publish(
        listener_room_name,
        json.dumps(
            WSEventMessage(
                type=user_file_updated_info,
                id=str(jwt_data.user_id),
                source="update-user-file-content",
            ).model_dump(mode="json")
        ),
    )

    return UserFileDB(**dict(user_file))  # Return the processed file data


@router.post("/from-file", response_model=UserFileDB)
async def create_user_file_from_file(
    file: UploadFile = File(...),
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    data = CreateUserFileInput(
        source_type="file",
        source_value="file",
        title=file.filename or "file",
        content=file.file.read().decode("utf-8"),
    )
    optimized_content = await bot_ai.optimize_content(
        content=data.content, user_id=jwt_data.user_id, room_id=""
    )
    data.optimized_content = optimized_content
    user_file = await upsert_user_file_to_db(jwt_data.user_id, data)

    if not user_file:
        raise UserFileAlreadyExists()

    return UserFileDB(**dict(user_file))


@router.delete("{file_uuid}", response_model=DeleteUserFileOutput)
async def delete_user_file(file_uuid):
    await delete_user_file_from_db(file_uuid)
    return DeleteUserFileOutput(status="success")
