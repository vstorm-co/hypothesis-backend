import openai

from src.chat.config import settings as chat_settings
from src.chat.schemas import MessageDB
from src.chat.service import get_room_messages_from_db


async def chat_with_chat(input_message: str, room_id: str):
    db_messages = [
        MessageDB(**dict(message))
        for message in await get_room_messages_from_db(room_id)
    ]

    messages = [
        {
            "role": "user" if message.created_by == "user" else "assistant",
            "content": message.content,
        }
        for message in db_messages
    ] + [{"role": "user", "content": input_message}]

    try:
        async for chunk in await openai.ChatCompletion.acreate(
            api_key=chat_settings.CHATGPT_KEY,
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True,
        ):
            if "content" in chunk["choices"][0]["delta"]:
                yield chunk["choices"][0]["delta"]["content"]
    except Exception as exc:
        yield str(exc)
