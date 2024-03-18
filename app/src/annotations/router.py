import asyncio
import logging

from databases.interfaces import Record
from fastapi import APIRouter, Depends

from src.annotations.background_tasks import create_annotations_in_background
from src.annotations.schemas import AnnotationFormInput, AnnotationFormOutput
from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.auth.service import get_user_by_id
from src.chat.schemas import MessageDetails
from src.chat.service import create_message_in_db

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=AnnotationFormOutput,
)
async def create_annotation(
    annotation_data: AnnotationFormInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    user: Record | None = await get_user_by_id(jwt_data.user_id)
    if not user:
        raise Exception("User not found")

    message_db: Record | None = await create_message_in_db(
        MessageDetails(
            created_by="annotation",
            content="Creating...",
            room_id=annotation_data.room_id,
            user_id=jwt_data.user_id,
        )
    )
    if not message_db:
        raise Exception("Message not created")

    asyncio.ensure_future(
        create_annotations_in_background(annotation_data, jwt_data, user, message_db)
    )

    return AnnotationFormOutput(
        status={"result": "Creating annotations in background..."}
    )
