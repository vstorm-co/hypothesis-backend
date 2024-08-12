import json
import logging
from asyncio import get_event_loop
from time import time

from src.annotations.helpers import (
    update_room_title_in_annotation,
    user_not_found_error,
)
from src.annotations.hypothesis_api import HypothesisAPI
from src.annotations.messaging import create_message_for_users
from src.annotations.schemas import (
    AnnotationFormInput,
    AnnotationFormOutput,
    HypothesisAnnotationCreateInput,
    HypothesisAnnotationCreateOutput,
    HypothesisApiInput,
    HypothesisSelector,
    HypothesisTarget,
    TextQuoteSelector,
)
from src.annotations.scrape import AnnotationsScraper
from src.annotations.validations import validate_data_tags
from src.auth.schemas import JWTData, UserDB
from src.chat.bot_ai import BotAI
from src.chat.content_cleaner import clean_html_input
from src.chat.schemas import BroadcastData, MessageDetails
from src.chat.service import update_message_in_db
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
        return await user_not_found_error(message_db, form_data_input, jwt_data_input)

    user_db: UserDB = UserDB(**db_user)
    form_data: AnnotationFormInput = AnnotationFormInput(**form_data_input)
    jwt_data: JWTData = JWTData(**jwt_data_input)

    # clean input html
    form_data.prompt = clean_html_input(form_data.prompt)
    form_data.response_template = clean_html_input(form_data.response_template)

    hypo_api: HypothesisAPI = HypothesisAPI(
        data=HypothesisApiInput(room_id=form_data.room_id, api_key=form_data.api_key)
    )
    scraper: AnnotationsScraper = AnnotationsScraper(
        input_form_data=form_data, user_db=user_db
    )
    bot_ai: BotAI = BotAI(user_id=jwt_data.user_id, room_id=form_data.room_id)
    # set timer start
    start_time = time()

    hypothesis_user_id = await hypo_api.get_hypothesis_user_id()
    logger.info(f"Hypo user: {hypothesis_user_id}")

    if form_data.delete_annotations:
        await hypo_api.delete_user_annotations_of_url(hypothesis_user_id, form_data.url)

    await update_room_title_in_annotation(form_data, bot_ai, jwt_data)

    # get selectors data
    logger.info("Getting selectors data")
    selectors_data: dict = await scraper.get_hypothesis_selectors_data()
    selectors: list[TextQuoteSelector] = selectors_data.get("selectors", [])
    logger.info("Selectors downloaded")

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
                content=f"Selectors not created with prompt: {form_data.prompt}",
                content_dict={
                    "status": "error",
                    "reason": selectors_data.get("error", "Selectors not created"),
                    "elapsed_time": time() - start_time,
                    "prompt": form_data.prompt,
                    "source": form_data.url,
                    "input": form_data.model_dump(mode="json"),
                    "model_used": form_data.model,
                },
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

        return AnnotationFormOutput(status={"error": "selectors not created"})

    source: str = scraper.pdf_urn or form_data.url
    logger.info(f"Source: {source}")
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
            reason = f"""Annotation `{annotation.text or ''}` not created,
            problem calling Hypothesis API."""
            await update_message_in_db(
                message_db["uuid"],
                MessageDetails(
                    created_by="annotation",
                    content=f"Annotation not created with prompt: {form_data.prompt}",
                    content_dict={
                        "status": "error",
                        "reason": reason,
                        "elapsed_time": time() - start_time,
                        "prompt": form_data.prompt,
                        "source": form_data.url,
                        "input": form_data.model_dump(mode="json"),
                        "model_used": form_data.model,
                    },
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

            return AnnotationFormOutput(status={"error": "annotation not created"})

        hypo_annotations_list.append(hypo_annotation_output)

    # save the message in the database
    # save id as a content
    # this will be loaded in getting chat history
    # and target selectors will be loaded from the hypothesis API
    user_message = create_message_for_users(hypo_annotations_list, form_data.prompt)
    # add via.hypothes.is to the url if the source is UserFileSourceType.YOUTUBE
    url = form_data.url
    if scraper.source == UserFileSourceType.YOUTUBE:
        url = f"https://via.hypothes.is/{url}"
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
                "url": url,
                "prompt": form_data.prompt,
                "group_id": form_data.group,
                "source_url": url,
                "selectors": [selector.model_dump() for selector in selectors],
                "model_used": form_data.model,
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
