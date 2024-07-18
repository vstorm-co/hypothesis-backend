import json
import logging
import time
from asyncio import get_event_loop
from concurrent.futures import CancelledError
from datetime import datetime
from functools import lru_cache
from typing import Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
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
from src.chat.content_cleaner import clean_html_input
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
from src.config import settings
from src.database import database
from src.listener.constants import (
    bot_message_creation_finished_info,
    listener_room_name,
    optimizing_user_file_content_info,
    room_changed_info,
    user_file_updated_info,
)
from src.listener.schemas import WSEventMessage
from src.redis import pub_sub_manager
from src.scraping.downloaders import download_and_extract_content_from_url
from src.tasks import celery_app
from src.user_files.constants import UserFileSourceType
from src.user_files.schemas import NewUserFileContent, UserFileDB
from src.user_files.service import (
    get_specific_user_file_from_db,
    optimize_file_content_in_db,
)
from src.user_models.schemas import UserModelOut
from src.user_models.service import get_user_model_by_uuid, decrypt_api_key

logger = logging.getLogger(__name__)


# manager = ConnectionManager()


class BotAI:
    _instance: Optional["BotAI"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, user_id: int = 0, room_id: str = "0"):
        self.user_id: int = user_id
        self.room_id: str = room_id

        self.async_client: AsyncClient = AsyncClient(api_key=chat_settings.CHATGPT_KEY)
        self.client: Client = Client(api_key=chat_settings.CHATGPT_KEY)

        self.stop_generation_flag = False  # Flag to control generation process
        self.llm_model = ChatOpenAI(  # type: ignore
            model=MODEL_NAME,
            openai_api_key=chat_settings.CHATGPT_KEY,
        )
        self.selected_model = MODEL_NAME

    async def set_llm_model(self, user_model_uuid: str, selected_model: str | None = None):
        user_model_db = await get_user_model_by_uuid(user_model_uuid, self.user_id)

        if not user_model_db:
            return

        self.selected_model = selected_model or MODEL_NAME
        user_model: UserModelOut = UserModelOut(**dict(user_model_db))

        if user_model.provider.lower() == "openai":
            self.llm_model = ChatOpenAI(  # type: ignore
                model=selected_model or user_model.defaultSelected,
                openai_api_key=decrypt_api_key(user_model.api_key),
            )
            return
        if user_model.provider.lower() == "claude":
            self.llm_model = ChatAnthropic(  # type: ignore
                model=selected_model or user_model.defaultSelected,
                openai_api_key=decrypt_api_key(user_model.api_key),
            )
            return

    async def type_cast(
            self, message: MessageDB, user_id: int, room_id: str
    ) -> ChatCompletionUserMessageParam | ChatCompletionAssistantMessageParam:
        logger.info(f"Type casting room: {room_id} message: {message.uuid}")
        content = message.content

        if FILE_PATTERN in content:
            content = await self.replace_file_pattern_with_optimized_content(
                content, user_id
            )

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

        return ChatCompletionAssistantMessageParam(
            content="Unknown message type", role="assistant"
        )

    async def replace_file_pattern_with_optimized_content(
            self, content: str, user_id: int
    ) -> str:
        file: UserFileDB | None = await self.get_user_file_from_content(
            content, user_id
        )
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
            self, user_id: int, room_id: str
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
            for message in await get_room_messages_from_db(room_id)
        ]

        messages += [
            await self.type_cast(message, user_id, room_id) for message in db_messages
        ]

        return messages

    async def stream_bot_response(self, input_message: str, user_id: int, room_id: str):
        messages_history = await self.load_messages_history(user_id, room_id)
        db_room = await get_room_by_id_from_db(room_id)
        room_name: str | None = None
        if db_room:
            room_name = db_room["name"]

        if self._is_chat_title_update_needed(messages_history, room_name):
            await self.update_chat_title(
                input_message=input_message, room_id=room_id, user_id=user_id
            )

        parser = StrOutputParser()
        prompt = PromptTemplate(
            template=MAIN_SYSTEM_PROMPT,
            input_variables=["input"],
        )
        chain = prompt | self.llm_model | parser

        def get_message_history(session_id: str) -> RedisChatMessageHistory:
            return RedisChatMessageHistory(session_id, url=settings.REDIS_URL.unicode_string())
        memory = get_message_history(str(db_room["uuid"]))

        with_message_history: RunnableWithMessageHistory = RunnableWithMessageHistory(
            runnable=chain,
            get_session_history=lambda session_id: memory,
            input_messages_key="input",
            history_messages_key="history",
        )

        try:
            async for chunk in with_message_history.astream({
                                                                "input": input_message
                                                            },
                                                            config={"configurable": {"session_id": str(room_id)}}):
                logger.info(chunk)
                yield chunk
        except Exception as exc:
            yield str(exc)

        # try:
        #     # There is info that async_client.chat.completions.create
        #     # has no __aiter__ method, even we use AsyncClient
        #     # and stream=True
        #     # this is probably a bug in openai library
        #     # because we use client.chat.completions.create
        #     # without any problems
        #     # thus why we use type: ignore here
        #     async for chunk in await self.async_client.chat.completions.create(  # type: ignore  # noqa: E501
        #             model=MODEL_NAME,
        #             messages=messages_history
        #                      + [ChatCompletionUserMessageParam(content=input_message, role="user")],
        #             stream=True,
        #             user=str(user_id),
        #     ):
        #         if chunk.choices and chunk.choices[0].delta.content:
        #             yield chunk.choices[0].delta.content
        # except Exception as exc:
        #     yield str(exc)

    async def stream_bot_response2(self, input_message: str, user_id: int, room_id: str):
        messages_history = await self.load_messages_history(user_id, room_id)
        db_room = await get_room_by_id_from_db(room_id)
        room_name: str | None = None
        if db_room:
            room_name = db_room["name"]

        if self._is_chat_title_update_needed(messages_history, room_name):
            await self.update_chat_title(
                input_message=input_message, room_id=room_id, user_id=user_id
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
                    messages=messages_history
                             + [ChatCompletionUserMessageParam(content=input_message, role="user")],
                    stream=True,
                    user=str(user_id),
            ):
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:
            yield str(exc)

    async def update_chat_title(self, input_message: str, room_id: str, user_id: int):
        start_time = time.time()
        # show sent message in the room
        await pub_sub_manager.publish(
            room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=room_id,
                    date=datetime.now().isoformat(),
                    api=f"{self.selected_model} API",
                    type="sent",
                    data={
                        "type": "update-room-title",
                        "template": TITLE_PROMPT,
                        "input": {
                            "query": input_message,
                        },
                    },
                ).model_dump(mode="json")
            ),
        )

        name: str | None = await self.get_title_from_content(input_message)

        # show log message for user
        await pub_sub_manager.publish(
            room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=room_id,
                    date=datetime.now().isoformat(),
                    api=f"{self.selected_model} API",
                    type="recd",
                    elapsed_time=time.time() - start_time,
                    data={
                        "type": "update-room-title",
                        "recd_name": name,
                    },
                ).model_dump(mode="json")
            ),
        )

        await update_room_in_db(
            RoomUpdateInputDetails(
                room_id=room_id,
                user_id=user_id,
                name=name,
            ),
            update_share=False,
            update_visibility=False,
        )
        await pub_sub_manager.publish(
            listener_room_name,
            json.dumps(
                WSEventMessage(
                    type=room_changed_info,
                    id=room_id,
                    source="update-room-title",
                ).model_dump(mode="json")
            ),
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

    @staticmethod
    async def get_user_file_from_content(
            content: str, user_id: int
    ) -> UserFileDB | None:
        file_uuid = content.split(FILE_PATTERN)[1].split(">>")[0]
        db_file = await get_specific_user_file_from_db(file_uuid, user_id)
        if not db_file:
            logger.error(f"File with uuid {file_uuid} not found in db")
            return None
        file: UserFileDB = UserFileDB(**dict(db_file))

        return file

    async def get_updated_file_content(
            self, input_content: str, room_id: str, user_id: int
    ) -> str | None:
        file: UserFileDB | None = await self.get_user_file_from_content(
            input_content, user_id
        )
        if not file:
            return input_content

        new_content: str
        if not file.source_type == UserFileSourceType.GOOGLE_DRIVE:
            url_data = await download_and_extract_content_from_url(file.source_value)
            if not url_data:
                return input_content
            new_content = url_data.get("content", "")
            logger.info(
                f"New content for file with uuid {file.uuid}: {new_content[:50]}..."
            )
            if file.content == new_content and file.optimized_content:
                logger.info("File content has not been updated")
                return input_content.replace(
                    f"{FILE_PATTERN}{file.uuid}>>",
                    f"\nfile content###{file.optimized_content}###\n" or "",
                )
        else:
            new_content = file.content or ""

        if file.optimized_content:
            return input_content.replace(
                f"{FILE_PATTERN}{file.uuid}>>",
                f"\nfile content###{file.optimized_content}###\n" or "",
            )
        logger.info("Optimizing content...")

        file.optimized_content = await self.optimize_content(
            new_content, room_id, user_id
        )

        logger.info("Updating file content in db...")
        await optimize_file_content_in_db(
            str(file.uuid),
            NewUserFileContent(
                content=new_content,
                optimized_content=file.optimized_content,
            ),
        )
        logger.info("File content has been updated in db")

        logger.info(
            f"New optimized content of file {file.uuid} has been sent to the room"
        )
        return input_content.replace(
            f"{FILE_PATTERN}{file.uuid}>>",
            f"\nfile content###{file.optimized_content}###\n" or "",
        )

    async def create_bot_answer(
            self, data_dict: dict, room_id: str, user_db_input: dict
    ) -> str | None:
        user_db = UserDB(**user_db_input)
        raw_content = data_dict["content"]

        if FILE_PATTERN in raw_content:
            logger.info(f"File pattern found in content: {raw_content}")
            await pub_sub_manager.publish(
                listener_room_name,
                json.dumps(
                    WSEventMessage(
                        type=optimizing_user_file_content_info,
                        id=room_id,
                        source="update-user-file-content",
                    ).model_dump(mode="json")
                ),
            )
            raw_content = await self.get_updated_file_content(
                raw_content, room_id, user_db.id
            )
            await pub_sub_manager.publish(
                listener_room_name,
                json.dumps(
                    WSEventMessage(
                        type=user_file_updated_info,
                        id=room_id,
                        source="update-user-file-content",
                    ).model_dump(mode="json")
                ),
            )

        # clean input html
        content = clean_html_input(raw_content)
        logger.info(f"Cleaned content: {content[:50]}...")

        message_uuid: str | None = None
        bot_content: MessageDetails | None = None
        bot_answer = ""
        start_time = time.time()  # Record the start time

        # show sent message in the room
        await pub_sub_manager.publish(
            room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=room_id,
                    date=datetime.now().isoformat(),
                    api=f"{self.selected_model} API",
                    type="sent",
                    data={
                        "template": MAIN_SYSTEM_PROMPT,
                        "input": {
                            "query": content,
                        },
                    },
                ).model_dump(mode="json")
            ),
        )
        try:
            async for message in self.stream_bot_response(content, user_db.id, room_id):
                if self.stop_generation_flag:
                    # Check the flag before processing each message
                    break

                bot_answer += message
                await pub_sub_manager.publish(
                    room_id,
                    json.dumps(
                        BroadcastData(
                            type="message",
                            message=message,
                            room_id=room_id,
                            created_by="bot",
                        ).model_dump(mode="json")
                    ),
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
                        return None
                    message_uuid = str(db_mess["uuid"])
                else:
                    await update_message_in_db(message_uuid, bot_content)
        except Exception as e:
            # Log any exceptions
            logger.error(f"An error occurred in create_bot_answer: {e}")

        elapsed_time = time.time() - start_time
        # show log message for user
        await pub_sub_manager.publish(
            room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=room_id,
                    date=datetime.now().isoformat(),
                    api=f"{self.selected_model} API",
                    type="recd",
                    elapsed_time=elapsed_time,
                    data=bot_content.model_dump(
                        exclude={"sender_picture", "content_html", "content_dict"},
                        mode="json",
                    )
                    if bot_content
                    else {},
                ).model_dump(mode="json")
            ),
        )
        logger.info(f"Chat response time: {elapsed_time} seconds")

        creation_finished_info = json.dumps(
            BroadcastData(
                type=bot_message_creation_finished_info,
                message="",
                room_id=room_id,
                created_by="bot",
            ).model_dump(mode="json")
        )
        logger.info(
            "Sending message '%s' to the room %s", creation_finished_info, room_id
        )
        await pub_sub_manager.publish(room_id, creation_finished_info)
        logger.info("Message sent to the room %s", room_id)

        await pub_sub_manager.publish(
            listener_room_name,
            json.dumps(
                WSEventMessage(
                    type=bot_message_creation_finished_info,
                    id=room_id,
                    source="bot-message-creation-finished",
                ).model_dump(mode="json")
            ),
        )

        return bot_answer

    async def optimize_content(
            self, content: str | None, room_id: str | None, user_id: int | None
    ) -> str | None:
        if not content:
            return None

        start = time.time()
        await pub_sub_manager.publish(
            room_id or "",
            json.dumps(
                APIInfoBroadcastData(
                    room_id=room_id or "",
                    date=datetime.now().isoformat(),
                    api=f"{self.selected_model} API",
                    type="sent",
                    data={
                        "template": OPTIMIZE_CONTENT_PROMPT,
                        "input": {
                            "query": content,
                        },
                    },
                ).model_dump(mode="json")
            ),
        )
        logger.info("Content: %s", content)

        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=127_000,
            chunk_overlap=0,
        )
        splits: list[str] = splitter.split_text(content)
        optimized_content: str | None = None
        for index, split in enumerate(splits):
            logger.info("Processing split %s out of %s", index + 1, len(splits))
            bot_response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": OPTIMIZE_CONTENT_PROMPT},
                    {"role": "user", "content": split},
                ],
                user=str(user_id or 0),
            )
            if optimized_content and bot_response.choices[0].message.content:
                optimized_content += bot_response.choices[0].message.content
                continue

            optimized_content = bot_response.choices[0].message.content

        await pub_sub_manager.publish(
            room_id or "",
            json.dumps(
                APIInfoBroadcastData(
                    room_id=room_id or "",
                    date=datetime.now().isoformat(),
                    api=f"{self.selected_model} API",
                    type="recd",
                    elapsed_time=time.time() - start,
                    data={
                        "recd_optimized_content": optimized_content,
                    },
                ).model_dump(mode="json")
            ),
        )

        return optimized_content

    async def get_title_from_url(
            self, url: str, room_id: str | None = None, user_id: int | None = None
    ) -> str | None:
        start = time.time()
        await pub_sub_manager.publish(
            room_id or "",
            json.dumps(
                APIInfoBroadcastData(
                    room_id=room_id or "",
                    date=datetime.now().isoformat(),
                    api=f"{self.selected_model} API",
                    type="sent",
                    data={
                        "template": TITLE_FROM_URL_PROMPT,
                        "input": {
                            "query": url,
                        },
                    },
                ).model_dump(mode="json")
            ),
        )

        bot_response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": TITLE_FROM_URL_PROMPT},
                {"role": "user", "content": url},
            ],
            user=str(user_id or 0),
        )
        title: str | None = bot_response.choices[0].message.content

        await pub_sub_manager.publish(
            room_id or "",
            json.dumps(
                APIInfoBroadcastData(
                    room_id=room_id or "",
                    date=datetime.now().isoformat(),
                    api=f"{self.selected_model} API",
                    type="recd",
                    elapsed_time=time.time() - start,
                    data={
                        "recd_title": title,
                    },
                ).model_dump(mode="json")
            ),
        )

        return title

    async def get_title_from_content(self, content: str) -> str | None:
        llm = self.llm_model
        parser = StrOutputParser()
        prompt = PromptTemplate(
            template=TITLE_PROMPT,
            input_variables=["input"],
        )
        chain = prompt | llm | parser

        return chain.invoke({"input": content})

    async def get_valuable_page_content(
            self, content: str, room_id: str | None, user_id: int | None
    ) -> str | None:
        start = time.time()
        await pub_sub_manager.publish(
            room_id or "",
            json.dumps(
                APIInfoBroadcastData(
                    room_id=room_id or "",
                    date=datetime.now().isoformat(),
                    api=f"{self.selected_model} API",
                    type="sent",
                    data={
                        "template": VALUABLE_PAGE_CONTENT_PROMPT,
                        "input": {
                            "query": content,
                        },
                    },
                ).model_dump(mode="json")
            ),
        )

        bot_response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": VALUABLE_PAGE_CONTENT_PROMPT},
                {"role": "user", "content": content},
            ],
            user=str(user_id or "0"),
            temperature=0.0,
        )
        valuable_content: str | None = bot_response.choices[0].message.content

        await pub_sub_manager.publish(
            room_id or "",
            json.dumps(
                APIInfoBroadcastData(
                    room_id=room_id or "",
                    date=datetime.now().isoformat(),
                    api=f"{self.selected_model} API",
                    type="recd",
                    elapsed_time=time.time() - start,
                    data={
                        "recd_valuable_content": valuable_content,
                    },
                ).model_dump(mode="json")
            ),
        )

        return valuable_content


@celery_app.task
def create_bot_answer_task(data_dict: dict, room_id: str, user_db: dict):
    logger.info("Data dict: %s", data_dict)
    logger.info("Room id: %s", room_id)
    logger.info("User db: %s", user_db)
    try:
        loop = get_event_loop()
        loop.run_until_complete(database.connect())
        logger.info("Connected to database")
        bot_answer = loop.run_until_complete(
            bot_ai.create_bot_answer(
                data_dict=data_dict, room_id=room_id, user_db_input=user_db
            )
        )
        logger.info("Got users from database")
        loop.run_until_complete(database.disconnect())
        return {
            "status": "OK",
            "bot_answer": bot_answer,
        }
    except CancelledError:
        logger.info("Stopping generation due to cancellation")
        return {"status": "Stopped"}


@lru_cache()
def get_bot_ai() -> BotAI:
    return BotAI()


bot_ai: BotAI = get_bot_ai()
