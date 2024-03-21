import logging
from time import time

from databases.interfaces import Record

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
from src.annotations.scrape import get_hypothesis_selectors
from src.auth.schemas import JWTData
from src.chat.manager import connection_manager as manager
from src.chat.schemas import BroadcastData, MessageDetails
from src.chat.service import update_message_in_db
from src.listener.constants import bot_message_creation_finished_info

logger = logging.getLogger(__name__)


async def create_annotations_in_background(
    annotation_data: AnnotationFormInput,
    jwt_data: JWTData,
    db_user: Record,
    message_db: Record,
):
    start_time = time()

    hypothesis_user_id = get_hypothesis_user_id(annotation_data.api_key)
    logger.info(f"Hypo user: {hypothesis_user_id}")

    selectors: list[TextQuoteSelector] = await get_hypothesis_selectors(annotation_data)
    if not selectors:
        return AnnotationFormOutput(status={"result": "selectors not found"})

    document_title = "Document title"
    # create hypothesis annotations
    annotations = [
        HypothesisAnnotationCreateInput(
            uri=annotation_data.url,
            document={"title": [document_title]},
            text=annotation_data.prompt,
            tags=annotation_data.tags,
            group=annotation_data.group or "__world__",
            permissions={
                "read": [f"group:{annotation_data.group or '__world__'}"],
                "admin": [hypothesis_user_id],
                "update": [hypothesis_user_id],
                "delete": [hypothesis_user_id],
            },
            target=[
                HypothesisTarget(
                    source=annotation_data.url,
                    selector=[
                        HypothesisSelector(
                            exact=selector.exact,
                            prefix=selector.prefix,
                            suffix=selector.suffix,
                        )
                    ],
                )
            ],
            references=[],
        )
        for selector in selectors
    ]

    hypo_annotations_list: list[HypothesisAnnotationCreateOutput] = []
    for annotation in annotations:
        hypo_annotation_output = create_hypothesis_annotation(
            annotation, annotation_data.api_key
        )

        if not hypo_annotation_output:
            return AnnotationFormOutput(status={"result": "annotation not created"})

        hypo_annotations_list.append(hypo_annotation_output)

    ws_message = create_message_for_users(hypo_annotations_list)

    # save the message in the database
    # save id as a content
    # this will be loaded in getting chat history
    # and target selectors will be loaded from the hypothesis API
    await update_message_in_db(
        message_db["uuid"],
        MessageDetails(
            created_by="annotation",
            content=",".join([annotation.id for annotation in hypo_annotations_list]),
            room_id=annotation_data.room_id,
            user_id=jwt_data.user_id,
            elapsed_time=time() - start_time,
        ),
    )
    # broadcast the message in the chat
    await manager.broadcast(
        BroadcastData(
            type="annotation",
            message=ws_message,
            room_id=annotation_data.room_id,
            sender_user_email=db_user["email"],
            created_by="bot",
        )
    )
    # set the message that the bot has finished creating the annotation
    await manager.broadcast(
        BroadcastData(
            type=bot_message_creation_finished_info,
            message="",
            room_id=annotation_data.room_id,
            sender_user_email=db_user["email"],
            created_by="user",
        )
    )
