import json
import logging

from databases.interfaces import Record
from fastapi import APIRouter, Depends

from src.annotations.background_tasks import create_annotations_in_background
from src.annotations.hypothesis_api import HypothesisAPI
from src.annotations.schemas import (
    AnnotationDeleteInput,
    AnnotationFormInput,
    AnnotationFormOutput,
    HypothesisApiInput,
)
from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.auth.service import get_user_by_id
from src.chat.schemas import MessageDetails
from src.chat.service import create_message_in_db, delete_user_message_from_db
from src.listener.constants import listener_room_name, room_changed_info
from src.listener.schemas import WSEventMessage
from src.redis_client import pub_sub_manager

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
            content_dict={
                "prompt": annotation_data.prompt,
                "model_used": annotation_data.model,
            },
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


@router.delete(
    "",
    response_model=AnnotationFormOutput,
)
async def delete_annotations(
    input_data: AnnotationDeleteInput,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
):
    user: Record | None = await get_user_by_id(jwt_data.user_id)
    if not user:
        raise Exception("User not found")

    for annotation_id in input_data.annotation_ids:
        hypo_api: HypothesisAPI = HypothesisAPI(
            data=HypothesisApiInput(
                room_id=input_data.room_id, api_key=input_data.api_key
            )
        )
        hypo_api.delete_user_annotation(annotation_id)

    logger.info("Deleting message from DB")
    await delete_user_message_from_db(input_data.message_uuid, jwt_data.user_id)
    logger.info("Message deleted from DB")

    await pub_sub_manager.publish(
        listener_room_name,
        json.dumps(
            WSEventMessage(
                type=room_changed_info,
                id=str(jwt_data.user_id),
                source="delete-annotations",
            ).model_dump(mode="json")
        ),
    )

    return AnnotationFormOutput(status={"result": "Annotations deleted successfully"})
