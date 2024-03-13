import logging

from databases.interfaces import Record
from fastapi import APIRouter, Depends
from time import time

from src.annotations.mocks import scrapped_content_mock
from src.annotations.schemas import AnnotationFormInput, AnnotationFormOutput, ListOfTextQuoteSelector, \
    TextQuoteSelector
from src.annotations.scrape import get_selectors_from_url
from src.annotations.service import get_selector_from_scrapped_data
from src.auth.jwt import parse_jwt_user_data
from src.auth.schemas import JWTData, UserDB
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
        jwt_data: JWTData = Depends(parse_jwt_user_data)
):
    start_time = time()
    user: Record | None = await get_user_by_id(jwt_data.user_id)
    if not user:
        raise Exception("User not found")

    selectors: list[TextQuoteSelector] = await get_selectors_from_url(annotation_data.url)

    for sl in selectors:
        logger.info(f"Selector: {sl.model_dump()}")

    # bot_answer = "I have found the following selectors: " + str(23232)
    # # save the message in the database
    # await create_message_in_db(MessageDetails(
    #     created_by="bot",
    #     content=bot_answer,
    #     room_id=annotation_data.room_id,
    #     user_id=jwt_data.user_id,
    #     elapsed_time=time() - start_time,
    # ))
    # # broadcast the message in the chat
    # await manager.broadcast(
    #     BroadcastData(
    #         type="message",
    #         message=bot_answer,
    #         room_id=annotation_data.room_id,
    #         sender_user_email=user["email"],
    #         created_by="bot",
    #     )
    # )
    # # set the message that the bot has finished creating the annotation
    # await manager.broadcast(
    #     BroadcastData(
    #         type=bot_message_creation_finished_info,
    #         message="",
    #         room_id=annotation_data.room_id,
    #         sender_user_email=user["email"],
    #         created_by="user",
    #     )
    # )
    #
    # return AnnotationFormOutput(status={"result": selectors.model_dump()})
