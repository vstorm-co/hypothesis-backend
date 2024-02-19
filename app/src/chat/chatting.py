import logging
import time
from functools import lru_cache

from openai import AsyncClient, Client
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionFunctionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)

from src.auth.schemas import UserDB
from src.chat.config import settings as chat_settings
from src.chat.constants import (
    FILE_PATTERN,
    MAIN_SYSTEM_PROMPT,
    MODEL_NAME,
    OPTIMIZE_CONTENT_PROMPT,
    TITLE_FROM_URL_PROMPT,
    TITLE_PROMPT,
)
from src.chat.manager import ConnectionManager
from src.chat.schemas import (
    BroadcastData,
    MessageDB,
    MessageDetails,
    RoomUpdateInputDetails,
)
from src.chat.service import (
    create_message_in_db,
    get_room_by_id_from_db,
    get_room_messages_from_db,
    update_message_in_db,
    update_room_in_db,
)
from src.listener.constants import (
    bot_message_creation_finished_info,
    optimizing_user_file_content_info,
    room_changed_info,
    user_file_updated_info,
)
from src.listener.manager import listener
from src.listener.schemas import WSEventMessage
from src.user_files.schemas import NewUserFileContent, UserFileDB
from src.user_files.service import (
    get_specific_user_file_from_db,
    optimize_file_content_in_db,
)
from src.user_files.utils import download_and_extract_file

logger = logging.getLogger(__name__)


class HypoAI:
    def __init__(self, user_id: int, room_id: str):
        self.user_id: int = user_id
        self.room_id: str = room_id

        self.async_client: AsyncClient = AsyncClient(api_key=chat_settings.CHATGPT_KEY)
        self.client: Client = Client(api_key=chat_settings.CHATGPT_KEY)

        self.stop_generation_flag = False  # Flag to control generation process

    async def load_messages_history(
        self,
    ) -> list[ChatCompletionUserMessageParam | ChatCompletionAssistantMessageParam]:
        def type_cast(
            message: MessageDB,
        ) -> ChatCompletionUserMessageParam | ChatCompletionAssistantMessageParam:
            if message.created_by == "user":
                return ChatCompletionUserMessageParam(
                    content=message.content, role="user"
                )
            else:
                return ChatCompletionAssistantMessageParam(
                    content=message.content, role="assistant"
                )

        db_messages = [
            MessageDB(**dict(message))
            for message in await get_room_messages_from_db(self.room_id)
        ]

        messages = [type_cast(message) for message in db_messages]

        return messages

    async def chat_with_chat(self, input_message: str):
        messages: list[
            ChatCompletionSystemMessageParam
            | ChatCompletionUserMessageParam
            | ChatCompletionAssistantMessageParam
            | ChatCompletionToolMessageParam
            | ChatCompletionFunctionMessageParam
        ] = [
            ChatCompletionSystemMessageParam(content=MAIN_SYSTEM_PROMPT, role="system"),
        ]

        messages_history = await self.load_messages_history()
        db_room = await get_room_by_id_from_db(self.room_id)
        room_name: str | None = None
        if db_room:
            room_name = db_room["name"]

        if self.is_chat_title_update_needed(messages_history, room_name):
            await self.update_chat_title(input_message=input_message)

        messages.extend(messages_history)

        # update messages with user input
        messages.append(
            ChatCompletionUserMessageParam(content=input_message, role="user")
        )

        try:
            # There is info that async_client.chat.completions.create
            # has no __aiter__ method, even we use AsyncClient
            # and stream=True
            # this is probably a bug in openai library
            # because we use client.chat.completions.create
            # without any problems
            # thus why we use type: ignore here
            async for chunk in await self.async_client.chat.completions.create(  # type: ignore  # noqa: E501
                model=MODEL_NAME,
                messages=messages,
                stream=True,
                user=str(self.user_id),
            ):
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:
            yield str(exc)

    async def update_chat_title(self, input_message: str):
        prompt = TITLE_PROMPT

        completion = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": input_message},
            ],
            user=str(self.user_id),
        )
        name = completion.choices[0].message.content

        await update_room_in_db(
            RoomUpdateInputDetails(
                room_id=self.room_id,
                user_id=self.user_id,
                name=name,
            )
        )
        await listener.receive_and_publish_message(
            WSEventMessage(
                type=room_changed_info, id=self.room_id, source="update-room-title"
            ).model_dump(mode="json")
        )

    @staticmethod
    def is_chat_title_update_needed(
        messages_history: list[
            ChatCompletionUserMessageParam | ChatCompletionAssistantMessageParam
        ],
        room_name: str | None,
    ) -> bool:
        is_first_message = len(messages_history) == 1
        room_chat_name_is_new_chat = room_name and room_name == "New Chat"

        if (
            is_first_message and room_chat_name_is_new_chat
        ) or room_chat_name_is_new_chat:
            return True

        return False

    async def get_updated_file_content(self, content: str) -> str | None:
        # get file uuid from <<file:uuid>> pattern
        file_uuid = content.split(FILE_PATTERN)[1].split("&gt;&gt;")[0]
        db_file = await get_specific_user_file_from_db(file_uuid, self.user_id)
        if not db_file:
            return content
        file: UserFileDB = UserFileDB(**dict(db_file))

        if not file or file.source_type not in ["url", "file"]:
            return content

        new_content = download_and_extract_file(file.source_value)
        if file.content == new_content:
            return file.optimized_content

        logger.info("File content has been updated")
        logger.info("Optimizing content...")
        await listener.receive_and_publish_message(
            WSEventMessage(
                type=optimizing_user_file_content_info,
                id=self.room_id,
                source="update-user-file-content",
            ).model_dump(mode="json")
        )
        file.optimized_content = self.optimize_content(new_content)
        logger.info("Updating file content in db...")
        await optimize_file_content_in_db(
            file_uuid,
            NewUserFileContent(
                content=new_content,
                optimized_content=file.optimized_content,
            ),
        )
        logger.info("File content has been updated in db")
        await listener.receive_and_publish_message(
            WSEventMessage(
                type=user_file_updated_info,
                id=self.room_id,
                source="update-user-file-content",
            ).model_dump(mode="json")
        )

        return file.optimized_content

    async def create_bot_answer(
        self, data_dict: dict, manager: ConnectionManager, room_id: str, user_db: UserDB
    ):
        content = data_dict["content"]
        if FILE_PATTERN in content:
            content = await self.get_updated_file_content(content)

        message_uuid: str | None = None
        bot_answer = ""
        start_time = time.time()  # Record the start time
        try:
            async for message in self.chat_with_chat(input_message=content):
                if self.stop_generation_flag:
                    # Check the flag before processing each message
                    break

                bot_answer += message
                await manager.broadcast(
                    BroadcastData(
                        type="message",
                        message=message,
                        room_id=room_id,
                        sender_user_email=user_db.email,
                        created_by="bot",
                    )
                )

                # create bot message in db
                bot_content = MessageDetails(
                    created_by="bot",
                    content=bot_answer,
                    room_id=room_id,
                    user_id=user_db.id,
                    elapsed_time=time.time() - start_time,
                )
                if not message_uuid:
                    db_mess = await create_message_in_db(bot_content)
                    if not db_mess:
                        return
                    message_uuid = str(db_mess["uuid"])
                else:
                    await update_message_in_db(message_uuid, bot_content)
        except Exception as e:
            # Log any exceptions
            logger.error(f"An error occurred in create_bot_answer: {e}")

        elapsed_time = time.time() - start_time
        logger.info(f"Chat response time: {elapsed_time} seconds")

        await manager.broadcast(
            BroadcastData(
                type=bot_message_creation_finished_info,
                message="",
                room_id=room_id,
                sender_user_email=user_db.email,
                created_by="user",
            )
        )
        await listener.receive_and_publish_message(
            WSEventMessage(
                type=bot_message_creation_finished_info,
                id=room_id,
                source="bot-message-creation-finished",
            ).model_dump(mode="json")
        )

    def optimize_content(self, content: str | None) -> str | None:
        bot_response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": OPTIMIZE_CONTENT_PROMPT},
                {"role": "user", "content": content},
            ],
            user=str(self.user_id),
        )
        optimized_content = bot_response.choices[0].message.content

        return optimized_content

    def get_title_from_url(self, url: str) -> str | None:
        bot_response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": TITLE_FROM_URL_PROMPT},
                {"role": "user", "content": url},
            ],
            user=str(self.user_id),
        )
        title = bot_response.choices[0].message.content

        return title


@lru_cache()
def get_hypo_ai() -> HypoAI:
    return HypoAI(user_id=0, room_id="0")


hypo_ai: HypoAI = get_hypo_ai()
