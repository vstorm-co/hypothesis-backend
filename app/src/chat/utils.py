import openai

from src.chat.config import settings as chat_settings


async def chat_with_chat(message: str):
    try:
        async for chunk in await openai.ChatCompletion.acreate(
            api_key=chat_settings.CHATGPT_KEY,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": message},
            ],
            stream=True,
        ):
            if 'content' in chunk["choices"][0]["delta"]:
                yield chunk["choices"][0]["delta"]["content"]
    except Exception as exc:
        yield str(exc)
