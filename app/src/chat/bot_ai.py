import logging
import time
from asyncio import create_task
from datetime import datetime
from functools import lru_cache

from openai import AsyncClient, Client
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionFunctionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)

from src.annotations.messaging import create_message_for_ai_history
from src.auth.schemas import UserDB
from src.chat.config import settings as chat_settings
from src.chat.constants import (
    FILE_PATTERN,
    MAIN_SYSTEM_PROMPT,
    MODEL_NAME,
    OPTIMIZE_CONTENT_PROMPT,
    TITLE_FROM_URL_PROMPT,
    TITLE_PROMPT,
    VALUABLE_PAGE_CONTENT_PROMPT,
)
from src.chat.manager import connection_manager as manager
from src.chat.schemas import (
    APIInfoBroadcastData,
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
from src.scraping.downloaders import download_and_extract_content_from_url
from src.user_files.schemas import NewUserFileContent, UserFileDB
from src.user_files.service import (
    get_specific_user_file_from_db,
    optimize_file_content_in_db,
)

logger = logging.getLogger(__name__)


class BotAI:
    def __init__(self, user_id: int = 0, room_id: str = "0"):
        self.user_id: int = user_id
        self.room_id: str = room_id

        self.async_client: AsyncClient = AsyncClient(api_key=chat_settings.CHATGPT_KEY)
        self.client: Client = Client(api_key=chat_settings.CHATGPT_KEY)

        self.stop_generation_flag = False  # Flag to control generation process

    async def type_cast(  # type: ignore
        self,
        message: MessageDB,
    ) -> ChatCompletionUserMessageParam | ChatCompletionAssistantMessageParam:
        content = message.content

        if FILE_PATTERN in content:
            content = await self.replace_file_pattern_with_optimized_content(content)

        if message.created_by == "user":
            return ChatCompletionUserMessageParam(content=content, role="user")
        elif message.created_by == "bot":
            return ChatCompletionAssistantMessageParam(
                content=content, role="assistant"
            )
        elif message.created_by == "annotation":
            hypo_annotations_list: list[dict] | None = (
                message.content_dict.get("annotations", None)
                if message.content_dict
                else None
            )

            if not hypo_annotations_list:
                return ChatCompletionAssistantMessageParam(
                    content="Annotation not found", role="assistant"
                )

            content = create_message_for_ai_history(hypo_annotations_list)
            return ChatCompletionAssistantMessageParam(
                content=content, role="assistant"
            )

    async def replace_file_pattern_with_optimized_content(self, content: str) -> str:
        file: UserFileDB | None = await self.get_user_file_from_content(content)
        if not file:
            return content

        # change file pattern in content to optimized content
        content = content.replace(
            f"{FILE_PATTERN}{file.uuid}>>", file.optimized_content or ""
        )
        logger.info(
            f"File pattern in content replaced with optimized content: {content}"
        )

        return content

    async def load_messages_history(
        self,
    ) -> list[
        ChatCompletionSystemMessageParam
        | ChatCompletionUserMessageParam
        | ChatCompletionAssistantMessageParam
        | ChatCompletionToolMessageParam
        | ChatCompletionFunctionMessageParam
    ]:
        messages: list[
            ChatCompletionSystemMessageParam
            | ChatCompletionUserMessageParam
            | ChatCompletionAssistantMessageParam
            | ChatCompletionToolMessageParam
            | ChatCompletionFunctionMessageParam
        ] = [
            ChatCompletionSystemMessageParam(content=MAIN_SYSTEM_PROMPT, role="system"),
        ]

        db_messages = [
            MessageDB(**dict(message))
            for message in await get_room_messages_from_db(self.room_id)
        ]

        messages += [await self.type_cast(message) for message in db_messages]

        return messages

    async def stream_bot_response(self, input_message: str):
        messages_history = await self.load_messages_history()
        db_room = await get_room_by_id_from_db(self.room_id)
        room_name: str | None = None
        if db_room:
            room_name = db_room["name"]

        if self._is_chat_title_update_needed(messages_history, room_name):
            await self.update_chat_title(input_message=input_message)

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
                messages=messages_history
                + [ChatCompletionUserMessageParam(content=input_message, role="user")],
                stream=True,
                user=str(self.user_id),
            ):
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:
            yield str(exc)

    async def update_chat_title(self, input_message: str):
        prompt = TITLE_PROMPT

        # show sent message in the room
        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="OpenAI API",
                    type="sent",
                    data={
                        "type": "update-room-title",
                        "template": prompt,
                        "input": {
                            "query": input_message,
                        },
                    },
                )
            )
        )

        completion = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": input_message},
            ],
            user=str(self.user_id),
        )
        name: str | None = completion.choices[0].message.content

        # show log message for user
        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="OpenAI API",
                    type="recd",
                    data={
                        "type": "update-room-title",
                        "recd_name": name,
                    },
                )
            )
        )

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
    def _is_chat_title_update_needed(
        messages_history: list[
            ChatCompletionSystemMessageParam
            | ChatCompletionUserMessageParam
            | ChatCompletionAssistantMessageParam
            | ChatCompletionToolMessageParam
            | ChatCompletionFunctionMessageParam
        ],
        room_name: str | None,
    ) -> bool:
        is_first_message = len(messages_history) <= 1
        room_chat_name_is_new_chat = room_name and room_name == "New Chat"

        if (
            is_first_message and room_chat_name_is_new_chat
        ) or room_chat_name_is_new_chat:
            return True

        return False

    async def get_user_file_from_content(self, content: str) -> UserFileDB | None:
        file_uuid = content.split(FILE_PATTERN)[1].split(">>")[0]
        db_file = await get_specific_user_file_from_db(file_uuid, self.user_id)
        if not db_file:
            logger.error(f"File with uuid {file_uuid} not found in db")
            return None
        file: UserFileDB = UserFileDB(**dict(db_file))

        return file

    async def get_updated_file_content(self, content: str) -> str | None:
        file: UserFileDB | None = await self.get_user_file_from_content(content)
        if not file:
            return content

        if file.source_type not in ["url", "file"]:
            logger.error(f"File with uuid {file.uuid} has unsupported source type")
            return content

        new_content = await download_and_extract_content_from_url(file.source_value)
        logger.info(
            f"New content for file with uuid {file.uuid}: {new_content[:50]}..."
        )
        if file.content == new_content:
            logger.info("File content has not been updated")
            return content.replace(
                f"{FILE_PATTERN}{file.uuid}>>",
                f"\nfile content###{file.optimized_content}###\n" or "",
            )

        logger.info("File content has been updated")
        logger.info("Optimizing content...")
        await listener.receive_and_publish_message(
            WSEventMessage(
                type=optimizing_user_file_content_info,
                id=self.room_id,
                source="update-user-file-content",
            ).model_dump(mode="json")
        )
        file.optimized_content = await self.optimize_content(new_content)
        logger.info("Updating file content in db...")
        await optimize_file_content_in_db(
            str(file.uuid),
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
        logger.info("New optimized content has been sent to the room")

        return content.replace(
            f"{FILE_PATTERN}{file.uuid}>>",
            f"\nfile content###{file.optimized_content}###\n" or "",
        )

    async def create_bot_answer(self, data_dict: dict, room_id: str, user_db: UserDB):
        content = data_dict["content"]
        logger.info(f"Creating bot answer for content: {content}")

        if FILE_PATTERN in content:
            logger.info(f"File pattern found in content: {content}")
            content = await self.get_updated_file_content(content)

        message_uuid: str | None = None
        bot_content: MessageDetails | None = None
        bot_answer = ""
        start_time = time.time()  # Record the start time

        # show sent message in the room
        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="OpenAI API",
                    type="sent",
                    data={
                        "template": MAIN_SYSTEM_PROMPT,
                        "input": {
                            "query": content,
                        },
                    },
                )
            )
        )
        try:
            async for message in self.stream_bot_response(input_message=content):
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

        # show log message for user
        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="OpenAI API",
                    type="recd",
                    data=bot_content.model_dump(
                        exclude={"sender_picture", "content_html", "content_dict"},
                        mode="json",
                    )
                    if bot_content
                    else {},
                )
            )
        )

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

    async def optimize_content(self, content: str | None) -> str | None:
        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="OpenAI API",
                    type="sent",
                    data={
                        "template": OPTIMIZE_CONTENT_PROMPT,
                        "input": {
                            "query": content,
                        },
                    },
                )
            )
        )

        bot_response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": OPTIMIZE_CONTENT_PROMPT},
                {"role": "user", "content": content},  # type: ignore
            ],
            user=str(self.user_id),
        )
        optimized_content: str | None = bot_response.choices[0].message.content

        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="OpenAI API",
                    type="recd",
                    data={
                        "recd_optimized_content": optimized_content,
                    },
                )
            )
        )

        return optimized_content

    async def get_title_from_url(self, url: str) -> str | None:
        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="OpenAI API",
                    type="sent",
                    data={
                        "template": TITLE_FROM_URL_PROMPT,
                        "input": {
                            "query": url,
                        },
                    },
                )
            )
        )

        bot_response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": TITLE_FROM_URL_PROMPT},
                {"role": "user", "content": url},
            ],
            user=str(self.user_id),
        )
        title: str | None = bot_response.choices[0].message.content

        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="OpenAI API",
                    type="recd",
                    data={
                        "recd_title": title,
                    },
                )
            )
        )

        return title

    async def get_valuable_page_content(self, content: str) -> str | None:
        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="OpenAI API",
                    type="sent",
                    data={
                        "template": VALUABLE_PAGE_CONTENT_PROMPT,
                        "input": {
                            "query": content,
                        },
                    },
                )
            )
        )

        bot_response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": VALUABLE_PAGE_CONTENT_PROMPT},
                {"role": "user", "content": content},
            ],
            user=str(self.user_id),
            temperature=0.0,
        )
        valuable_content: str | None = bot_response.choices[0].message.content

        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="OpenAI API",
                    type="recd",
                    data={
                        "recd_valuable_content": valuable_content,
                    },
                )
            )
        )

        return valuable_content


@lru_cache()
def get_bot_ai() -> BotAI:
    return BotAI()


bot_ai: BotAI = get_bot_ai()
