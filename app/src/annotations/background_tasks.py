import json
import logging
from asyncio import get_event_loop
from time import time

from src.annotations.hypothesis_api import HypothesisAPI
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
from src.annotations.scrape import AnnotationsScraper
from src.annotations.validations import validate_data_tags
from src.auth.schemas import JWTData, UserDB
from src.chat.bot_ai import BotAI
from src.chat.schemas import BroadcastData, MessageDetails
from src.chat.service import update_message_in_db
from src.database import database
from src.listener.constants import bot_message_creation_finished_info
from src.redis import pub_sub_manager
from src.tasks import celery_app

logger = logging.getLogger(__name__)


async def create_annotations(
        form_data_input: dict,
        jwt_data_input: dict,
        db_user: dict,
        message_db: dict,
):
    if not db_user:
        logger.error("User not found")
        return AnnotationFormOutput(status={"result": "user not found"})

    user_db: UserDB = UserDB(**db_user)
    form_data: AnnotationFormInput = AnnotationFormInput(**form_data_input)
    jwt_data: JWTData = JWTData(**jwt_data_input)

    hypo_api = HypothesisAPI(data=form_data)
    scraper = AnnotationsScraper(data=form_data, user_db=user_db)
    bot_ai = BotAI(user_id=jwt_data.user_id, room_id=form_data.room_id)
    start_time = time()

    hypothesis_user_id = await hypo_api.get_hypothesis_user_id()
    logger.info(f"Hypo user: {hypothesis_user_id}")

    logger.info("Updating room title")
    await bot_ai.update_chat_title(
        input_message=f"""User asked for {form_data.prompt}
        from {form_data.url if form_data.input_type != 'google-drive' else 'google drive'}""",
        room_id=form_data.room_id,
        user_id=jwt_data.user_id,
    )

    selectors: list[TextQuoteSelector] = await scraper.get_hypothesis_selectors()
    if not selectors:
        return AnnotationFormOutput(status={"result": "selectors not found"})

    source: str = scraper.pdf_urn or form_data.url
    # create hypothesis annotations
    annotations: list[HypothesisAnnotationCreateInput] = [
        HypothesisAnnotationCreateInput(
            uri=source,
            document={"title": [scraper.get_document_title_from_first_split()]},
            text=selector.annotation,
            tags=validate_data_tags(form_data.tags),
            group=form_data.group or "__world__",
            permissions={
                "read": [f"group:{form_data.group or '__world__'}"],
                "admin": [hypothesis_user_id],
                "update": [hypothesis_user_id],
                "delete": [hypothesis_user_id],
            },
            target=[
                HypothesisTarget(
                    source=source,
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
        hypo_annotation_output = await hypo_api.create_hypothesis_annotation(
            data=annotation, form_data=form_data
        )

        if not hypo_annotation_output:
            return AnnotationFormOutput(status={"result": "annotation not created"})

        hypo_annotations_list.append(hypo_annotation_output)

    user_message = create_message_for_users(hypo_annotations_list, form_data.prompt)
    # save the message in the database
    # save id as a content
    # this will be loaded in getting chat history
    # and target selectors will be loaded from the hypothesis API
    await update_message_in_db(
        message_db["uuid"],
        MessageDetails(
            created_by="annotation",
            content=user_message,
            content_dict={
                "api_key": form_data.api_key,
                "annotations": [
                    annotation.model_dump(mode="json")
                    for annotation in hypo_annotations_list
                ],
                "url": source,
                "prompt": form_data.prompt,
                "group_id": form_data.group,
            },
            content_html=hypo_annotations_list[0].links.get("incontext", ""),
            room_id=form_data.room_id,
            user_id=jwt_data.user_id,
            elapsed_time=time() - start_time,
        ),
    )
    # broadcast the message in the chat
    await pub_sub_manager.publish(
        form_data.room_id,
        json.dumps(
            BroadcastData(
                type="annotation",
                message=user_message,
                room_id=form_data.room_id,
                created_by="bot",
            ).model_dump(mode="json"),
        ),
    )
    # set the message that the bot has finished creating the annotation
    await pub_sub_manager.publish(
        form_data.room_id,
        json.dumps(
            BroadcastData(
                type=bot_message_creation_finished_info,
                message="",
                room_id=form_data.room_id,
                created_by="bot",
            ).model_dump(mode="json")
        ),
    )


@celery_app.task
def create_annotations_in_background(
        form_data: dict,
        jwt_data: dict,
        db_user: dict,
        message_db: dict,
):
    loop = get_event_loop()
    loop.run_until_complete(database.connect())
    logger.info("Connected to database")
    loop.run_until_complete(
        create_annotations(
            form_data_input=form_data,
            jwt_data_input=jwt_data,
            db_user=db_user,
            message_db=message_db,
        )
    )
    logger.info("Got users from database")
    loop.run_until_complete(database.disconnect())
    return {"status": "OK"}
