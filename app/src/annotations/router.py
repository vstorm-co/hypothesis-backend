import logging
from time import time

from databases.interfaces import Record
from fastapi import APIRouter, Depends

from src.annotations.hypothesis_api import (
    create_hypothesis_annotation,
    get_hypothesis_user_id,
)
from src.annotations.messaging import create_message_for_users
from src.annotations.schemas import (
    AnnotationFormInput,
    AnnotationFormOutput,
    HypothesisAnnotationCreateInput,
    HypothesisAnnotationCreateOutput,
    HypothesisSelector,
    HypothesisTarget,
    TextQuoteSelector,
)
from src.annotations.scrape import get_selectors_by_query_from_url
from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData
from src.auth.service import get_user_by_id
from src.chat.manager import connection_manager as manager
from src.chat.schemas import BroadcastData, MessageDetails
from src.chat.service import create_message_in_db
from src.listener.constants import bot_message_creation_finished_info

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
    start_time = time()
    user: Record | None = await get_user_by_id(jwt_data.user_id)
    if not user:
        raise Exception("User not found")

    hypothesis_user_id = get_hypothesis_user_id(annotation_data.api_key)
    logger.info(f"Hypo user: {hypothesis_user_id}")

    selectors: list[TextQuoteSelector] = await get_selectors_by_query_from_url(
        annotation_data.prompt, annotation_data.url
    )
    if not selectors:
        return AnnotationFormOutput(status={"result": "selectors not found"})

    # create hypothesis annotation
    target = [
        HypothesisTarget(
            source=annotation_data.url,
            selector=[
                HypothesisSelector(
                    exact=selector.exact,
                    prefix=selector.prefix,
                    suffix=selector.suffix,
                )
                for selector in selectors
            ],
        )
    ]
    logger.info(f"Target: {target}")
    hypothesis_annotation_input = HypothesisAnnotationCreateInput(
        uri=annotation_data.url,
        document={"title": ["Document title"]},
        text=annotation_data.prompt,
        tags=annotation_data.tags,
        group=annotation_data.group or "__world__",
        permissions={
            "read": ["group:__world__"],
            "admin": [hypothesis_user_id],
            "update": [hypothesis_user_id],
            "delete": [hypothesis_user_id],
        },
        target=target,
        references=[],
    )
    hypo_annotation_output: HypothesisAnnotationCreateOutput | None = (
        create_hypothesis_annotation(
            hypothesis_annotation_input, annotation_data.api_key
        )
    )
    if not hypo_annotation_output:
        return AnnotationFormOutput(status={"result": "annotation not created"})

    ws_message = create_message_for_users(hypo_annotation_output)

    # save the message in the database
    # save id as a content
    # this will be loaded in getting chat history
    # and target selectors will be loaded from the hypothesis API
    await create_message_in_db(
        MessageDetails(
            created_by="annotation",
            content=hypo_annotation_output.id,
            room_id=annotation_data.room_id,
            user_id=jwt_data.user_id,
            elapsed_time=time() - start_time,
        )
    )
    # broadcast the message in the chat
    await manager.broadcast(
        BroadcastData(
            type="annotation",
            message=ws_message,
            room_id=annotation_data.room_id,
            sender_user_email=user["email"],
            created_by="bot",
        )
    )
    # set the message that the bot has finished creating the annotation
    await manager.broadcast(
        BroadcastData(
            type=bot_message_creation_finished_info,
            message="",
            room_id=annotation_data.room_id,
            sender_user_email=user["email"],
            created_by="user",
        )
    )

    return AnnotationFormOutput(status={"result": "selectors created successfully"})
