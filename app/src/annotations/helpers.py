import json
from logging import Logger, getLogger
from time import time

from src.annotations.schemas import AnnotationFormInput, AnnotationFormOutput
from src.auth.schemas import JWTData
from src.chat.bot_ai import BotAI
from src.chat.constants import DEFAULT_ROOM_NAME
from src.chat.schemas import BroadcastData, MessageDetails
from src.chat.service import get_room_by_id_from_db, update_message_in_db
from src.listener.constants import bot_message_creation_finished_info
from src.redis_client import pub_sub_manager
from src.user_files.constants import UserFileSourceType

logger: Logger = getLogger(__name__)


async def user_not_found_error(
    message_db: dict, form_data_input: dict, jwt_data_input: dict
) -> AnnotationFormOutput:
    start_time = time()
    logger.error("User not found")
    await update_message_in_db(
        message_db["uuid"],
        MessageDetails(
            created_by="annotation",
            content="User not found",
            content_html="User not found",
            content_dict={
                "status": "error",
                "reason": "User not found",
                "elapsed_time": time() - start_time,
                "prompt": form_data_input["prompt"],
                "source": form_data_input["url"],
                "input": form_data_input,
            },
            room_id=form_data_input["room_id"],
            user_id=jwt_data_input["user_id"],
        ),
    )
    # set the message that the bot has finished creating the annotation
    await pub_sub_manager.publish(
        form_data_input["room_id"],
        json.dumps(
            BroadcastData(
                type=bot_message_creation_finished_info,
                message="",
                room_id=form_data_input["room_id"],
                created_by="bot",
            ).model_dump(mode="json")
        ),
    )

    return AnnotationFormOutput(status={"error": "user not found"})


async def update_room_title_in_annotation(
    form_data: AnnotationFormInput, bot_ai: BotAI, jwt_data: JWTData
) -> None:
    db_room = await get_room_by_id_from_db(form_data.room_id)
    room_name: str | None = db_room["name"] if db_room else None

    if room_name == DEFAULT_ROOM_NAME or not room_name:
        logger.info("Updating room title")
        info_from = (
            "google drive"
            if form_data.input_type == UserFileSourceType.GOOGLE_DRIVE
            else form_data.url
        )
        await bot_ai.update_chat_title(
            input_message=f"""User asked for {form_data.prompt} from {info_from}""",
            room_id=form_data.room_id,
            user_id=jwt_data.user_id,
        )
