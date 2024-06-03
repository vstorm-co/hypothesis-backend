from logging import getLogger

from databases.interfaces import Record
from sqlalchemy import func, insert, select, update

from src.chat.constants import MODEL_NAME
from src.chat.schemas import MessageDBWithTokenUsage, MessageDetails
from src.database import TokenUsage, database
from src.token_usage.constants import token_prices
from src.token_usage.schemas import TokenUsageInput
from src.tokenizer.tiktoken import count_content_tokens

logger = getLogger(__name__)


async def get_max_id() -> int:
    query = select(func.max(TokenUsage.id))
    result = await database.fetch_val(query)
    return result or 0  # Return 0 if no records exist


async def generate_new_id() -> int:
    max_id = await get_max_id()
    return max_id + 1


async def create_token_usage_in_db(token_usage_data: TokenUsageInput) -> Record | None:
    insert_values = {
        **token_usage_data.model_dump(),
    }

    try:
        insert_query = insert(TokenUsage).values(**insert_values).returning(TokenUsage)
        return await database.fetch_one(insert_query)
    except Exception as e:
        logger.error(f"Error while inserting token usage: {e}")
        logger.info("Token usage already exists in the database")
        id_ = await generate_new_id()
        max_insert_query = (
            insert(TokenUsage).values(id=id_, **insert_values).returning(TokenUsage)
        )
        logger.info(f"Inserting token usage with id: {id_}")
        return await database.fetch_one(max_insert_query)


def get_token_usage_input_from_message(message: MessageDetails) -> TokenUsageInput:
    token_counts: int = count_content_tokens(message.content)
    token_usage_type = "prompt" if message.created_by == "user" else "completion"
    model_name = MODEL_NAME
    model_token_price = token_prices.get(
        model_name,
        {
            "prompt": 0.01,
            "completion": 0.03,
            "divider": 1000,
        },
    )
    price_per_token = model_token_price[token_usage_type]
    divider = model_token_price["divider"]
    token_usage_value = (token_counts / divider) * price_per_token

    return TokenUsageInput(
        type=token_usage_type,
        count=token_counts,
        value=token_usage_value,
    )


async def get_token_usage_by_id(token_usage_id: int) -> Record | None:
    select_query = select(TokenUsage).where(TokenUsage.id == token_usage_id)

    return await database.fetch_one(select_query)


async def update_token_usage_in_db(
    token_id: int, token_usage_data: TokenUsageInput
) -> Record | None:
    update_query = (
        update(TokenUsage)
        .where(TokenUsage.id == token_id)
        .values(**token_usage_data.model_dump())
        .returning(TokenUsage)
    )

    return await database.fetch_one(update_query)


def get_room_token_usages_by_messages(
    messages_schema: list[MessageDBWithTokenUsage],
) -> dict:
    prompt_tokens_count = 0
    completion_tokens_count = 0
    # values
    prompt_value = 0.0
    completion_value = 0.0
    for index, message in enumerate(messages_schema):
        # type hint for PyCharm
        index: int  # type: ignore
        message: MessageDBWithTokenUsage  # type: ignore

        if message.created_by == "user":
            prompt_tokens_count += message.usage.count
            prompt_value += message.usage.value

            # token counts and values
            message.usage.prompt_tokens_count = message.usage.count
            message.usage.total_tokens_count = message.usage.count
            message.usage.prompt_value = message.usage.value
            message.usage.total_value = message.usage.value
        elif message.created_by == "bot":
            completion_tokens_count += message.usage.count
            completion_value += message.usage.value
            # token usage for completion message is calculated from previous message
            # no need to worry about index out of range
            # as we have at least one message in messages_schema before "bot" response
            message.usage.prompt_tokens_count = messages_schema[index - 1].usage.count
            message.usage.completion_tokens_count = message.usage.count
            message.usage.total_tokens_count = (
                message.usage.prompt_tokens_count
                + message.usage.completion_tokens_count
            )
            # value is calculated from previous message
            message.usage.prompt_value = messages_schema[index - 1].usage.value
            message.usage.completion_value = message.usage.value
            message.usage.total_value = (
                message.usage.prompt_value + message.usage.completion_value
            )

    return {
        "prompt_tokens_count": prompt_tokens_count,
        "completion_tokens_count": completion_tokens_count,
        "prompt_value": prompt_value,
        "completion_value": completion_value,
    }
