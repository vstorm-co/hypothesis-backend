from functools import lru_cache

from pydantic_settings import BaseSettings


class ChatConfig(BaseSettings):
    CHATGPT_KEY: str = ""
    CLAUDE_KEY: str = ""


@lru_cache()
def get_settings():
    return ChatConfig()


settings = get_settings()
