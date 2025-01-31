from langchain_community.chat_message_histories import RedisChatMessageHistory

from src.config import settings


def get_message_history(session_id: str) -> RedisChatMessageHistory:
    return RedisChatMessageHistory(session_id, url=settings.REDIS_URL.unicode_string())
