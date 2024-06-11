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
from src.chat.service import get_room_by_id_from_db, update_message_in_db
from src.database import database
from src.listener.constants import bot_message_creation_finished_info
from src.redis import pub_sub_manager
from src.tasks import celery_app
from src.user_files.constants import UserFileSourceType

logger = logging.getLogger(__name__)


async def create_annotations(
    form_data_input: dict,
    jwt_data_input: dict,
    db_user: dict,
    message_db: dict,
    prompt_message_db: dict,
) -> AnnotationFormOutput:
    if not db_user:
        logger.error("User not found")
        await update_message_in_db(
            message_db["uuid"],
            MessageDetails(
                created_by="annotation",
                content="User not found",
                room_id=form_data_input["room_id"],
                user_id=jwt_data_input["user_id"],
            ),
        )

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

    db_room = await get_room_by_id_from_db(form_data.room_id)
    room_name: str | None = db_room["name"] if db_room else None

    if room_name == "New Chat" or not room_name:
        info_from = (
            "google drive"
            if form_data.input_type == UserFileSourceType.GOOGLE_DRIVE
            else UserFileSourceType.URL
        )
        logger.info("Updating room title")

        await bot_ai.update_chat_title(
            input_message=f"""User asked for {form_data.prompt} from {info_from}""",
            room_id=form_data.room_id,
            user_id=jwt_data.user_id,
        )

    selectors: list[TextQuoteSelector] = await scraper.get_hypothesis_selectors()
    # save the prompt in the database
    await update_message_in_db(
        prompt_message_db["uuid"],
        MessageDetails(
            created_by="annotation-prompt",
            content=scraper.whole_input,
            room_id=form_data.room_id,
            user_id=jwt_data.user_id,
        ),
    )

    if not selectors:
        logger.error("Selectors not created")

        await update_message_in_db(
            message_db["uuid"],
            MessageDetails(
                created_by="annotation",
                content="Selectors not created",
                room_id=form_data.room_id,
                user_id=jwt_data.user_id,
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

        return AnnotationFormOutput(status={"result": "selectors not created"})

    source: str = scraper.pdf_urn or form_data.url
    doc_title = scraper.get_document_title_from_first_split()
    # create hypothesis annotations
    annotations: list[HypothesisAnnotationCreateInput] = [
        HypothesisAnnotationCreateInput(
            uri=source,
            document={
                "title": [doc_title],
            },
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
            logger.error("Annotation not created")
            await update_message_in_db(
                message_db["uuid"],
                MessageDetails(
                    created_by="annotation",
                    content="Annotation not created",
                    room_id=form_data.room_id,
                    user_id=jwt_data.user_id,
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

            return AnnotationFormOutput(status={"result": "annotation not created"})

        hypo_annotations_list.append(hypo_annotation_output)

    # save the message in the database
    # save id as a content
    # this will be loaded in getting chat history
    # and target selectors will be loaded from the hypothesis API
    user_message = create_message_for_users(hypo_annotations_list, form_data.prompt)
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
                "url": hypo_annotations_list[-1].links.get("incontext", ""),
                "prompt": form_data.prompt,
                "group_id": form_data.group,
                "selectors": [selector.model_dump() for selector in selectors],
            },
            content_html=hypo_annotations_list[-1].links.get("incontext", ""),
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

    return AnnotationFormOutput(status={"result": "annotation created"})


@celery_app.task
def create_annotations_in_background(
    form_data: dict,
    jwt_data: dict,
    db_user: dict,
    message_db: dict,
    prompt_message_db: dict,
):
    loop = get_event_loop()
    loop.run_until_complete(database.connect())
    logger.info("Connected to database")
    status: AnnotationFormOutput = loop.run_until_complete(
        create_annotations(
            form_data_input=form_data,
            jwt_data_input=jwt_data,
            db_user=db_user,
            message_db=message_db,
            prompt_message_db=prompt_message_db,
        )
    )
    logger.info("Got users from database")
    loop.run_until_complete(database.disconnect())
    return status.model_dump()
