from openai import AsyncClient, Client
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionFunctionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)

from src.chat.config import settings as chat_settings
from src.chat.constants import MAIN_SYSTEM_PROMPT, MODEL_NAME, TITLE_PROMPT
from src.chat.schemas import MessageDB, RoomUpdateInputDetails
from src.chat.service import (
    get_room_by_id_from_db,
    get_room_messages_from_db,
    update_room_in_db,
)
from src.listener.constants import room_changed_info
from src.listener.manager import listener
from src.listener.schemas import WSEventMessage


class HypoAI:
    def __init__(self, user_id: int, room_id: str):
        self.user_id: int = user_id
        self.room_id: str = room_id

        self.async_client: AsyncClient = AsyncClient(api_key=chat_settings.CHATGPT_KEY)
        self.client: Client = Client(api_key=chat_settings.CHATGPT_KEY)

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
            WSEventMessage(type=room_changed_info).model_dump(mode="json")
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
