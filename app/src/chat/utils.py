from src.chat.config import chat_settings
import openai


async def chat_with_chat(message: str):
    answer = []
    try:
        async for chunk in await openai.ChatCompletion.acreate(
            api_key=chat_settings.CHATGPT_KEY,
            model="gpt-3.5-turbo",
            messages=[
                    {"role": "user", "content": message},
                ],
                stream=True,
        ):
            # content = chunk['choices'][0]['delta']['content']
            # if content:
            #     yield content
            yield chunk['choices'][0]['delta']['content']
            # content = chunk['message']['content']
            # print(chunk['message']['content'])
            # print(type(chunk))
            # print("Dunno")
            # if content:
            #     yield chunk
            # content = chunk['choices'][0].get('delta', {}).get('content')
            # if content is not None:
            #     answer.append(content)
    except Exception as exc:
        yield str(exc)
        # return {"Error": str(exc)}
    # return {"Answer": answer}
