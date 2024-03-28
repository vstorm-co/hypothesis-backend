import logging

from src.chat.bot_ai import bot_ai
from src.chat.constants import MAX_TOKENS
from src.tokenizer.tiktoken import count_content_tokens
from src.user_files.schemas import UserFileDB

logger = logging.getLogger(__name__)


async def get_optimized_content(data: UserFileDB, room_id: str) -> str:
    pre_processed_content = data.content
    if not (
        data.source_value.endswith(".txt")
        or data.source_value.endswith(".docx")
        or data.source_value.endswith(".doc")
    ):
        content_tokens_count = count_content_tokens(data.content or "")
        if content_tokens_count > MAX_TOKENS and data.content:
            logger.info("Content too long, shortening...")
            data.content = data.content[:MAX_TOKENS]
            logger.info(f"Shortened content: {data.content}")

        logger.info("Getting most valuable content from page...")
        pre_processed_content = await bot_ai.get_valuable_page_content(
            content=f"""url: {data.source_value}
            title: {data.title}
            content: {data.content}
            """,
            user_id=data.user,
            room_id=room_id,
        )
        logger.info(f"Most valuable content from page: {pre_processed_content}")

    logger.info("Optimizing content...")
    optimized_content = await bot_ai.optimize_content(
        content=pre_processed_content, user_id=data.user, room_id=room_id
    )
    logger.info(f"Optimized content: {optimized_content}")

    return optimized_content or ""
