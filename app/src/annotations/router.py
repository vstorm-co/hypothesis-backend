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

    prompt_message_db: Record | None = await create_message_in_db(
        MessageDetails(
            created_by="annotation-prompt",
            content=annotation_data.prompt,
            room_id=annotation_data.room_id,
            user_id=jwt_data.user_id,
        )
    )
    if not prompt_message_db:
        raise Exception("Annotations Prompt message not created")

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

    create_annotations_in_background.delay(
        annotation_data.model_dump(),
        jwt_data.model_dump(),
        dict(user),
        dict(message_db),
        dict(prompt_message_db),
    )

    return AnnotationFormOutput(
        status={"result": "Creating annotations in background..."}
    )
